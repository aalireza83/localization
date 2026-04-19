from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from localization.exceptions import LocaleDataError, LocaleNotFoundError, ManifestError
from localization.schemas import LocaleDescriptor, ManifestData


class LocaleRepository:
    """Loads and persists manifest and locale JSON documents from the filesystem."""

    def __init__(self, base_dir: str | Path, manifest_path: str | Path, *, cache_enabled: bool = True) -> None:
        self.base_dir = Path(base_dir)
        self.manifest_path = Path(manifest_path)
        self.cache_enabled = cache_enabled
        self._cache: dict[str, dict[str, Any]] = {}
        self._manifest: ManifestData = self._load_manifest()

    @property
    def default_locale(self) -> str:
        return self._manifest["default_locale"]

    def locale_exists(self, locale: str) -> bool:
        return locale in self._manifest["locales"]

    def resolve_locale(self, locale: str | None) -> str:
        if locale is None:
            return self.default_locale

        normalized = locale.strip()
        if not normalized:
            raise LocaleNotFoundError("Locale cannot be empty.")
        if self.locale_exists(normalized):
            return normalized
        raise LocaleNotFoundError(f"Locale '{locale}' is not declared in the manifest.")

    def get_locale_descriptors(self) -> dict[str, LocaleDescriptor]:
        descriptors: dict[str, LocaleDescriptor] = {}
        for code, payload in self._manifest["locales"].items():
            direction = payload.get("direction", "ltr")
            descriptors[code] = LocaleDescriptor(
                code=code,
                label=payload.get("label", code),
                native_name=payload.get("native_name", code),
                direction="rtl" if direction == "rtl" else "ltr",
            )
        return descriptors

    def locale_path(self, locale: str) -> Path:
        return self.base_dir / f"{locale}.json"

    def load_locale(self, locale: str | None) -> dict[str, Any]:
        resolved = self.resolve_locale(locale)
        if self.cache_enabled and resolved in self._cache:
            return deepcopy(self._cache[resolved])

        path = self.locale_path(resolved)
        if not path.is_file():
            raise LocaleNotFoundError(f"Locale file not found for '{resolved}': {path}")

        data = self._load_json_file(path)
        if not isinstance(data, dict):
            raise LocaleDataError(f"Locale file must contain a JSON object: {path}")

        if self.cache_enabled:
            self._cache[resolved] = deepcopy(data)
        return deepcopy(data)

    def save_locale(self, locale: str, data: dict[str, Any]) -> None:
        resolved = self.resolve_locale(locale)
        path = self.locale_path(resolved)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")

        if self.cache_enabled:
            self._cache[resolved] = deepcopy(data)

    def clear_cache(self) -> None:
        self._cache.clear()

    def _load_manifest(self) -> ManifestData:
        if not self.manifest_path.is_file():
            raise ManifestError(f"Manifest file not found: {self.manifest_path}")

        raw = self._load_json_file(self.manifest_path)
        if not isinstance(raw, dict):
            raise ManifestError("Manifest root must be a JSON object.")

        default_locale = raw.get("default_locale")
        locales = raw.get("locales")

        if not isinstance(default_locale, str) or not default_locale.strip():
            raise ManifestError("Manifest must define a non-empty string 'default_locale'.")
        default_locale = default_locale.strip()

        if not isinstance(locales, dict) or not locales:
            raise ManifestError("Manifest must define a non-empty 'locales' object.")
        if default_locale not in locales:
            raise ManifestError("Manifest 'default_locale' must be declared under 'locales'.")

        for locale_code, descriptor in locales.items():
            if not isinstance(locale_code, str) or not locale_code.strip():
                raise ManifestError("Manifest locale codes must be non-empty strings.")
            if not isinstance(descriptor, dict):
                raise ManifestError(f"Manifest entry for locale '{locale_code}' must be an object.")

            direction = descriptor.get("direction")
            if direction is not None and direction not in {"ltr", "rtl"}:
                raise ManifestError(
                    f"Invalid direction for locale '{locale_code}': {direction!r}. Use 'ltr' or 'rtl'."
                )

        return {"default_locale": default_locale, "locales": locales}

    @staticmethod
    def _load_json_file(path: Path) -> Any:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise LocaleDataError(f"Invalid JSON in file '{path}': {exc}") from exc
