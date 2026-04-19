from __future__ import annotations

import json
from pathlib import Path

import pytest

from localization.exceptions import LocaleDataError, LocaleNotFoundError, ManifestError
from localization.repository import LocaleRepository


def test_repository_accepts_non_english_default_locale(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    assert repository.default_locale == "fa"
    descriptors = repository.get_locale_descriptors()
    assert descriptors["fa"].direction == "rtl"
    assert descriptors["en"].direction == "ltr"


def test_repository_unknown_locale_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    with pytest.raises(LocaleNotFoundError):
        repository.resolve_locale("unknown")


def test_repository_validates_default_locale_exists(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "default_locale": "de",
        "locales": {
            "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
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
        "default_locale": "fa",
        "locales": {
            "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
        },
    }

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "fa.json").write_text("{invalid", encoding="utf-8")

    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    with pytest.raises(LocaleDataError):
        repository.load_locale("fa")


def test_repository_cache_isolation(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path, cache_enabled=True)

    loaded = repository.load_locale("fa")
    loaded["messages"]["user"]["greeting"] = "mutated"

    loaded_again = repository.load_locale("fa")
    assert loaded_again["messages"]["user"]["greeting"] == "سلام {name}"
