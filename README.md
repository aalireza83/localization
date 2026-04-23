# localization

Small, explicit, production-oriented Python localization for JSON locale files.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Two-stage locale-aware date/datetime formatting:
  1) timezone normalization, 2) locale rendering

---

## Requirements

- Python 3.11+

## Expected file layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

`manifest.json`:

```json
{
  "default_locale": "fa",
  "locales": {
    "fa": {"label": "Farsi", "native_name": "فارسی", "direction": "rtl"},
    "en": {"label": "English", "native_name": "English", "direction": "ltr"}
  }
}
```

Important manifest rules:
- `default_locale` can be any declared locale.
- `locales` must be non-empty.
- unknown locales are errors (no silent fallback).

---

## Formatter redesign: two-stage temporal pipeline

`LocaleValueFormatter` now formats temporal wrapped values in **two explicit stages**.

### Stage 1: timezone normalization (`datetime` values)

Timezone resolution order is fixed and explicit:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Stage 2: string rendering (`date` and `datetime`)

Renderer resolution order is also fixed and explicit:

1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer` fallback

This makes behavior predictable and easy to reason about.

---

## Naive vs aware datetime semantics

### Aware datetimes

Aware values are normalized with `astimezone(resolved_timezone)`.

### Naive datetimes

The formatter uses one explicit rule:

- If `naive_input_timezone` is **not** set, naive datetimes are left unchanged (safe default).
- If `naive_input_timezone` **is** set, naive values are first interpreted in that timezone and then normalized to the resolved target timezone.

This avoids hidden assumptions while still allowing explicit conversion rules.

---

## Renderer contract

Use `LocaleRenderer` for locale-specific final string output:

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

A renderer returns the final `str`, so locale-specific calendars (for example Jalali/Shamsi formatting) are straightforward to implement.

---

## Usage examples

### 1) Default timezone + default renderer only

```python
from datetime import UTC, datetime
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
)

# timezone fallback: UTC
# renderer fallback: built-in strftime renderer
print(formatter.format_datetime(datetime(2026, 4, 15, 8, 30, tzinfo=UTC), locale="en"))
```

### 2) Locale-specific timezone

```python
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    default_timezone=ZoneInfo("UTC"),
)

# fa uses Asia/Tehran, others use default UTC
```

### 3) Locale-specific renderer

```python
from datetime import date, datetime
from localization import LocaleRenderer, LocaleValueFormatter

class PrefixRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"{locale}:{value.strftime(pattern or '%Y/%m/%d')}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"{locale}:{value.strftime(pattern or '%Y/%m/%d %H:%M:%S')}"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    renderers={"fa": PrefixRenderer()},
)
```

### 4) Fallback to default renderer

```python
formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    default_renderer=PrefixRenderer(),
)
# any locale without a specific renderer uses default_renderer
```

### 5) Persian example: Tehran timezone + Jalali/Shamsi-like output

```python
from datetime import date, datetime, UTC
from zoneinfo import ZoneInfo
from localization import LocaleRenderer, LocaleValueFormatter

class PersianJalaliRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        # plug real Jalali conversion here (e.g. your own implementation/library)
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianJalaliRenderer()},
)
```

### 6) Wrapped `date`

```python
from datetime import date
from localization import wrapped_date

value = wrapped_date(date(2026, 4, 17))
```

### 7) Wrapped `datetime`

```python
from datetime import UTC, datetime
from localization import wrapped_datetime

value = wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC))
```

### 8) Mixed placeholders (wrapped + raw)

```python
from datetime import UTC, date, datetime
from localization import grouped_number, wrapped_date, wrapped_datetime

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),  # remains raw, not auto-formatted
)
```

---

## Advanced examples

### Custom renderer implementation

```python
class CompactRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%d-%m-%Y")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%d-%m-%Y %H:%M")
```

### Jalali/Shamsi renderer hook

Use any calendar conversion implementation you prefer inside `render_date` / `render_datetime`.
The formatter only requires a final `str`, so non-Gregorian output is a first-class use case.

### Raw values remain raw

Only wrapped values (`wrapped_date`, `wrapped_datetime`, `grouped_number`, `enum_ref`) are specially processed.
Unwrapped values are passed through Python formatting unchanged.

---

## Backward compatibility and migration notes

### What changed

Old design centered around converter methods that returned Python temporal values:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

New design separates concerns:

1. timezone normalization
2. final rendering to `str`

### Why this changed

Locale-specific calendar formatting (for example Persian/Jalali) often needs direct string output.
Returning only `date`/`datetime` from locale hooks was too restrictive.

### Compatibility behavior

`LocaleValueFormatter` still accepts older converter APIs:

- `converters={...}` and `default_converter=...`
- callable converters (`Callable[[date | datetime], date | datetime]`)
- object-based legacy converters with `convert_date` / `convert_datetime`

These are adapted internally to renderer behavior, so existing code can migrate incrementally.

---

## Public API overview

### Builders
- `build_i18n_runtime(...)`
- `build_runtime(...)`

### Main classes
- `LocaleRepository`
- `LocaleValidator`
- `I18nService`
- `LocaleEditor`
- `LocaleValueFormatter`
- `LocaleRenderer`
- `StrftimeRenderer`

Backward-compatibility interfaces:

- `LocaleConverter`
- `TimezoneLocaleConverter`

### Wrapper helpers
- `wrapped_date`
- `wrapped_datetime`
- `grouped_number`
- `enum_ref`

---

## Run tests

```bash
pytest -q
```

## Example script

```bash
python examples/basic_usage.py
```
