from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
LegacyCallableConverter = Callable[[DateLike], DateLike]
NowProvider = Callable[[], datetime]


@runtime_checkable
class LocaleRenderer(Protocol):
    """Contract for rendering localized temporal values to final strings."""

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        """Render a date for a locale."""

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        """Render a datetime for a locale."""


@runtime_checkable
class LegacyLocaleConverter(Protocol):
    """Backward-compatible converter contract from the older formatter design."""

    def convert_date(self, value: date, *, locale: str) -> date:
        """Convert a date value for a locale."""

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        """Convert a datetime value for a locale."""


@dataclass(frozen=True, slots=True)
class StrftimeRenderer:
    """Built-in fallback renderer using strftime patterns."""

    default_date_pattern: str = "%Y/%m/%d"
    default_datetime_pattern: str = "%Y/%m/%d %H:%M:%S"

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_date_pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_datetime_pattern)


BUILTIN_RENDERER = StrftimeRenderer()


@dataclass(frozen=True, slots=True)
class CallableLocaleConverter:
    """Adapter for legacy callable converters that accept date | datetime."""

    converter: LegacyCallableConverter

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
class ConverterRendererAdapter:
    """Adapts legacy converters into the new render-to-string contract.

    Conversion runs after timezone normalization and before final rendering.
    """

    converter: LegacyLocaleConverter
    fallback_renderer: LocaleRenderer = BUILTIN_RENDERER

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter.convert_date(value, locale=locale)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Date converter must return date for date input.")
        return self.fallback_renderer.render_date(converted, locale=locale, pattern=pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter.convert_datetime(value, locale=locale)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Datetime converter must return datetime for datetime input.")
        return self.fallback_renderer.render_datetime(converted, locale=locale, pattern=pattern)


RendererLike = LocaleRenderer | LegacyLocaleConverter | LegacyCallableConverter


@dataclass(frozen=True, slots=True)
class TimezoneLocaleConverter:
    """Backward-compatible legacy converter with timezone normalization."""

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


LocaleConverter = LegacyLocaleConverter



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
    """Formats wrapped values using an explicit two-stage temporal pipeline.

    Stage 1 (datetime only): timezone normalization.
    Stage 2: locale rendering to final string.

    Timezone resolution order:
    1. ``locale_timezones[locale]``
    2. ``default_timezone``
    3. UTC

    Renderer resolution order:
    1. ``renderers[locale]``
    2. ``default_renderer``
    3. built-in ``StrftimeRenderer``

    Naive datetimes are left untouched by default. If ``naive_input_timezone`` is
    configured, naive values are interpreted in that timezone and then normalized.
    """

    default_now: NowProvider
    renderers: dict[str, RendererLike] | None = None
    default_renderer: RendererLike | None = None
    locale_timezones: dict[str, tzinfo] | None = None
    default_timezone: tzinfo | None = None
    naive_input_timezone: tzinfo | None = None
    converters: dict[str, RendererLike] | None = None
    default_converter: RendererLike | None = None
    _resolved_renderers: dict[str, LocaleRenderer] = field(init=False, repr=False)
    _resolved_default_renderer: LocaleRenderer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        merged_renderers: dict[str, RendererLike] = {}
        if self.converters:
            merged_renderers.update(self.converters)
        if self.renderers:
            merged_renderers.update(self.renderers)

        self._resolved_renderers = {
            locale: self._coerce_renderer(renderer)
            for locale, renderer in merged_renderers.items()
        }

        default_like = self.default_renderer if self.default_renderer is not None else self.default_converter
        if default_like is None:
            self._resolved_default_renderer = BUILTIN_RENDERER
        else:
            self._resolved_default_renderer = self._coerce_renderer(default_like)

    def _coerce_renderer(self, renderer: RendererLike) -> LocaleRenderer:
        if isinstance(renderer, LocaleRenderer):
            return renderer

        converter: LegacyLocaleConverter
        if isinstance(renderer, LegacyLocaleConverter):
            converter = renderer
        else:
            converter = CallableLocaleConverter(renderer)
        return ConverterRendererAdapter(converter=converter, fallback_renderer=BUILTIN_RENDERER)

    def _resolve_timezone(self, locale: str) -> tzinfo:
        if self.locale_timezones and locale in self.locale_timezones:
            return self.locale_timezones[locale]
        if self.default_timezone is not None:
            return self.default_timezone
        return timezone.utc

    def _normalize_datetime(self, value: datetime, *, locale: str) -> datetime:
        target_timezone = self._resolve_timezone(locale)

        if value.tzinfo is None:
            if self.naive_input_timezone is None:
                return value
            value = value.replace(tzinfo=self.naive_input_timezone)

        return value.astimezone(target_timezone)

    def _resolve_renderer(self, locale: str) -> LocaleRenderer:
        return self._resolved_renderers.get(locale, self._resolved_default_renderer)

    def format_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        normalized = self._normalize_datetime(value, locale=locale)
        renderer = self._resolve_renderer(locale)
        return renderer.render_datetime(normalized, locale=locale, pattern=pattern)

    def format_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        renderer = self._resolve_renderer(locale)
        return renderer.render_date(value, locale=locale, pattern=pattern)

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

        if isinstance(value, float):
            if not isfinite(value):
                raise ValueFormattingError(f"Invalid grouped number value: {value!r}")

        try:
            decimal_value = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueFormattingError(f"Invalid grouped number value: {value!r}") from exc
        return format(decimal_value, "f")


def wrapped_date(value: date, *, pattern: str | None = None) -> LocalizedDate:
    """Create an explicit wrapped date placeholder value."""

    return LocalizedDate(value=value, pattern=pattern)


def wrapped_datetime(value: datetime, *, pattern: str | None = None) -> LocalizedDateTime:
    """Create an explicit wrapped datetime placeholder value."""

    return LocalizedDateTime(value=value, pattern=pattern)


def grouped_number(value: int | float | Decimal | str) -> GroupedNumber:
    """Create an explicit wrapped grouped-number placeholder value."""

    return GroupedNumber(value=value)


def enum_ref(enum_name: str, item: str | Enum) -> EnumReference:
    """Create an explicit wrapped enum label placeholder value."""

    return EnumReference(enum_name=enum_name, item=item)


WrappedValue = LocalizedDate | LocalizedDateTime | GroupedNumber | EnumReference
