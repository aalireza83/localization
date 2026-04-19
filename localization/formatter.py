from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
LegacyConverter = Callable[[DateLike], DateLike]
NowProvider = Callable[[], datetime]


@runtime_checkable
class LocaleConverter(Protocol):
    """Contract for locale-specific date and datetime conversion.

    Implementations may apply timezone normalization, calendar conversion, or both.
    """

    def convert_date(self, value: date, *, locale: str) -> date:
        """Convert a date value for the target locale."""

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        """Convert a datetime value for the target locale."""


@dataclass(frozen=True, slots=True)
class IdentityLocaleConverter:
    """No-op converter used as a safe fallback when no converter is configured."""

    def convert_date(self, value: date, *, locale: str) -> date:
        return value

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        return value


IDENTITY_CONVERTER = IdentityLocaleConverter()


@dataclass(frozen=True, slots=True)
class CallableLocaleConverter:
    """Adapter for legacy single-callable converters.

    The callable must accept both ``date`` and ``datetime`` values and must return
    a value of the same kind as the input.
    """

    converter: LegacyConverter

    def convert_date(self, value: date, *, locale: str) -> date:
        converted = self.converter(value)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date for date input.")
        return converted

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        converted = self.converter(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted


@dataclass(frozen=True, slots=True)
class TimezoneLocaleConverter:
    """Timezone-aware converter using standard-library datetime/zoneinfo behavior.

    Rules for naive datetimes:
    - if ``assume_naive_input_timezone`` is ``False`` (default), naive datetimes are
      left naive and are not timezone-normalized.
    - if ``assume_naive_input_timezone`` is ``True``, ``naive_input_timezone`` must
      be provided; naive values are interpreted in that timezone and can then be
      normalized to ``target_timezone``.
    """

    target_timezone: tzinfo | None = None
    assume_naive_input_timezone: bool = False
    naive_input_timezone: tzinfo | None = None

    def __post_init__(self) -> None:
        if self.assume_naive_input_timezone and self.naive_input_timezone is None:
            raise ValueError(
                "naive_input_timezone must be set when assume_naive_input_timezone is True."
            )

    def convert_date(self, value: date, *, locale: str) -> date:
        return value

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        normalized = value

        if normalized.tzinfo is None:
            if not self.assume_naive_input_timezone:
                return normalized
            normalized = normalized.replace(tzinfo=self.naive_input_timezone)

        if self.target_timezone is None:
            return normalized

        return normalized.astimezone(self.target_timezone)


@dataclass(frozen=True, slots=True)
class LocalizedDate:
    """Explicit wrapper for locale-aware date formatting in placeholders."""

    value: date
    pattern: str = "%Y/%m/%d"


@dataclass(frozen=True, slots=True)
class LocalizedDateTime:
    """Explicit wrapper for locale-aware datetime formatting in placeholders."""

    value: datetime
    pattern: str = "%Y/%m/%d %H:%M:%S"


@dataclass(frozen=True, slots=True)
class GroupedNumber:
    """Explicit wrapper for grouped-number formatting in placeholders."""

    value: int | float | Decimal | str


@dataclass(frozen=True, slots=True)
class EnumReference:
    """Explicit wrapper for enum label resolution in placeholders."""

    enum_name: str
    item: str | Enum

    def item_key(self) -> str:
        if isinstance(self.item, Enum):
            enum_value = self.item.value
            if isinstance(enum_value, str) and enum_value.strip():
                return enum_value
            return self.item.name.lower()
        return str(self.item)


@dataclass(slots=True)
class LocaleValueFormatter:
    """Formats explicitly wrapped placeholder values for a given locale.

    Converter resolution order:
    1. Locale-specific converter from ``converters``
    2. ``default_converter``
    3. Built-in no-op converter (identity behavior)
    """

    default_now: NowProvider
    converters: dict[str, LocaleConverter | LegacyConverter] | None = None
    default_converter: LocaleConverter | LegacyConverter | None = None

    def __post_init__(self) -> None:
        if self.converters is not None:
            self.converters = {locale: self._coerce_converter(converter) for locale, converter in self.converters.items()}
        self.default_converter = self._coerce_converter(self.default_converter)

    def _coerce_converter(self, converter: LocaleConverter | LegacyConverter | None) -> LocaleConverter | None:
        if converter is None:
            return None
        if isinstance(converter, LocaleConverter):
            return converter
        return CallableLocaleConverter(converter)

    def _resolve_converter(self, locale: str) -> LocaleConverter:
        if self.converters and locale in self.converters:
            return self.converters[locale]
        if self.default_converter is not None:
            return self.default_converter
        return IDENTITY_CONVERTER

    def format_datetime(self, value: datetime, *, locale: str, pattern: str = "%Y/%m/%d %H:%M:%S") -> str:
        converted = self._resolve_converter(locale).convert_datetime(value, locale=locale)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted.strftime(pattern)

    def format_date(self, value: date, *, locale: str, pattern: str = "%Y/%m/%d") -> str:
        converted = self._resolve_converter(locale).convert_date(value, locale=locale)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date for date input.")
        return converted.strftime(pattern)

    def now_as_text(self, *, locale: str, pattern: str = "%Y/%m/%d %H:%M:%S") -> str:
        return self.format_datetime(self.default_now(), locale=locale, pattern=pattern)

    def format_grouped_number(self, value: int | float | Decimal | str) -> str:
        if isinstance(value, bool):
            raise ValueFormattingError("Grouped number value cannot be a boolean.")

        if isinstance(value, int):
            return f"{value:,}"

        normalized = self._normalize_numeric_string(value)
        sign = ""
        if normalized.startswith("-"):
            sign = "-"
            normalized = normalized[1:]

        if "." in normalized:
            int_part, frac_part = normalized.split(".", 1)
            grouped = f"{int(int_part):,}"
            return f"{sign}{grouped}.{frac_part}" if frac_part else f"{sign}{grouped}"

        return f"{sign}{int(normalized):,}"

    def _normalize_numeric_string(self, value: int | float | Decimal | str) -> str:
        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if not text:
                raise ValueFormattingError("Grouped number string cannot be empty.")
            try:
                decimal_value = Decimal(text)
            except InvalidOperation as exc:
                raise ValueFormattingError(f"Invalid grouped number string: {value!r}") from exc
            return format(decimal_value, "f")

        if isinstance(value, float):
            if not isfinite(value):
                raise ValueFormattingError(f"Invalid grouped number value: {value!r}")

        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueFormattingError(f"Invalid grouped number value: {value!r}") from exc
        return format(decimal_value, "f")


def wrapped_date(value: date, *, pattern: str = "%Y/%m/%d") -> LocalizedDate:
    """Create an explicit wrapped date placeholder value."""

    return LocalizedDate(value=value, pattern=pattern)


def wrapped_datetime(value: datetime, *, pattern: str = "%Y/%m/%d %H:%M:%S") -> LocalizedDateTime:
    """Create an explicit wrapped datetime placeholder value."""

    return LocalizedDateTime(value=value, pattern=pattern)


def grouped_number(value: int | float | Decimal | str) -> GroupedNumber:
    """Create an explicit wrapped grouped-number placeholder value."""

    return GroupedNumber(value=value)


def enum_ref(enum_name: str, item: str | Enum) -> EnumReference:
    """Create an explicit wrapped enum label placeholder value."""

    return EnumReference(enum_name=enum_name, item=item)


WrappedValue = LocalizedDate | LocalizedDateTime | GroupedNumber | EnumReference
