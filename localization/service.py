from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from string import Formatter
from typing import Any, Callable

from localization._paths import get_path
from localization.exceptions import LocaleDataError, MissingTranslationError, PlaceholderError
from localization.formatter import EnumReference, GroupedNumber, LocaleValueFormatter, LocalizedDate, LocalizedDateTime
from localization.repository import LocaleRepository

ContextProvider = Callable[[], dict[str, Any]]


class I18nService:
    """High-level API for message and structured translation lookup."""

    def __init__(
        self,
        repository: LocaleRepository,
        *,
        default_context_provider: ContextProvider | None = None,
        strict_missing_keys: bool = True,
        value_formatter: LocaleValueFormatter | None = None,
    ) -> None:
        self.repository = repository
        self.default_context_provider = default_context_provider or (lambda: {})
        self.strict_missing_keys = strict_missing_keys
        self.value_formatter = value_formatter or LocaleValueFormatter(default_now=lambda: datetime.now(timezone.utc))

    def msg(self, key: str, *, locale: str | None = None, **kwargs: Any) -> str:
        path = f"messages.{key}"
        template = self._get_effective_value(path, locale=locale)

        if template is None:
            if self.strict_missing_keys:
                raise MissingTranslationError(f"Translation key not found: {path}")
            return key
        if not isinstance(template, str):
            raise LocaleDataError(f"Expected string at '{path}', got {type(template).__name__}.")

        resolved_locale = self.repository.resolve_locale(locale)
        context = {**self.default_context_provider(), **kwargs}
        self._ensure_template_context(template, context, path=path)
        formatted_context = self._resolve_wrapped_values(context, locale=resolved_locale)
        return template.format(**formatted_context)

    def enum_group(self, enum_name: str, *, locale: str | None = None) -> dict[str, Any]:
        path = f"enums.{enum_name}"
        return self._require_object(self._get_effective_value(path, locale=locale), path)

    def enum_values(self, enum_name: str, *, locale: str | None = None) -> dict[str, dict[str, Any]]:
        path = f"enums.{enum_name}.values"
        return self._require_object(self._get_effective_value(path, locale=locale), path)

    def enum_item(self, enum_name: str, item_key: str, *, locale: str | None = None) -> dict[str, Any]:
        path = f"enums.{enum_name}.values.{item_key}"
        return self._require_object(self._get_effective_value(path, locale=locale), path)

    def enum_label(self, enum_name: str, item_key: str, *, locale: str | None = None) -> str:
        path = f"enums.{enum_name}.values.{item_key}.label"
        return self._require_string(self._get_effective_value(path, locale=locale), path)

    def faq_section(self, section_key: str, *, locale: str | None = None) -> dict[str, Any]:
        path = f"faqs.{section_key}"
        return self._require_object(self._get_effective_value(path, locale=locale), path)

    def faq_items(self, section_key: str, *, locale: str | None = None) -> list[dict[str, Any]]:
        path = f"faqs.{section_key}.items"
        items = self._require_object(self._get_effective_value(path, locale=locale), path)
        normalized: list[dict[str, Any]] = []
        for key, value in items.items():
            if not isinstance(value, dict):
                raise LocaleDataError(f"Expected object at '{path}.{key}', got {type(value).__name__}.")
            normalized.append({"id": key, **value})
        return sorted(normalized, key=lambda item: item.get("order", 2_147_483_647))

    def faq_item(self, section_key: str, item_key: str, *, locale: str | None = None) -> dict[str, Any]:
        path = f"faqs.{section_key}.items.{item_key}"
        return self._require_object(self._get_effective_value(path, locale=locale), path)

    def faq_answer(self, section_key: str, item_key: str, *, locale: str | None = None) -> str:
        path = f"faqs.{section_key}.items.{item_key}.answer"
        return self._require_string(self._get_effective_value(path, locale=locale), path)

    def faq_question(self, section_key: str, item_key: str, *, locale: str | None = None) -> str:
        path = f"faqs.{section_key}.items.{item_key}.question"
        return self._require_string(self._get_effective_value(path, locale=locale), path)

    def _resolve_wrapped_values(self, context: dict[str, Any], *, locale: str) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in context.items():
            resolved[key] = self._resolve_wrapped_value(value, locale=locale)
        return resolved

    def _resolve_wrapped_value(self, value: Any, *, locale: str) -> Any:
        if isinstance(value, LocalizedDateTime):
            return self.value_formatter.format_datetime(value.value, locale=locale, pattern=value.pattern)
        if isinstance(value, LocalizedDate):
            return self.value_formatter.format_date(value.value, locale=locale, pattern=value.pattern)
        if isinstance(value, GroupedNumber):
            return self.value_formatter.format_grouped_number(value.value)
        if isinstance(value, EnumReference):
            return self.enum_label(value.enum_name, value.item_key(), locale=locale)
        return value

    def _effective_locale_data(self, locale: str | None) -> dict[str, Any]:
        resolved = self.repository.resolve_locale(locale)
        default_locale = self.repository.default_locale
        default_data = self.repository.load_locale(default_locale)
        if resolved == default_locale:
            return default_data

        requested_data = self.repository.load_locale(resolved)
        merged = self._deep_merge(default_data, requested_data)
        if not isinstance(merged, dict):
            raise LocaleDataError("Effective locale data must be an object.")
        return merged

    def _get_effective_value(self, path: str, *, locale: str | None) -> Any | None:
        return get_path(self._effective_locale_data(locale), path)

    def _require_object(self, value: Any | None, path: str) -> dict[str, Any]:
        if value is None:
            raise MissingTranslationError(f"Translation key not found: {path}")
        if not isinstance(value, dict):
            raise LocaleDataError(f"Expected object at '{path}', got {type(value).__name__}.")
        return value

    def _require_string(self, value: Any | None, path: str) -> str:
        if value is None:
            raise MissingTranslationError(f"Translation key not found: {path}")
        if not isinstance(value, str):
            raise LocaleDataError(f"Expected string at '{path}', got {type(value).__name__}.")
        return value

    def _deep_merge(self, base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            result = deepcopy(base)
            for key, value in override.items():
                if key in result:
                    result[key] = self._deep_merge(result[key], value)
                else:
                    result[key] = deepcopy(value)
            return result

        if isinstance(override, list):
            return deepcopy(override)

        return deepcopy(override)

    @staticmethod
    def _ensure_template_context(template: str, context: dict[str, Any], *, path: str) -> None:
        required: set[str] = set()

        for _, field_name, _, _ in Formatter().parse(template):
            if not field_name:
                continue
            if "." in field_name or "[" in field_name or "]" in field_name:
                raise PlaceholderError(
                    f"Unsupported placeholder at '{path}': '{field_name}'. "
                    "Only top-level placeholders like '{name}' are supported."
                )
            required.add(field_name)

        missing = sorted(required - set(context))
        if missing:
            raise PlaceholderError(f"Missing placeholders for '{path}': {missing}")
