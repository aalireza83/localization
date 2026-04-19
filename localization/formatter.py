from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Callable, Literal, Protocol, runtime_checkable

from localization.exceptions import ValueFormattingError

DateLike = date | datetime
NowProvider = Callable[[], datetime]
NaiveDateTimePolicy = Literal["keep", "assume_source"]
LegacyConverterCallable = Callable[[DateLike], DateLike]


@runtime_checkable
class TemporalRenderer(Protocol):
    """Render temporal values to final locale-specific strings."""

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        """Render a date value to text."""

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        """Render a datetime value to text."""


@runtime_checkable
class TemporalConverter(Protocol):
    """Legacy converter contract kept for backward compatibility."""

    def convert_date(self, value: date, *, locale: str) -> date:
        """Convert date before rendering."""

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        """Convert datetime before rendering."""


@dataclass(frozen=True, slots=True)
class StrftimeRenderer:
    """Built-in fallback renderer using ``strftime``."""

    default_date_pattern: str = "%Y/%m/%d"
    default_datetime_pattern: str = "%Y/%m/%d %H:%M:%S"

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_date_pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or self.default_datetime_pattern)


BUILTIN_RENDERER = StrftimeRenderer()


@dataclass(frozen=True, slots=True)
class CallableTemporalConverter:
    """Adapter for old ``Callable[[date | datetime], date | datetime]`` converters."""

    converter: LegacyConverterCallable

    def convert_date(self, value: date, *, locale: str) -> date:
        converted = self.converter(value)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Legacy date converter must return date for date input.")
        return converted

    def convert_datetime(self, value: datetime, *, locale: str) -> datetime:
        converted = self.converter(value)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Legacy datetime converter must return datetime for datetime input.")
        return converted


@dataclass(frozen=True, slots=True)
class ConverterRendererAdapter:
    """Adapter that renders by first converting then delegating to a renderer."""

    converter: TemporalConverter
    renderer: TemporalRenderer = BUILTIN_RENDERER

    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter.convert_date(value, locale=locale)
        if isinstance(converted, datetime) or not isinstance(converted, date):
            raise ValueFormattingError("Legacy date converter must return date for date input.")
        return self.renderer.render_date(converted, locale=locale, pattern=pattern)

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        converted = self.converter.convert_datetime(value, locale=locale)
        if not isinstance(converted, datetime):
            raise ValueFormattingError("Legacy datetime converter must return datetime for datetime input.")
        return self.renderer.render_datetime(converted, locale=locale, pattern=pattern)


@dataclass(frozen=True, slots=True)
class TimezoneLocaleConverter:
    """Deprecated compatibility helper for legacy converter-based integrations.

    Prefer formatter-level timezone resolution via ``locale_timezones`` and
    ``default_timezone``.
    """

    target_timezone: tzinfo | None = None
    assume_naive_input_timezone: bool = False
    naive_input_timezone: tzinfo | None = None

    def __post_init__(self) -> None:
        if self.assume_naive_input_timezone and self.naive_input_timezone is None:
            raise ValueError("naive_input_timezone must be set when assume_naive_input_timezone is True.")

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


RendererInput = TemporalRenderer | TemporalConverter | LegacyConverterCallable
LegacyConverterInput = TemporalConverter | LegacyConverterCallable


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
    """Formats explicitly wrapped placeholder values using a two-stage pipeline.

    Stage 1 (timezone normalization for datetime):
      locale timezone -> default_timezone -> UTC

    Stage 2 (final string rendering):
      locale renderer -> default renderer -> built-in strftime renderer
    """

    default_now: NowProvider
    locale_timezones: dict[str, tzinfo] | None = None
    default_timezone: tzinfo | None = None
    naive_datetime_policy: NaiveDateTimePolicy = "keep"
    naive_source_timezone: tzinfo | None = None
    renderers: dict[str, RendererInput] | None = None
    default_renderer: RendererInput | None = None
    # Backward-compatible aliases from converter-based API.
    converters: dict[str, LegacyConverterInput] | None = None
    default_converter: LegacyConverterInput | None = None

    def __post_init__(self) -> None:
        if self.naive_datetime_policy not in {"keep", "assume_source"}:
            raise ValueError("naive_datetime_policy must be either 'keep' or 'assume_source'.")
        if self.naive_datetime_policy == "assume_source" and self.naive_source_timezone is None:
            raise ValueError("naive_source_timezone must be set when naive_datetime_policy is 'assume_source'.")

        normalized_renderers: dict[str, RendererInput] = {}
        if self.renderers:
            normalized_renderers.update(self.renderers)
        if self.converters:
            for locale, converter in self.converters.items():
                normalized_renderers.setdefault(locale, converter)

        self.renderers = {locale: self._coerce_renderer(renderer) for locale, renderer in normalized_renderers.items()}

        chosen_default: RendererInput | None = self.default_renderer if self.default_renderer is not None else self.default_converter
        self.default_renderer = self._coerce_renderer(chosen_default) if chosen_default is not None else None

    def _coerce_renderer(self, renderer: RendererInput) -> TemporalRenderer:
        if isinstance(renderer, TemporalRenderer):
            return renderer
        converter: TemporalConverter
        if isinstance(renderer, TemporalConverter):
            converter = renderer
        else:
            converter = CallableTemporalConverter(renderer)
        return ConverterRendererAdapter(converter=converter, renderer=BUILTIN_RENDERER)

    def _resolve_timezone(self, locale: str) -> tzinfo:
        if self.locale_timezones and locale in self.locale_timezones:
            return self.locale_timezones[locale]
        if self.default_timezone is not None:
            return self.default_timezone
        return timezone.utc

    def _normalize_datetime(self, value: datetime, *, locale: str) -> datetime:
        target_timezone = self._resolve_timezone(locale)

        if value.tzinfo is None:
            if self.naive_datetime_policy == "keep":
                return value
            assumed = value.replace(tzinfo=self.naive_source_timezone)
            return assumed.astimezone(target_timezone)

        return value.astimezone(target_timezone)

    def _resolve_renderer(self, locale: str) -> TemporalRenderer:
        if self.renderers and locale in self.renderers:
            return self.renderers[locale]
        if isinstance(self.default_renderer, TemporalRenderer):
            return self.default_renderer
        return BUILTIN_RENDERER

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
