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


class JalaliLikeRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"


def test_message_lookup_and_overlay_fallback(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    # fa is default locale in fixture
    assert service.msg("user.operation_failed", locale="en") == "عملیات ناموفق بود."


def test_unknown_locale_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    with pytest.raises(LocaleNotFoundError):
        service.msg("user.greeting", locale="unknown", name="Ali")


def test_message_missing_placeholder_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    with pytest.raises(PlaceholderError):
        service.msg("user.greeting", locale="en")


def test_message_nested_placeholder_is_rejected() -> None:
    with pytest.raises(PlaceholderError):
        I18nService._ensure_template_context("Hello {user.name}", {"user": "x"}, path="messages.user.greeting")


def test_uniform_overlay_for_enum_and_faq(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    pending = service.enum_item("order_status", "pending", locale="en")
    # label overrides in en, order falls back from default fa
    assert pending["label"] == "Pending payment"
    assert pending["order"] == 10

    faq_item = service.faq_item("payment", "refund_time", locale="en")
    assert faq_item["question"] == "How long does a refund take?"
    assert faq_item["order"] == 20


def test_missing_vs_malformed_errors_are_distinct(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(MissingTranslationError):
        service.enum_label("order_status", "unknown", locale="fa")

    data = repository.load_locale("fa")
    data["enums"]["order_status"]["values"]["pending"]["label"] = {"bad": "type"}
    repository.save_locale("fa", data)

    with pytest.raises(LocaleDataError):
        service.enum_label("order_status", "pending", locale="fa")


def test_strict_and_non_strict_msg_modes(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)

    strict_service = I18nService(repository, strict_missing_keys=True)
    with pytest.raises(MissingTranslationError):
        strict_service.msg("user.not_found", locale="fa")

    non_strict_service = I18nService(repository, strict_missing_keys=False)
    assert non_strict_service.msg("user.not_found", locale="fa") == "user.not_found"


def test_wrapped_values_with_renderer_timezone_pipeline(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    formatter = LocaleValueFormatter(
        default_now=lambda: datetime.now(timezone.utc),
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        default_timezone=timezone.utc,
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

    assert "jalali(2026-04-17 12:15:00)" in message
    assert "1,234,567" in message
    assert "در انتظار پرداخت" in message
    assert "2026-04-17" in message


def test_grouped_number_invalid_input_raises_clear_error(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path))

    with pytest.raises(ValueFormattingError, match="Invalid grouped number"):
        service.msg(
            "user.report",
            locale="fa",
            date=wrapped_date(date(2026, 4, 17)),
            dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
            amount=grouped_number("abc"),
            status=enum_ref("order_status", "pending"),
            raw_date=date(2026, 4, 17),
        )


def test_enum_reference_uses_enum_name_when_value_is_not_string(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    service = I18nService(LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path), strict_missing_keys=False)

    output = service.msg(
        "user.report",
        locale="fa",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
        amount=grouped_number(1000),
        status=enum_ref("order_status", OrderStatusEnum.CANCELED),
        raw_date=date(2026, 4, 17),
    )

    assert "لغو شده" in output
