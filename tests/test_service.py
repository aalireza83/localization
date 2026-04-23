from __future__ import annotations

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


class JalaliLikeRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"


def test_message_lookup_uses_default_locale_when_locale_none(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    assert service.msg("user.greeting", name="Ali") == "سلام Ali"


def test_unknown_locale_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    with pytest.raises(LocaleNotFoundError):
        service.msg("user.greeting", locale="de", name="Ali")


def test_message_overlay_fallback_is_consistent(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    # en does not define user.operation_failed in fixture; falls back from default locale fa
    assert service.msg("user.operation_failed", locale="en") == "عملیات ناموفق بود."


def test_missing_and_malformed_errors_are_distinct(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(MissingTranslationError):
        service.enum_label("order_status", "missing", locale="en")

    en_data = repository.load_locale("en")
    en_data["enums"]["order_status"]["values"]["pending"]["label"] = 123
    repository.save_locale("en", en_data)

    with pytest.raises(LocaleDataError):
        service.enum_label("order_status", "pending", locale="en")


def test_placeholder_support_is_top_level_only(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    data = repository.load_locale("en")
    data["messages"]["user"]["greeting"] = "Hello {user.name}"
    repository.save_locale("en", data)

    service = I18nService(repository)

    with pytest.raises(PlaceholderError):
        service.msg("user.greeting", locale="en", user_name="Ali")


def test_enum_and_faq_overlay_use_same_model(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    enum_item = service.enum_item("order_status", "pending", locale="en")
    faq_item = service.faq_item("payment", "refund_time", locale="en")

    assert enum_item["label"] == "Pending payment"
    assert enum_item["description"] == "Awaiting payment"
    # title/tags are missing in en and should fall back from default locale fa where available
    assert service.enum_group("order_status", locale="en")["title"] == "وضعیت سفارش"
    assert faq_item["question"] == "How long does a refund take?"
    assert faq_item["tags"] == ["payment", "refund"]


def test_wrapped_values_use_renderer_pipeline(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    formatter = LocaleValueFormatter(
        default_now=lambda: datetime(2026, 4, 17, 9, 0, 0, tzinfo=timezone.utc),
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        renderers={"fa": JalaliLikeRenderer()},
    )
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path), value_formatter=formatter)

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
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

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
