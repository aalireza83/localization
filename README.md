# localization

A production-focused Python localization package for loading, validating, querying, and editing JSON locale files.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Locale-aware date/datetime formatting through pluggable converters

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

### Locale schema

```json
{
  "_meta": {"locale": "en", "version": 1},
  "messages": {
    "user": {
      "greeting": "Hello {name}",
      "report": "Date {date}, datetime {dt}, amount {amount}, status {status}, raw {raw_date}"
    }
  },
  "enums": {
    "order_status": {
      "title": "Order status",
      "values": {
        "pending": {"label": "Pending payment", "description": "Awaiting payment", "order": 10}
      }
    }
  },
  "faqs": {
    "payment": {
      "title": "Payment questions",
      "items": {
        "refund_time": {
          "question": "How long does a refund take?",
          "answer": "Refunds usually take 3 to 7 business days.",
          "order": 20,
          "tags": ["payment", "refund"]
        }
      }
    }
  }
}
```

---

## Quick start

```python
from localization import LocaleValueFormatter, build_i18n_runtime

formatter = LocaleValueFormatter(
    default_now=lambda: ...,  # callable returning datetime
    converters={"fa": lambda value: value},
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

## Example and tests

- Example: `examples/basic_usage.py`
- Run tests: `pytest -q`
