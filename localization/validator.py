from __future__ import annotations

from string import Formatter
from typing import Any

from localization.exceptions import LocaleDataError, PlaceholderError
from localization.repository import LocaleRepository


class LocaleValidator:
    """Validates locale documents and cross-locale compatibility rules."""

    REQUIRED_ROOT_KEYS = ("_meta", "messages", "enums", "faqs")

    def __init__(self, repository: LocaleRepository, *, require_complete_locales: bool = False) -> None:
        self.repository = repository
        self.require_complete_locales = require_complete_locales

    def validate_all(self) -> None:
        for locale in self.repository.get_locale_descriptors():
            self.validate_single_locale(locale)

    def validate_single_locale(self, locale: str) -> None:
        data = self.repository.load_locale(locale)
        self.validate_single_locale_data(locale, data)

    def validate_single_locale_data(self, locale: str, data: dict[str, Any]) -> None:
        self._validate_root(locale, data)
        self._validate_messages(data["messages"], path="messages")
        self._validate_enums(data["enums"], path="enums")
        self._validate_faqs(data["faqs"], path="faqs")
        self._validate_against_default(locale, data)

    def _validate_root(self, locale: str, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise LocaleDataError("Locale data must be a JSON object.")

        missing = [key for key in self.REQUIRED_ROOT_KEYS if key not in data]
        if missing:
            raise LocaleDataError(f"Missing required root keys: {missing}")

        meta = data.get("_meta")
        if not isinstance(meta, dict):
            raise LocaleDataError("_meta must be an object.")
        if meta.get("locale") != locale:
            raise LocaleDataError(f"_meta.locale must be '{locale}'.")
        if not isinstance(meta.get("version"), int):
            raise LocaleDataError("_meta.version must be an integer.")

    def _validate_messages(self, node: Any, *, path: str) -> None:
        if not isinstance(node, dict):
            raise LocaleDataError(f"{path} must be an object.")

        for key, value in node.items():
            current_path = f"{path}.{key}"
            if isinstance(value, dict):
                self._validate_messages(value, path=current_path)
            elif not isinstance(value, str):
                raise LocaleDataError(f"{current_path} must be a string.")

    def _validate_enums(self, node: Any, *, path: str) -> None:
        if not isinstance(node, dict):
            raise LocaleDataError(f"{path} must be an object.")

        for enum_key, enum_data in node.items():
            enum_path = f"{path}.{enum_key}"
            if not isinstance(enum_data, dict):
                raise LocaleDataError(f"{enum_path} must be an object.")

            title = enum_data.get("title")
            if title is not None and not isinstance(title, str):
                raise LocaleDataError(f"{enum_path}.title must be a string when present.")

            values = enum_data.get("values")
            if not isinstance(values, dict):
                raise LocaleDataError(f"{enum_path}.values must be an object.")

            for item_key, item_data in values.items():
                item_path = f"{enum_path}.values.{item_key}"
                if not isinstance(item_data, dict):
                    raise LocaleDataError(f"{item_path} must be an object.")
                if not isinstance(item_data.get("label"), str):
                    raise LocaleDataError(f"{item_path}.label must be a string.")
                description = item_data.get("description")
                if description is not None and not isinstance(description, str):
                    raise LocaleDataError(f"{item_path}.description must be a string when present.")
                order = item_data.get("order")
                if order is not None and not isinstance(order, int):
                    raise LocaleDataError(f"{item_path}.order must be an integer when present.")

    def _validate_faqs(self, node: Any, *, path: str) -> None:
        if not isinstance(node, dict):
            raise LocaleDataError(f"{path} must be an object.")

        for section_key, section_data in node.items():
            section_path = f"{path}.{section_key}"
            if not isinstance(section_data, dict):
                raise LocaleDataError(f"{section_path} must be an object.")

            title = section_data.get("title")
            if title is not None and not isinstance(title, str):
                raise LocaleDataError(f"{section_path}.title must be a string when present.")

            items = section_data.get("items")
            if not isinstance(items, dict):
                raise LocaleDataError(f"{section_path}.items must be an object.")

            for item_key, item_data in items.items():
                item_path = f"{section_path}.items.{item_key}"
                if not isinstance(item_data, dict):
                    raise LocaleDataError(f"{item_path} must be an object.")
                if not isinstance(item_data.get("question"), str):
                    raise LocaleDataError(f"{item_path}.question must be a string.")
                if not isinstance(item_data.get("answer"), str):
                    raise LocaleDataError(f"{item_path}.answer must be a string.")
                order = item_data.get("order")
                if order is not None and not isinstance(order, int):
                    raise LocaleDataError(f"{item_path}.order must be an integer when present.")
                tags = item_data.get("tags")
                if tags is not None and (not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags)):
                    raise LocaleDataError(f"{item_path}.tags must be a list of strings when present.")

    def _validate_against_default(self, locale: str, data: dict[str, Any]) -> None:
        default = self.repository.default_locale
        if locale == default:
            return

        default_data = self.repository.load_locale(default)
        self._validate_placeholders_recursively(default_data.get("messages", {}), data.get("messages", {}), "messages")

        if self.require_complete_locales:
            self._ensure_complete_structure(default_data, data, path="root")

    def _validate_placeholders_recursively(self, base_node: Any, target_node: Any, path: str) -> None:
        if isinstance(base_node, dict):
            if not isinstance(target_node, dict):
                return
            for key, child in base_node.items():
                self._validate_placeholders_recursively(child, target_node.get(key), f"{path}.{key}")
            return

        if isinstance(base_node, str) and isinstance(target_node, str):
            base_fields = self._extract_placeholders(base_node)
            target_fields = self._extract_placeholders(target_node)
            if base_fields != target_fields:
                raise PlaceholderError(
                    f"Placeholder mismatch at {path}: expected {sorted(base_fields)}, got {sorted(target_fields)}"
                )

    def _ensure_complete_structure(self, base: Any, target: Any, *, path: str) -> None:
        if isinstance(base, dict):
            if not isinstance(target, dict):
                raise LocaleDataError(f"{path} must be an object.")
            for key, value in base.items():
                if key not in target:
                    raise LocaleDataError(f"Missing key in locale: {path}.{key}")
                self._ensure_complete_structure(value, target[key], path=f"{path}.{key}")

    @staticmethod
    def _extract_placeholders(template: str) -> set[str]:
        names: set[str] = set()
        for _, field_name, _, _ in Formatter().parse(template):
            if not field_name:
                continue
            names.add(field_name.split(".")[0].split("[")[0])
        return names
