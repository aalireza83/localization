from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
LegacyConverter = Callable[[DateLike], DateLike]
NowProvider = Callable[[], datetime]


@runtime_checkable
class TemporalRenderer(Protocol):
    """Contract for locale-aware temporal rendering.

    Implementations receive values after timezone normalization and return final strings.
    """

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        """Render a date value as the final string."""

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        """Render a datetime value as the final string."""


@dataclass(frozen=True, slots=True)
class StrftimeRenderer:
    """Built-in renderer that uses ``strftime`` for date and datetime output."""

    default_date_pattern: str = "%Y/%m/%d"
    default_datetime_pattern: str = "%Y/%m/%d %H:%M:%S"

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_date_pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_datetime_pattern)


BUILTIN_RENDERER = StrftimeRenderer()


@dataclass(frozen=True, slots=True)
class ConverterRendererAdapter:
    """Backward-compatible adapter for legacy date/datetime converters.

    This adapter runs a legacy converter then delegates final string rendering to
    ``delegate_renderer`` (defaults to ``StrftimeRenderer``).
    """

    converter: LegacyConverter
    delegate_renderer: TemporalRenderer = BUILTIN_RENDERER

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter(value)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date for date input.")
        return self.delegate_renderer.render_date(converted, locale=locale, pattern=pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return self.delegate_renderer.render_datetime(converted, locale=locale, pattern=pattern)


@dataclass(frozen=True, slots=True)
class LocalizedDate:
    """Explicit wrapper for locale-aware date formatting in placeholders."""

    value: date
    pattern: str | None = "%Y/%m/%d"


@dataclass(frozen=True, slots=True)
class LocalizedDateTime:
    """Explicit wrapper for locale-aware datetime formatting in placeholders."""

    value: datetime
    pattern: str | None = "%Y/%m/%d %H:%M:%S"


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
    """Formats explicitly wrapped placeholder values using a two-stage pipeline.

    Stage 1: timezone normalization
      - resolve timezone by locale -> default_timezone -> UTC
      - aware datetimes are normalized via ``astimezone``
      - naive datetimes are untouched by default; optionally interpret in
        ``naive_input_timezone`` when ``assume_naive_input_timezone=True``

    Stage 2: temporal rendering
      - resolve renderer by locale -> default_renderer -> built-in strftime renderer
      - render normalized value to final string
    """

    default_now: NowProvider
    renderers: dict[str, TemporalRenderer | LegacyConverter] | None = None
    default_renderer: TemporalRenderer | LegacyConverter | None = None
    locale_timezones: dict[str, tzinfo] | None = None
    default_timezone: tzinfo | None = None
    assume_naive_input_timezone: bool = False
    naive_input_timezone: tzinfo | None = None
    # Backward-compatible aliases for previous API
    converters: dict[str, TemporalRenderer | LegacyConverter] | None = None
    default_converter: TemporalRenderer | LegacyConverter | None = None

    def __post_init__(self) -> None:
        if self.assume_naive_input_timezone and self.naive_input_timezone is None:
            raise ValueError("naive_input_timezone must be set when assume_naive_input_timezone is True.")

        if self.renderers is None and self.converters is not None:
            self.renderers = self.converters
        if self.default_renderer is None and self.default_converter is not None:
            self.default_renderer = self.default_converter

        if self.renderers is not None:
            self.renderers = {
                locale: self._coerce_renderer(renderer)
                for locale, renderer in self.renderers.items()
            }
        self.default_renderer = self._coerce_renderer(self.default_renderer)

    def _coerce_renderer(self, renderer: TemporalRenderer | LegacyConverter | None) -> TemporalRenderer | None:
        if renderer is None:
            return None
        if isinstance(renderer, TemporalRenderer):
            return renderer
        return ConverterRendererAdapter(renderer)

    def _resolve_timezone(self, locale: str) -> tzinfo:
        if self.locale_timezones and locale in self.locale_timezones:
            return self.locale_timezones[locale]
        if self.default_timezone is not None:
            return self.default_timezone
        return timezone.utc

    def _normalize_date(self, value: date, *, locale: str) -> date:
        # Date has no timezone; this keeps a coherent stage-1 pipeline for both types.
        _ = self._resolve_timezone(locale)
        return value

    def _normalize_datetime(self, value: datetime, *, locale: str) -> datetime:
        target_timezone = self._resolve_timezone(locale)
        if value.tzinfo is not None:
            return value.astimezone(target_timezone)

        if not self.assume_naive_input_timezone:
            return value

        aware = value.replace(tzinfo=self.naive_input_timezone)
        return aware.astimezone(target_timezone)

    def _resolve_renderer(self, locale: str) -> TemporalRenderer:
        if self.renderers and locale in self.renderers:
            return self.renderers[locale]
        if self.default_renderer is not None:
            return self.default_renderer
        return BUILTIN_RENDERER

    def format_datetime(self, value: datetime, *, locale: str, pattern: str | None = "%Y/%m/%d %H:%M:%S") -> str:
        normalized = self._normalize_datetime(value, locale=locale)
        return self._resolve_renderer(locale).render_datetime(normalized, locale=locale, pattern=pattern)

    def format_date(self, value: date, *, locale: str, pattern: str | None = "%Y/%m/%d") -> str:
        normalized = self._normalize_date(value, locale=locale)
        return self._resolve_renderer(locale).render_date(normalized, locale=locale, pattern=pattern)

    def now_as_text(self, *, locale: str, pattern: str | None = "%Y/%m/%d %H:%M:%S") -> str:
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


def wrapped_date(value: date, *, pattern: str | None = "%Y/%m/%d") -> LocalizedDate:
    """Create an explicit wrapped date placeholder value."""

    return LocalizedDate(value=value, pattern=pattern)


def wrapped_datetime(value: datetime, *, pattern: str | None = "%Y/%m/%d %H:%M:%S") -> LocalizedDateTime:
    """Create an explicit wrapped datetime placeholder value."""

    return LocalizedDateTime(value=value, pattern=pattern)


def grouped_number(value: int | float | Decimal | str) -> GroupedNumber:
    """Create an explicit wrapped grouped-number placeholder value."""

    return GroupedNumber(value=value)


def enum_ref(enum_name: str, item: str | Enum) -> EnumReference:
    """Create an explicit wrapped enum label placeholder value."""

    return EnumReference(enum_name=enum_name, item=item)


WrappedValue = LocalizedDate | LocalizedDateTime | GroupedNumber | EnumReference
