from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from localization.editor import LocaleEditor
from localization.exceptions import LocaleEditError, PlaceholderError, ValueFormattingError
from localization.formatter import LocaleValueFormatter
from localization.repository import LocaleRepository
from localization.validator import LocaleValidator


class JalaliStubRenderer:
    def render_date(self, value, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali-date({locale}):{value.isoformat()}"

    def render_datetime(self, value, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali-datetime({locale}):{value.isoformat()}"


def test_validator_accepts_valid_locales(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository)

    validator.validate_all()


def test_validator_detects_placeholder_mismatch(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "manifest.json"

    manifest = {
        "default_locale": "en",
        "locales": {
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
            "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
        },
    }

    en = {
        "_meta": {"locale": "en", "version": 1},
        "messages": {"user": {"greeting": "Hello {name}"}},
        "enums": {},
        "faqs": {},
    }

    fa = {
        "_meta": {"locale": "fa", "version": 1},
        "messages": {"user": {"greeting": "سلام {username}"}},
        "enums": {},
        "faqs": {},
    }

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en), encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps(fa), encoding="utf-8")

    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository)

    with pytest.raises(PlaceholderError):
        validator.validate_single_locale("fa")


def test_editor_set_and_get_value(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository)
    editor = LocaleEditor(repository, validator)

    editor.set_value("fa", "messages.user.operation_failed", "خطا")
    assert editor.get_value("fa", "messages.user.operation_failed") == "خطا"


def test_editor_rejects_meta_updates(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository)
    editor = LocaleEditor(repository, validator)

    with pytest.raises(LocaleEditError):
        editor.set_value("fa", "_meta.version", 2)


def test_formatter_legacy_converter_compatibility() -> None:
    value = datetime(2026, 4, 15, 12, 30, 0, tzinfo=timezone.utc)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        renderers={"fa": lambda dt: dt.replace(year=2000)},
    )

    assert formatter.format_datetime(value, locale="fa") == "2000/04/15 12:30:00"


def test_formatter_timezone_resolution_locale_then_default_then_utc() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        default_timezone=ZoneInfo("Europe/London"),
    )

    assert formatter.format_datetime(value, locale="fa") == "2026/04/15 12:00:00"
    assert formatter.format_datetime(value, locale="en") == "2026/04/15 09:30:00"

    utc_fallback = LocaleValueFormatter(default_now=lambda: value)
    assert utc_fallback.format_datetime(value, locale="unknown") == "2026/04/15 08:30:00"


def test_formatter_naive_datetime_is_untouched_by_default() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    )

    assert formatter.format_datetime(value, locale="fa") == "2026/04/15 08:30:00"


def test_formatter_naive_datetime_assumed_source_timezone_when_configured() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        assume_naive_input_timezone=True,
        naive_input_timezone=timezone.utc,
    )

    assert formatter.format_datetime(value, locale="fa") == "2026/04/15 12:00:00"


def test_formatter_renderer_fallback_order() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        renderers={"fa": JalaliStubRenderer()},
        default_renderer=lambda dt: dt,
    )

    assert formatter.format_datetime(value, locale="fa") == "jalali-datetime(fa):2026-04-15T08:30:00+00:00"
    assert formatter.format_datetime(value, locale="en") == "2026/04/15 08:30:00"


def test_formatter_date_uses_same_pipeline_and_custom_renderer() -> None:
    formatter = LocaleValueFormatter(
        default_now=lambda: datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc),
        renderers={"fa": JalaliStubRenderer()},
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    )

    assert formatter.format_date(datetime(2026, 4, 15).date(), locale="fa") == "jalali-date(fa):2026-04-15"


def test_locale_value_formatter_grouped_number() -> None:
    formatter = LocaleValueFormatter(default_now=lambda: datetime(2026, 4, 15, 12, 30, 0))

    assert formatter.format_grouped_number(1234567) == "1,234,567"
    assert formatter.format_grouped_number("1234567.50") == "1,234,567.50"


def test_locale_value_formatter_grouped_number_rejects_invalid_values() -> None:
    formatter = LocaleValueFormatter(default_now=lambda: datetime(2026, 4, 15, 12, 30, 0))

    with pytest.raises(ValueFormattingError):
        formatter.format_grouped_number("not-a-number")


def test_formatter_raises_when_naive_assumption_lacks_source_timezone() -> None:
    with pytest.raises(ValueError):
        LocaleValueFormatter(
            default_now=lambda: datetime(2026, 4, 15, 12, 30, 0),
            assume_naive_input_timezone=True,
        )
