# localization

A production-focused Python localization package for loading, validating, querying, and editing JSON locale files.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Two-stage locale-aware temporal formatting (timezone normalization + rendering)

---

## Requirements

- Python 3.11+

---

## Expected layout

```text
project/
  manifest.json
  locales/
    en.json
    fa.json
```

### `manifest.json`

```json
{
  "default_locale": "en",
  "locales": {
    "en": {"label": "English", "native_name": "English", "direction": "ltr"},
    "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"}
  }
}
```

> `default_locale` is enforced as `en`.

---

## Quick start

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from localization import LocaleValueFormatter, build_i18n_runtime

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=timezone.utc),
    default_timezone=timezone.utc,
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
)

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="./locales",
    manifest_path="./manifest.json",
    value_formatter=formatter,
)

validator.validate_all()
print(i18n.msg("user.greeting", locale="fa", name="Sara"))
```

---

## Formatter architecture (two-stage pipeline)

`LocaleValueFormatter` processes wrapped temporal values in **two explicit stages**.

### Stage 1) Timezone normalization

The formatter resolves a target timezone in this exact order:

1. `locale_timezones[locale]`
2. `default_timezone`
3. `UTC`

For `datetime` values:

- **Aware datetime**: normalized using `astimezone(resolved_timezone)`.
- **Naive datetime**:
  - default behavior: value is left untouched (naive remains naive),
  - optional behavior: if `assume_naive_input_timezone=True`, the naive value is interpreted in `naive_input_timezone` and then normalized to resolved timezone.

For `date` values:

- date values still pass through the same pipeline shape for consistency,
- no timezone arithmetic is applied to plain `date`.

### Stage 2) String rendering

After normalization, rendering resolves in this order:

1. locale-specific renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

Renderers produce the **final string output**, which means locale-specific implementations can render non-Gregorian calendars (for example, Jalali/Shamsi output).

---

## Renderer contract

Use `TemporalRenderer` for locale renderers:

```python
from datetime import date, datetime
from localization import TemporalRenderer

class MyRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        ...

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        ...
```

Built-in fallback renderer:

- `StrftimeRenderer` with defaults:
  - date: `%Y/%m/%d`
  - datetime: `%Y/%m/%d %H:%M:%S`

---

## Usage examples

### 1) Only default timezone + default renderer

```python
from datetime import datetime, timezone
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=timezone.utc),
    default_timezone=timezone.utc,
)
```

### 2) Locale-specific timezone

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=timezone.utc),
    default_timezone=timezone.utc,
    locale_timezones={
        "fa": ZoneInfo("Asia/Tehran"),
        "en": ZoneInfo("America/New_York"),
    },
)
```

### 3) Locale-specific renderer

```python
from datetime import date, datetime
from localization import LocaleValueFormatter, TemporalRenderer

class CompactRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y-%m-%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y-%m-%dT%H:%M:%S")

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    renderers={"en": CompactRenderer()},
)
```

### 4) Fallback to default renderer

```python
from datetime import date, datetime
from localization import LocaleValueFormatter, TemporalRenderer

class DefaultRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"[{locale}] {value.isoformat()}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"[{locale}] {value.isoformat()}"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    default_renderer=DefaultRenderer(),
    renderers={"fa": DefaultRenderer()},
)

# unknown locale -> default_renderer
```

### 5) Persian example: Tehran timezone + Jalali/Shamsi-style renderer

```python
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from localization import LocaleValueFormatter, TemporalRenderer

class PersianRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        # Insert real Jalali conversion here (e.g. your preferred calendar library).
        return f"شمسی({locale}) {value.isoformat()}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        # value has already been timezone-normalized.
        return f"شمسی({locale}) {value.isoformat()}"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=timezone.utc),
    default_timezone=timezone.utc,
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianRenderer()},
)
```

### 6) Wrapped date

```python
from datetime import date
from localization import wrapped_date

text = i18n.msg("user.report", locale="fa", date=wrapped_date(date(2026, 4, 17)))
```

### 7) Wrapped datetime

```python
from datetime import datetime
from localization import wrapped_datetime

text = i18n.msg("user.report", locale="fa", dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)))
```

### 8) Mixed placeholders

```python
from datetime import date, datetime
from enum import Enum

from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime

class OrderStatus(Enum):
    PENDING = "pending"

text = i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
    amount=grouped_number("1234567"),
    status=enum_ref("order_status", OrderStatus.PENDING),
    raw_date=date(2026, 4, 17),
)

# wrapped values are formatted by formatter pipeline
# raw_date remains a raw Python value
```

---

## Advanced example: custom renderer returning non-Gregorian strings

```python
from datetime import date, datetime
from localization import TemporalRenderer

class JalaliRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        # Convert Gregorian date -> Jalali string.
        # This method returns final output directly.
        return f"JALALI-DATE:{value.isoformat()}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        # Convert Gregorian datetime -> Jalali datetime string.
        return f"JALALI-DATETIME:{value.isoformat()}"
```

This is the key capability of the redesign: renderers are not limited to returning Python `date`/`datetime`; they return final strings.

---

## Placeholder wrapper behavior (important)

Formatting is explicit and opt-in.

- raw values are never auto-formatted
- wrapped values are formatted using the locale from `i18n.msg(..., locale=...)`
- caller does not pass locale into each wrapped value

Supported wrappers:

- `wrapped_date(date_value)`
- `wrapped_datetime(datetime_value)`
- `grouped_number(number_or_numeric_string)`
- `enum_ref(enum_name, item_key_or_enum_member)`

Number formatting and enum resolution behavior are unchanged.

---

## Public API overview

### Runtime builders

- `build_i18n_runtime(...)`
- `build_runtime(...)`

### Core classes

- `LocaleRepository`
- `LocaleValidator`
- `I18nService`
- `LocaleEditor`
- `LocaleValueFormatter`
- `TemporalRenderer`
- `StrftimeRenderer`

### Wrapper helpers

- `wrapped_date`
- `wrapped_datetime`
- `grouped_number`
- `enum_ref`

---

## Migration notes (old converter API -> new renderer API)

### What changed

Previous converter-oriented model:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

Current renderer-oriented model:

- normalization is handled by formatter (timezone layer)
- renderer returns final strings:
  - `render_date(...) -> str`
  - `render_datetime(...) -> str`

### Why changed

- timezone normalization and string rendering are separate concerns
- locale-specific calendar output (e.g., Jalali/Shamsi) requires direct string rendering
- fallback behavior is explicit and predictable for both timezone and renderer resolution

### Backward compatibility

- legacy callable converters are still accepted and adapted internally
- legacy argument names are still accepted:
  - `converters` (alias for `renderers`)
  - `default_converter` (alias for `default_renderer`)

Recommended migration:

1. keep your existing converter callables working as-is,
2. progressively replace them with `TemporalRenderer` implementations,
3. move timezone logic from converters into `locale_timezones` / `default_timezone`.

---

## Validation behavior

`LocaleValidator` checks:

1. Required root sections (`_meta`, `messages`, `enums`, `faqs`)
2. `_meta.locale` and `_meta.version`
3. Message/enum/faq structures and field types
4. Placeholder compatibility against `en` for overlapping message keys
5. Optional complete-structure parity (`require_complete_locales=True`)

---

## Editing locale files

```python
editor.set_value("fa", "messages.user.greeting", "سلام {name}")
editor.delete_value("fa", "faqs.payment.items.refund_time")
```

- `_meta` paths are protected
- edits are validated before writing

---

## Exceptions

- `I18nError`
- `ManifestError`
- `LocaleNotFoundError`
- `LocaleDataError`
- `MissingTranslationError`
- `PlaceholderError`
- `ValueFormattingError`
- `LocaleEditError`

Backward-compatible aliases:

- `TranslationValidationError`
- `TranslationKeyNotFoundError`

---

## Example and tests

- Example: `examples/basic_usage.py`
- Run tests: `pytest -q`
