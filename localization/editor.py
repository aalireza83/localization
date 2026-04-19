from __future__ import annotations

from typing import Any

from localization._paths import delete_path, get_path, set_path, split_path
from localization.exceptions import LocaleEditError
from localization.repository import LocaleRepository
from localization.validator import LocaleValidator


class LocaleEditor:
    """Edits locale values by dot path and validates before save."""

    PROTECTED_PREFIXES = {"_meta"}

    def __init__(self, repository: LocaleRepository, validator: LocaleValidator) -> None:
        self.repository = repository
        self.validator = validator

    def get_value(self, locale: str, path: str) -> Any | None:
        data = self.repository.load_locale(locale)
        return get_path(data, path)

    def set_value(self, locale: str, path: str, value: Any) -> None:
        self._ensure_editable(path)
        resolved = self.repository.resolve_locale(locale)
        data = self.repository.load_locale(resolved)

        try:
            set_path(data, path, value)
        except ValueError as exc:
            raise LocaleEditError(str(exc)) from exc

        self.validator.validate_single_locale_data(resolved, data)
        self.repository.save_locale(resolved, data)

    def delete_value(self, locale: str, path: str) -> None:
        self._ensure_editable(path)
        resolved = self.repository.resolve_locale(locale)
        data = self.repository.load_locale(resolved)

        deleted = delete_path(data, path)
        if not deleted:
            raise LocaleEditError(f"Path not found: {path}")

        self.validator.validate_single_locale_data(resolved, data)
        self.repository.save_locale(resolved, data)

    def _ensure_editable(self, path: str) -> None:
        try:
            parts = split_path(path)
        except ValueError as exc:
            raise LocaleEditError(str(exc)) from exc

        if parts[0] in self.PROTECTED_PREFIXES:
            raise LocaleEditError(f"Protected path cannot be edited: {path}")
