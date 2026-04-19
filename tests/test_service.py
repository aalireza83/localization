from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pytest

from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime
from localization.exceptions import MissingTranslationError, PlaceholderError, ValueFormattingError
from localization.formatter import LocaleValueFormatter
from localization.repository import LocaleRepository
from localization.service import I18nService


class OrderStatusEnum(Enum):
    PENDING = "pending"
    CANCELED = 100


def test_message_lookup_and_placeholder_rendering(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    assert service.msg("user.greeting", locale="fa", name="Ali") == "سلام Ali"


def test_message_fallback_to_default_locale(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    assert service.msg("user.operation_failed", locale="unknown") == "Operation failed."


def test_message_missing_placeholder_raises(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    with pytest.raises(PlaceholderError):
        service.msg("user.greeting", locale="en")


def test_structured_lookup_merges_defaults(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository)

    item = service.enum_item("order_status", "pending", locale="fa")
    assert item["label"] == "در انتظار پرداخت"
    assert item["description"] == "Awaiting payment"


def test_non_strict_mode_returns_key_for_missing_message(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository, strict_missing_keys=False)

    assert service.msg("user.not_found", locale="fa") == "user.not_found"


def test_strict_mode_raises_for_missing_message(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    service = I18nService(repository, strict_missing_keys=True)

    with pytest.raises(MissingTranslationError):
        service.msg("user.not_found", locale="fa")


def test_wrapped_values_use_locale_from_message_call(sample_i18n_files: tuple[Path, Path]) -> None:
    locales_dir, manifest_path = sample_i18n_files
    repository = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
    formatter = LocaleValueFormatter(
        default_now=lambda: datetime(2026, 4, 17, 9, 0, 0),
        converters={"fa": lambda value: value.replace(year=1405)},
    )
    service = I18nService(repository, value_formatter=formatter)

    message = service.msg(
        "user.report",
        locale="fa",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
        amount=grouped_number("1234567"),
        status=enum_ref("order_status", OrderStatusEnum.PENDING),
        raw_date=date(2026, 4, 17),
    )

    assert "1405/04/17" in message
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
    service = I18nService(repository, strict_missing_keys=False)

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
