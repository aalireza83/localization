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


def test_repository_resolve_locale_fallbacks_to_default(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    assert repository.resolve_locale("unknown") == "en"

    with pytest.raises(LocaleNotFoundError):
        repository.resolve_locale("unknown", fallback_to_default=False)


def test_repository_rejects_invalid_manifest_default(tmp_path: Path) -> None:
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
