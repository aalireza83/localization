# localization

A production-focused Python localization package for loading, validating, querying, and editing JSON locale files.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Two-stage locale-aware temporal formatting (timezone normalization + locale rendering)

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
from datetime import datetime
from zoneinfo import ZoneInfo

from localization import LocaleValueFormatter, build_i18n_runtime

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=ZoneInfo("UTC")),
    default_timezone=ZoneInfo("UTC"),
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

## Formatter architecture (two explicit stages)

`LocaleValueFormatter` processes wrapped date/datetime values through **two explicit stages**.

### Stage 1: Timezone normalization (datetime)

Timezone resolution order:

1. `locale_timezones[locale]`
2. `default_timezone`
3. `UTC`

Then normalization rules are applied:

- **aware datetime**: normalized with `astimezone(resolved_timezone)`
- **naive datetime**:
  - `naive_datetime_policy="keep"` (default): leave naive value unchanged
  - `naive_datetime_policy="assume_source"`: treat naive value as `naive_source_timezone`, then normalize to resolved timezone

### Stage 2: String rendering

Renderer resolution order:

1. locale-specific renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

This stage produces the **final string** and is where locale-specific calendars (e.g. Jalali/Shamsi) can be implemented cleanly.

---

## Renderer contract

Use `TemporalRenderer` for strongly typed rendering:

```python
from datetime import date, datetime
from localization import TemporalRenderer

class MyRenderer(TemporalRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

---

## Timezone semantics with examples

### Aware datetime example

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(timezone.utc),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
)

value = datetime(2026, 4, 15, 8, 30, tzinfo=timezone.utc)
print(formatter.format_datetime(value, locale="fa"))
# 2026/04/15 12:00:00
```

### Naive datetime example (safe default)

```python
from datetime import datetime
from zoneinfo import ZoneInfo

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    naive_datetime_policy="keep",
)

value = datetime(2026, 4, 15, 8, 30)
print(formatter.format_datetime(value, locale="fa"))
# 2026/04/15 08:30:00  (unchanged, still naive)
```

### Naive datetime example (assume source timezone)

```python
from datetime import datetime
from zoneinfo import ZoneInfo

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    naive_datetime_policy="assume_source",
    naive_source_timezone=ZoneInfo("UTC"),
)

value = datetime(2026, 4, 15, 8, 30)
print(formatter.format_datetime(value, locale="fa"))
# 2026/04/15 12:00:00
```

---

## Usage examples requested in one place

### 1) Only default timezone + default renderer

```python
formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    default_timezone=ZoneInfo("UTC"),
)
```

### 2) Locale-specific timezone

```python
formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    default_timezone=ZoneInfo("UTC"),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
)
```

### 3) Locale-specific renderer

```python
formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    renderers={"fa": MyFaRenderer()},
)
```

### 4) Fallback to default renderer

```python
formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    default_renderer=MyRenderer(),
)
# Any locale missing in renderers uses default_renderer.
```

### 5) Persian example (Tehran timezone + Jalali/Shamsi string)

```python
class PersianRenderer:
    def render_date(self, value, *, locale: str, pattern: str | None = None) -> str:
        # Convert Gregorian date -> Jalali string using your preferred lib or logic.
        return f"jalali:{value.isoformat()}"

    def render_datetime(self, value, *, locale: str, pattern: str | None = None) -> str:
        # value is already timezone-normalized by formatter stage 1.
        return f"jalali-dt:{value.isoformat()}"

formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianRenderer()},
)
```

### 6) Wrapped date

```python
from datetime import date
from localization import wrapped_date

i18n.msg("user.report", locale="fa", date=wrapped_date(date(2026, 4, 17)))
```

### 7) Wrapped datetime

```python
from datetime import datetime
from localization import wrapped_datetime

i18n.msg("user.report", locale="fa", dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)))
```

### 8) Mixed placeholders

```python
from datetime import date, datetime
from localization import grouped_number, wrapped_date, wrapped_datetime

i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),  # raw values are untouched unless wrapped
)
```

---

## Advanced renderer examples

### Custom renderer implementation

```python
class IsoRenderer:
    def render_date(self, value, *, locale: str, pattern: str | None = None) -> str:
        return value.isoformat()

    def render_datetime(self, value, *, locale: str, pattern: str | None = None) -> str:
        return value.isoformat()
```

### Renderer returning Jalali/Shamsi strings

Your renderer can directly return final locale-specific strings (including non-Gregorian calendars). The formatter no longer requires locale logic to return Python `date`/`datetime`.

### Raw values stay raw, wrapped values are formatted

Only explicit wrappers (`wrapped_date`, `wrapped_datetime`, `grouped_number`, `enum_ref`) are transformed by the formatter. Raw values follow Python default formatting behavior in templates.

---

## Placeholder wrapper behavior (important)

Formatting is **explicit** and **opt-in**.

- Raw values are never auto-formatted.
- Wrapped values are formatted/resolved using the locale from `i18n.msg(..., locale=...)`.
- Caller does **not** pass locale into each wrapped value.

### Supported wrappers

- `wrapped_date(date_value)`
- `wrapped_datetime(datetime_value)`
- `grouped_number(number_or_numeric_string)`
- `enum_ref(enum_name, item_key_or_enum_member)`

### Number formatting rules

- only `grouped_number(...)` values are grouped
- raw `int`/`float` values remain unchanged
- numeric values and numeric strings are supported
- grouping style is simple comma grouping (`1,234,567`)
- invalid wrapped numeric input raises `ValueFormattingError`

### Enum wrapper rules

- labels are loaded from locale files via `i18n.enum_label(...)`
- no hardcoded labels in Python
- if wrapper receives a Python `Enum` member:
  - use its `value` when it is a non-empty string
  - otherwise use `name.lower()`

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

### Backward-compatibility helpers

- `TemporalConverter`
- `TimezoneLocaleConverter` (legacy converter path)

### Wrapper helpers

- `wrapped_date`
- `wrapped_datetime`
- `grouped_number`
- `enum_ref`

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

## Migration notes (converter API -> renderer API)

### What changed

Old design focused on converter outputs (`date` / `datetime`):

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

New design separates concerns:

1. timezone normalization (formatter stage 1)
2. final string rendering (renderer stage 2)

### Why this change

Locale-specific calendars (for example Jalali/Shamsi) often need to emit final strings directly. The renderer API supports that explicitly.

### Backward compatibility

You can still pass old converter-style objects/callables:

```python
formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # datetime
    converters={"fa": old_converter},
)
```

Those are internally adapted to renderer behavior.

---

## Design rationale

This architecture is better because:

- timezone normalization and string rendering are separate explicit concerns
- locale-specific calendars can return final locale strings directly
- fallback behavior is deterministic and documented
- wrapper-based formatting remains explicit and predictable

---

## Example and tests

- Example: `examples/basic_usage.py`
- Run tests: `pytest -q`
