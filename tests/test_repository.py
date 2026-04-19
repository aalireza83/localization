from __future__ import annotations

import json
from pathlib import Path

import pytest

from localization.exceptions import LocaleDataError, LocaleNotFoundError, ManifestError
from localization.repository import LocaleRepository


def test_repository_loads_manifest_and_descriptors(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    assert repository.default_locale == "en"
    descriptors = repository.get_locale_descriptors()
    assert descriptors["en"].direction == "ltr"
    assert descriptors["fa"].direction == "rtl"


def test_repository_supports_non_english_default_locale(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "default_locale": "fa",
        "locales": {
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
            "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
        },
    }

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps({"_meta": {"locale": "en", "version": 1}, "messages": {}, "enums": {}, "faqs": {}}), encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps({"_meta": {"locale": "fa", "version": 1}, "messages": {}, "enums": {}, "faqs": {}}), encoding="utf-8")

    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    assert repository.default_locale == "fa"


def test_repository_resolve_locale_raises_for_unknown_locale(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    with pytest.raises(LocaleNotFoundError):
        repository.resolve_locale("unknown")


def test_repository_rejects_manifest_with_missing_default_locale_entry(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "default_locale": "fa",
        "locales": {
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
        },
    }

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ManifestError):
        LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)


def test_repository_raises_for_invalid_locale_json(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "default_locale": "en",
        "locales": {
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
        },
    }

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "en.json").write_text("{invalid", encoding="utf-8")

    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    with pytest.raises(LocaleDataError):
        repository.load_locale("en")


def test_repository_cache_returns_stale_until_clear(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path, cache_enabled=True)

    first = repository.load_locale("en")
    first["messages"]["user"]["operation_failed"] = "mutated in memory"

    en_path = locales_dir / "en.json"
    payload = json.loads(en_path.read_text(encoding="utf-8"))
    payload["messages"]["user"]["operation_failed"] = "Updated on disk"
    en_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cached = repository.load_locale("en")
    assert cached["messages"]["user"]["operation_failed"] == "Operation failed."

    repository.clear_cache()
    fresh = repository.load_locale("en")
    assert fresh["messages"]["user"]["operation_failed"] == "Updated on disk"
