from __future__ import annotations

import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from localization import LocaleRenderer, enum_ref, grouped_number, wrapped_date, wrapped_datetime
from localization.exceptions import LocaleDataError, LocaleNotFoundError, MissingTranslationError, PlaceholderError, ValueFormattingError
from localization.formatter import LocaleValueFormatter
from localization.repository import LocaleRepository
from localization.service import I18nService


class OrderStatusEnum(Enum):
    PENDING = "pending"
    CANCELED = 100


class PersianRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"


def test_message_lookup_and_placeholder_rendering(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    assert service.msg("user.greeting", locale="fa", name="Ali") == "سلام Ali"


def test_unknown_locale_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(LocaleNotFoundError):
        service.msg("user.operation_failed", locale="unknown")


def test_non_english_default_locale_works_for_none_locale(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "manifest.json"

    manifest = {
        "default_locale": "fa",
        "locales": {
            "en": {"label": "English", "native_name": "English", "direction": "ltr"},
            "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
        },
    }
    en = {"_meta": {"locale": "en", "version": 1}, "messages": {"x": "Hello"}, "enums": {}, "faqs": {}}
    fa = {"_meta": {"locale": "fa", "version": 1}, "messages": {"x": "سلام"}, "enums": {}, "faqs": {}}

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en), encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps(fa), encoding="utf-8")

    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))
    assert service.msg("x") == "سلام"


def test_nested_placeholders_are_rejected(tmp_path: Path) -> None:
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "manifest.json"

    manifest = {
        "default_locale": "en",
        "locales": {"en": {"label": "English", "native_name": "English", "direction": "ltr"}},
    }
    en = {
        "_meta": {"locale": "en", "version": 1},
        "messages": {"user": {"profile": "Profile {user.name}"}},
        "enums": {},
        "faqs": {},
    }

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en), encoding="utf-8")

    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(PlaceholderError):
        service.msg("user.profile", locale="en", user="Ali")


def test_structured_lookup_uses_uniform_overlay(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    item = service.enum_item("order_status", "pending", locale="fa")
    assert item["label"] == "در انتظار پرداخت"
    assert item["description"] == "Awaiting payment"

    faq = service.faq_item("payment", "refund_time", locale="fa")
    assert faq["question"] == "بازپرداخت چقدر طول می‌کشد؟"
    assert faq["tags"] == ["payment", "refund"]


def test_missing_vs_malformed_errors_are_separate(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(MissingTranslationError):
        service.enum_label("order_status", "missing", locale="en")

    en_path = locales_dir / "en.json"
    payload = json.loads(en_path.read_text(encoding="utf-8"))
    payload["enums"]["order_status"]["values"]["pending"]["label"] = 123
    en_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    repository.clear_cache()

    with pytest.raises(LocaleDataError):
        service.enum_label("order_status", "pending", locale="en")


def test_non_strict_mode_returns_key_for_missing_message(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository, strict_missing_keys=False)

    assert service.msg("user.not_found", locale="fa") == "user.not_found"


def test_wrapped_values_and_renderer_api(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    formatter = LocaleValueFormatter(
        default_now=lambda: datetime(2026, 4, 17, 9, 0, 0, tzinfo=timezone.utc),
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        renderers={"fa": PersianRenderer()},
    )
    service = I18nService(repository, value_formatter=formatter)

    message = service.msg(
        "user.report",
        locale="fa",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=timezone.utc)),
        amount=grouped_number("1234567"),
        status=enum_ref("order_status", OrderStatusEnum.PENDING),
        raw_date=date(2026, 4, 17),
    )

    assert "jalali(2026-04-17" in message
    assert "1,234,567" in message
    assert "در انتظار پرداخت" in message
    assert "2026-04-17" in message


def test_grouped_number_invalid_input_raises_clear_error(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(ValueFormattingError, match="Invalid grouped number"):
        service.msg(
            "user.report",
            locale="en",
            date=wrapped_date(date(2026, 4, 17)),
            dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
            amount=grouped_number("abc"),
            status=enum_ref("order_status", "pending"),
            raw_date=date(2026, 4, 17),
        )
