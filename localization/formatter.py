from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

NowProvider = Callable[[], datetime]


@runtime_checkable
class LocaleRenderer(Protocol):
    """Render normalized temporal values to final localized strings."""

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        """Render date value."""

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        """Render datetime value."""


@dataclass(frozen=True, slots=True)
class StrftimeRenderer:
    """Default renderer based on standard ``strftime`` patterns."""

    default_date_pattern: str = "%Y/%m/%d"
    default_datetime_pattern: str = "%Y/%m/%d %H:%M:%S"

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_date_pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_datetime_pattern)


BUILTIN_TEMPORAL_RENDERER = StrftimeRenderer()


@dataclass(frozen=True, slots=True)
class LocalizedDate:
    """Explicit wrapper for locale-aware date formatting in placeholders."""

    value: date
    pattern: str | None = None


@dataclass(frozen=True, slots=True)
class LocalizedDateTime:
    """Explicit wrapper for locale-aware datetime formatting in placeholders."""

    value: datetime
    pattern: str | None = None


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
    """Formats explicit wrapped values for a locale.

    Temporal values use two explicit stages:
    1) timezone normalization (datetime values only)
    2) locale renderer -> final string

    Timezone resolution order:
    - locale-specific timezone
    - default timezone
    - UTC

    Renderer resolution order:
    - locale-specific renderer
    - default renderer
    - builtin strftime renderer

    Naive datetime behavior:
    - default: left unchanged
    - when ``naive_input_timezone`` is set: naive values are interpreted in that
      timezone then normalized to the resolved target timezone.
    """

    default_now: NowProvider
    renderers: dict[str, LocaleRenderer] | None = None
    default_renderer: LocaleRenderer | None = None
    locale_timezones: dict[str, tzinfo] | None = None
    default_timezone: tzinfo | None = None
    naive_input_timezone: tzinfo | None = None
    _resolved_renderers: dict[str, LocaleRenderer] = field(init=False, repr=False)
    _resolved_default_renderer: LocaleRenderer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._resolved_renderers = dict(self.renderers or {})
        self._resolved_default_renderer = self.default_renderer or BUILTIN_TEMPORAL_RENDERER

    def _resolve_timezone(self, locale: str) -> tzinfo:
        if self.locale_timezones and locale in self.locale_timezones:
            return self.locale_timezones[locale]
        if self.default_timezone is not None:
            return self.default_timezone
        return timezone.utc

    def _normalize_datetime(self, value: datetime, *, locale: str) -> datetime:
        target_tz = self._resolve_timezone(locale)

        if value.tzinfo is None:
            if self.naive_input_timezone is None:
                return value
            value = value.replace(tzinfo=self.naive_input_timezone)

        return value.astimezone(target_tz)

    def _resolve_renderer(self, locale: str) -> LocaleRenderer:
        return self._resolved_renderers.get(locale, self._resolved_default_renderer)

    def format_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        normalized = self._normalize_datetime(value, locale=locale)
        return self._resolve_renderer(locale).render_datetime(normalized, locale=locale, pattern=pattern)

    def format_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return self._resolve_renderer(locale).render_date(value, locale=locale, pattern=pattern)

    def now_as_text(self, *, locale: str, pattern: str | None = None) -> str:
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

        if isinstance(value, float) and not isfinite(value):
            raise ValueFormattingError(f"Invalid grouped number value: {value!r}")

        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueFormattingError(f"Invalid grouped number value: {value!r}") from exc
        return format(decimal_value, "f")


def wrapped_date(value: date, *, pattern: str | None = None) -> LocalizedDate:
    return LocalizedDate(value=value, pattern=pattern)


def wrapped_datetime(value: datetime, *, pattern: str | None = None) -> LocalizedDateTime:
    return LocalizedDateTime(value=value, pattern=pattern)


def grouped_number(value: int | float | Decimal | str) -> GroupedNumber:
    return GroupedNumber(value=value)


def enum_ref(enum_name: str, item: str | Enum) -> EnumReference:
    return EnumReference(enum_name=enum_name, item=item)


WrappedValue = LocalizedDate | LocalizedDateTime | GroupedNumber | EnumReference
