from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from localization.editor import LocaleEditor
from localization.exceptions import LocaleEditError, PlaceholderError, ValueFormattingError
from localization.formatter import LocaleRenderer, LocaleValueFormatter, wrapped_date, wrapped_datetime
from localization.repository import LocaleRepository
from localization.validator import LocaleValidator


class PrefixRenderer(LocaleRenderer):
    def __init__(self, *, prefix: str) -> None:
        self.prefix = prefix

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"{self.prefix}:{value.strftime(pattern or '%Y/%m/%d')}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"{self.prefix}:{value.strftime(pattern or '%Y/%m/%d %H:%M:%S')}"


class JalaliLikeRenderer(LocaleRenderer):
    """Test double that demonstrates non-Gregorian final string output behavior."""

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return (
            f"jalali({value.year}-{value.month:02d}-{value.day:02d}"
            f" {value.hour:02d}:{value.minute:02d}:{value.second:02d})"
        )


def test_validator_accepts_valid_locales(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository)

    validator.validate_all()


def test_validator_rejects_nested_placeholders(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "manifest.json"

    manifest = {
        "default_locale": "fa",
        "locales": {
            "fa": {"label": "Farsi", "native_name": "فارسی", "direction": "rtl"},
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
        },
    }

    fa = {
        "_meta": {"locale": "fa", "version": 1},
        "messages": {"user": {"greeting": "سلام {name}"}},
        "enums": {},
        "faqs": {},
    }
    en = {
        "_meta": {"locale": "en", "version": 1},
        "messages": {"user": {"greeting": "Hello {user.name}"}},
        "enums": {},
        "faqs": {},
    }

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps(fa), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en), encoding="utf-8")

    validator = LocaleValidator(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    with pytest.raises(PlaceholderError):
        validator.validate_single_locale("en")


def test_editor_delete_raises_when_path_missing(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    editor = LocaleEditor(repository, LocaleValidator(repository))

    with pytest.raises(LocaleEditError):
        editor.delete_value("fa", "messages.user.missing")


def test_editor_set_and_get_value(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    editor = LocaleEditor(repository, LocaleValidator(repository))

    editor.set_value("fa", "messages.user.operation_failed", "خطا")
    assert editor.get_value("fa", "messages.user.operation_failed") == "خطا"


def test_formatter_timezone_and_renderer_fallbacks() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)

    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        default_timezone=ZoneInfo("America/New_York"),
        renderers={"fa": PrefixRenderer("fa")},
        default_renderer=PrefixRenderer("default"),
    )

    assert formatter.format_datetime(value, locale="fa") == "fa:2026/04/15 12:00:00"
    assert formatter.format_datetime(value, locale="en") == "default:2026/04/15 04:30:00"

def test_formatter_timezone_resolution_locale_then_default_then_utc() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)

    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        default_timezone=ZoneInfo("America/New_York"),
    )

    assert formatter.format_datetime(value, locale="fa") == "2026/04/15 12:00:00"
    assert formatter.format_datetime(value, locale="en") == "2026/04/15 04:30:00"

    utc_only = LocaleValueFormatter(default_now=lambda: value)
    assert utc_only.format_datetime(value, locale="missing") == "2026/04/15 08:30:00"


def test_formatter_naive_datetime_is_untouched_unless_source_timezone_configured() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0)

    untouched = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    )
    assert untouched.format_datetime(value, locale="fa") == "2026/04/15 08:30:00"

    assumed = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        naive_input_timezone=timezone.utc,
    )
    assert assumed.format_datetime(value, locale="fa") == "2026/04/15 12:00:00"


def test_formatter_renderer_fallback_order_locale_then_default_then_builtin() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)

    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        renderers={"fa": PrefixRenderer(prefix="fa")},
        default_renderer=PrefixRenderer(prefix="default"),
    )

    assert formatter.format_datetime(value, locale="fa") == "fa:2026/04/15 08:30:00"
    assert formatter.format_datetime(value, locale="en") == "default:2026/04/15 08:30:00"

    builtin = LocaleValueFormatter(default_now=lambda: value)
    assert builtin.format_datetime(value, locale="en") == "2026/04/15 08:30:00"


def test_formatter_supports_locale_renderer_direct_string_output_for_persian_like_use_case() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)

    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        renderers={"fa": JalaliLikeRenderer()},
    )

    assert formatter.format_datetime(value, locale="fa") == "jalali(2026-04-15 12:00:00)"


def test_formatter_keeps_legacy_converter_support() -> None:
    value = datetime(2026, 4, 15, 12, 30, 0, tzinfo=timezone.utc)

    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    )
    assert formatter.format_datetime(value, locale="fa") == "2026/04/15 08:30:00"

    formatter_with_source = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        naive_input_timezone=timezone.utc,
    )
    assert formatter_with_source.format_datetime(value, locale="fa") == "2026/04/15 12:00:00"


def test_locale_value_formatter_grouped_number() -> None:
    formatter = LocaleValueFormatter(default_now=lambda: datetime(2026, 4, 15, 12, 30, 0))

    assert formatter.format_grouped_number(1234567) == "1,234,567"
    assert formatter.format_grouped_number("1234567.50") == "1,234,567.50"


def test_locale_value_formatter_grouped_number_rejects_invalid_values() -> None:
    formatter = LocaleValueFormatter(default_now=lambda: datetime(2026, 4, 15, 12, 30, 0))

    with pytest.raises(ValueFormattingError):
        formatter.format_grouped_number("not-a-number")


def test_wrappers_use_new_pipeline() -> None:
    value = datetime(2026, 4, 15, 8, 30, 0, tzinfo=timezone.utc)
    formatter = LocaleValueFormatter(
        default_now=lambda: value,
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        renderers={"fa": PrefixRenderer(prefix="fa")},
    )

    wrapped_dt = wrapped_datetime(value)
    wrapped_d = wrapped_date(value.date())

    assert formatter.format_datetime(wrapped_dt.value, locale="fa", pattern=wrapped_dt.pattern) == "fa:2026/04/15 12:00:00"
    assert formatter.format_date(wrapped_d.value, locale="fa", pattern=wrapped_d.pattern) == "fa:2026/04/15"
