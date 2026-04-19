from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
NowProvider = Callable[[], datetime]


class NaiveDatetimePolicy(str, Enum):
    """How timezone-aware converters should handle naive datetimes."""

    KEEP_NAIVE = "keep_naive"
    ASSUME_UTC = "assume_utc"
    ASSUME_SOURCE_TIMEZONE = "assume_source_timezone"


@runtime_checkable
class LocaleDateTimeConverter(Protocol):
    """Contract for locale-specific date/datetime conversion.

    Implementations may apply timezone normalization, calendar conversion, or both.
    """

    def convert_date(self, value: date) -> date: ...

    def convert_datetime(self, value: datetime) -> datetime: ...


class IdentityLocaleConverter:
    """No-op converter used as a predictable fallback."""

    def convert_date(self, value: date) -> date:
        return value

    def convert_datetime(self, value: datetime) -> datetime:
        return value


@dataclass(frozen=True, slots=True)
class TimezoneAwareLocaleConverter(LocaleDateTimeConverter):
    """Converter with explicit timezone normalization behavior.

    - Aware datetimes are converted to `target_timezone` when provided.
    - Naive datetimes follow `naive_policy`.
    - Date conversion is pass-through by default.
    """

    target_timezone: tzinfo | None = None
    naive_policy: NaiveDatetimePolicy = NaiveDatetimePolicy.ASSUME_UTC
    source_timezone: tzinfo | None = None

    def convert_date(self, value: date) -> date:
        return value

    def convert_datetime(self, value: datetime) -> datetime:
        normalized = self._normalize_timezone(value)
        return normalized

    def _normalize_timezone(self, value: datetime) -> datetime:
        aware = value
        if value.tzinfo is None:
            if self.naive_policy is NaiveDatetimePolicy.KEEP_NAIVE:
                return value
            if self.naive_policy is NaiveDatetimePolicy.ASSUME_UTC:
                aware = value.replace(tzinfo=timezone.utc)
            elif self.naive_policy is NaiveDatetimePolicy.ASSUME_SOURCE_TIMEZONE:
                if self.source_timezone is None:
                    raise ValueFormattingError(
                        "Naive datetime policy ASSUME_SOURCE_TIMEZONE requires source_timezone."
                    )
                aware = value.replace(tzinfo=self.source_timezone)

        if self.target_timezone is not None and aware.tzinfo is not None:
            return aware.astimezone(self.target_timezone)
        return aware


@dataclass(frozen=True, slots=True)
class CallableLocaleConverter(LocaleDateTimeConverter):
    """Adapter for legacy callable converters.

    The callable receives either date or datetime and must return the same type.
    """

    converter: Callable[[DateLike], DateLike]

    def convert_date(self, value: date) -> date:
        converted = self.converter(value)
        if not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date for date input.")
        return converted

    def convert_datetime(self, value: datetime) -> datetime:
        converted = self.converter(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted


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
    1) `converters[locale]`
    2) `default_converter`
    3) built-in identity converter (no-op)
    """

    default_now: NowProvider
    converters: dict[str, LocaleDateTimeConverter | Callable[[DateLike], DateLike]] = field(default_factory=dict)
    default_converter: LocaleDateTimeConverter | Callable[[DateLike], DateLike] | None = None
    _identity_converter: LocaleDateTimeConverter = field(default_factory=IdentityLocaleConverter, init=False)

    def __post_init__(self) -> None:
        self.converters = {locale: self._coerce_converter(converter) for locale, converter in self.converters.items()}
        if self.default_converter is not None:
            self.default_converter = self._coerce_converter(self.default_converter)

    def _coerce_converter(
        self, converter: LocaleDateTimeConverter | Callable[[DateLike], DateLike]
    ) -> LocaleDateTimeConverter:
        if isinstance(converter, LocaleDateTimeConverter):
            return converter
        return CallableLocaleConverter(converter=converter)

    def _resolve_converter(self, locale: str) -> LocaleDateTimeConverter:
        if locale in self.converters:
            return self.converters[locale]  # type: ignore[return-value]
        if self.default_converter is not None:
            return self.default_converter  # type: ignore[return-value]
        return self._identity_converter

    def format_datetime(self, value: datetime, *, locale: str, pattern: str = "%Y/%m/%d %H:%M:%S") -> str:
        converted = self._resolve_converter(locale).convert_datetime(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return converted.strftime(pattern)

    def format_date(self, value: date, *, locale: str, pattern: str = "%Y/%m/%d") -> str:
        converted = self._resolve_converter(locale).convert_date(value)
        if isinstance(converted, datetime):
            converted = converted.date()
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
