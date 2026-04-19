from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime
from localization.exceptions import LocaleDataError, LocaleNotFoundError, MissingTranslationError, PlaceholderError, ValueFormattingError
from localization.formatter import LocaleRenderer, LocaleValueFormatter
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

    assert service.msg("user.greeting", locale="en", name="Ali") == "Hello Ali"


def test_message_fallback_uses_overlay_model(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    # missing in en, present in default fa
    assert service.msg("user.operation_failed", locale="en") == "عملیات ناموفق بود."


def test_unknown_locale_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(LocaleNotFoundError):
        service.msg("user.greeting", locale="unknown", name="X")


def test_message_missing_placeholder_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(PlaceholderError):
        service.msg("user.greeting", locale="en")


def test_nested_placeholder_is_rejected_at_runtime(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    repository_data = repository.load_locale("en")
    repository_data["messages"]["user"]["bad"] = "Hello {user.name}"
    repository.save_locale("en", repository_data)

    with pytest.raises(PlaceholderError):
        service.msg("user.bad", locale="en", user_name="Ali")


def test_missing_vs_malformed_errors(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(MissingTranslationError):
        service.msg("user.not_found", locale="en")

    bad = repository.load_locale("en")
    bad["messages"]["user"]["greeting"] = {"oops": 1}
    repository.save_locale("en", bad)
    with pytest.raises(LocaleDataError):
        service.msg("user.greeting", locale="en", name="A")


def test_enum_and_faq_lookup_use_overlay_model(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    item = service.enum_item("order_status", "pending", locale="en")
    assert item["label"] == "Pending payment"
    assert item["description"] == "Awaiting payment"

    faq_item = service.faq_item("payment", "refund_time", locale="en")
    assert faq_item["question"] == "How long does a refund take?"
    assert faq_item["tags"] == ["payment", "refund"]


def test_wrapped_values_use_formatter_pipeline(sample_i18n_files: tuple[Path, Path]) -> None:
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

    assert "jalali(2026-04-17)" in message
    assert "jalali(2026-04-17 12:15:00)" in message
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


def test_enum_reference_uses_enum_name_when_value_is_not_string(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    output = service.msg(
        "user.report",
        locale="en",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
        amount=grouped_number(1000),
        status=enum_ref("order_status", OrderStatusEnum.CANCELED),
        raw_date=date(2026, 4, 17),
    )

    assert "Canceled" in output
