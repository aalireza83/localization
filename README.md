# localization

A production-focused Python localization package for loading, validating, querying, and editing JSON locale files.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Locale-aware date/datetime formatting through strongly-typed per-locale converters
- Explicit default converter fallback for unknown locales

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

## Date/datetime converter architecture

### Converter contract

`LocaleValueFormatter` uses a converter object implementing:

- `convert_date(value: date) -> date`
- `convert_datetime(value: datetime) -> datetime`

Use either:

- `LocaleDateTimeConverter` implementations (recommended), or
- legacy callables (`Callable[[date | datetime], date | datetime]`) for backward compatibility.

### Converter resolution order

For each formatting call, resolution is explicit and deterministic:

1. converter registered in `converters[locale]`
2. `default_converter`
3. built-in no-op identity converter

This ensures unknown locales still behave predictably.

### Timezone support and naive datetime policy

`TimezoneAwareLocaleConverter` provides explicit timezone normalization:

- aware datetime + `target_timezone` → converted via `.astimezone(...)`
- naive datetime behavior is controlled by `NaiveDatetimePolicy`:
  - `ASSUME_UTC` (default)
  - `ASSUME_SOURCE_TIMEZONE` (requires `source_timezone`)
  - `KEEP_NAIVE`

This keeps datetime conversion safe and non-magical.

### Example: per-locale + default fallback

```python
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from localization import (
    LocaleValueFormatter,
    NaiveDatetimePolicy,
    TimezoneAwareLocaleConverter,
)

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(UTC),
    converters={
        # Farsi: normalize datetimes to Tehran
        "fa": TimezoneAwareLocaleConverter(
            target_timezone=ZoneInfo("Asia/Tehran"),
            naive_policy=NaiveDatetimePolicy.ASSUME_SOURCE_TIMEZONE,
            source_timezone=UTC,
        ),
        # English: keep UTC semantics explicitly
        "en": TimezoneAwareLocaleConverter(target_timezone=UTC),
    },
    # fallback for locales without explicit registration
    default_converter=TimezoneAwareLocaleConverter(target_timezone=UTC),
)
```

---

## Placeholder wrapper behavior (important)

Formatting is **explicit** and **opt-in**.

- Raw values are never auto-formatted.
- Wrapped values are formatted/resolved using the locale from `i18n.msg(..., locale=...)`.
- Caller does **not** pass locale into each wrapped value.
- `wrapped_date(...)` and `wrapped_datetime(...)` always route through converter resolution.

### Supported wrappers

- `wrapped_date(date_value)`
- `wrapped_datetime(datetime_value)`
- `grouped_number(number_or_numeric_string)`
- `enum_ref(enum_name, item_key_or_enum_member)`

### Example

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
```

In the output:

- wrapped values are localized
- `raw_date` remains a raw Python value (`str(date)` behavior)

---

## Number formatting rules

Grouped number formatting remains in `formatter.py` because it is part of explicit wrapper-based placeholder value formatting.

- only `grouped_number(...)` values are grouped
- raw `int`/`float` values remain unchanged
- numeric values and numeric strings are supported
- grouping style is simple comma grouping (`1,234,567`)
- invalid wrapped numeric input raises `ValueFormattingError`

---

## Enum wrapper rules

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

### Converter types

- `LocaleDateTimeConverter` (protocol)
- `IdentityLocaleConverter`
- `CallableLocaleConverter` (legacy callable adapter)
- `TimezoneAwareLocaleConverter`
- `NaiveDatetimePolicy`

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

## Migration notes

### What changed

- Date/datetime conversion now uses a formal converter protocol (`LocaleDateTimeConverter`).
- `LocaleValueFormatter` now supports `default_converter` fallback.
- The default fallback when no converter is configured is an explicit no-op identity converter.
- Built-in timezone conversion support is available via `TimezoneAwareLocaleConverter`.

### Backward compatibility

- Existing callable-based converters still work.
- They are automatically wrapped by `CallableLocaleConverter`.
- No changes are required for existing wrapper helpers (`wrapped_date`, `wrapped_datetime`, `grouped_number`, `enum_ref`).

### Behavior clarifications

- Wrappers always use converter resolution; they never bypass converters.
- Naive datetime behavior is explicit through `NaiveDatetimePolicy`.
- `ASSUME_SOURCE_TIMEZONE` without `source_timezone` raises `ValueFormattingError`.

---

## Example and tests

- Example: `examples/basic_usage.py`
- Run tests: `pytest -q`
