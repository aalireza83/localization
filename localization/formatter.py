from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Mapping, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
NowProvider = Callable[[], datetime]


@runtime_checkable
class LocaleValueConverter(Protocol):
    """Contract for locale-aware date/datetime conversion.

    Converters are responsible for any locale-specific normalization before
    string formatting, including timezone normalization for datetimes.
    """

    def convert_date(self, value: date, *, locale: str) -> date:
        """Convert a date value for the requested locale."""

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        """Convert a datetime value for the requested locale."""


LegacyConverter = Callable[[DateLike], DateLike]
ConverterLike = LocaleValueConverter | LegacyConverter


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


@dataclass(frozen=True, slots=True)
class IdentityLocaleValueConverter:
    """Default no-op converter used when no locale/default converter exists."""

    def convert_date(self, value: date, *, locale: str) -> date:
        return value

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        return value


@dataclass(frozen=True, slots=True)
class CallableLocaleValueConverter:
    """Adapter for legacy callable converters.

    The same callable is used for both date and datetime conversion so existing
    `converters={"fa": lambda value: ...}` usage remains supported.
    """

    func: LegacyConverter

    def convert_date(self, value: date, *, locale: str) -> date:
        converted = self.func(value)
        if not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date-compatible value for date input.")
        return converted

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        converted = self.func(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted


@dataclass(frozen=True, slots=True)
class TimezoneAwareLocaleValueConverter:
    """Locale converter with explicit timezone normalization rules.

    Rules:
    - Aware datetimes are converted to `target_timezone` when provided.
    - Naive datetimes are treated as:
      - `assume_naive_source_timezone` when configured, then normalized.
      - untouched when no source timezone is configured.
    - Date values are returned unchanged by default.

    This class intentionally handles timezone behavior only. Locale-specific
    calendar conversion can be added by subclassing and overriding
    `convert_date`/`convert_datetime`.
    """

    target_timezone: tzinfo | None = None
    assume_naive_source_timezone: tzinfo | None = None

    def convert_date(self, value: date, *, locale: str) -> date:
        return value

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        normalized = value
        if normalized.tzinfo is None and self.assume_naive_source_timezone is not None:
            normalized = normalized.replace(tzinfo=self.assume_naive_source_timezone)

        if self.target_timezone is None or normalized.tzinfo is None:
            return normalized
        return normalized.astimezone(self.target_timezone)


@dataclass(slots=True)
class LocaleValueFormatter:
    """Formats explicitly wrapped placeholder values for a given locale.

    Converter resolution order is explicit and predictable:
    1. locale-specific converter in `converters`
    2. `default_converter`
    3. built-in no-op `IdentityLocaleValueConverter`
    """

    default_now: NowProvider
    converters: Mapping[str, ConverterLike] | None = None
    default_converter: ConverterLike | None = None
    _resolved_converters: dict[str, LocaleValueConverter] = field(init=False, repr=False)
    _resolved_default_converter: LocaleValueConverter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._resolved_converters = {
            locale: self._normalize_converter(converter)
            for locale, converter in (self.converters or {}).items()
        }
        if self.default_converter is None:
            self._resolved_default_converter = IdentityLocaleValueConverter()
        else:
            self._resolved_default_converter = self._normalize_converter(self.default_converter)

    @staticmethod
    def _normalize_converter(converter: ConverterLike) -> LocaleValueConverter:
        if isinstance(converter, LocaleValueConverter):
            return converter
        if callable(converter):
            return CallableLocaleValueConverter(converter)
        raise ValueFormattingError("Invalid converter configuration. Expected converter object or callable.")

    def _resolve_converter(self, locale: str) -> LocaleValueConverter:
        return self._resolved_converters.get(locale, self._resolved_default_converter)

    def format_datetime(self, value: datetime, *, locale: str, pattern: str = "%Y/%m/%d %H:%M:%S") -> str:
        converted = self._resolve_converter(locale).convert_datetime(value, locale=locale)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted.strftime(pattern)

    def format_date(self, value: date, *, locale: str, pattern: str = "%Y/%m/%d") -> str:
        converted = self._resolve_converter(locale).convert_date(value, locale=locale)
        if not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date-compatible value for date input.")
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
