# localization

A small, explicit, production-oriented Python localization package for:

- loading JSON locale files
- validating locale structure and placeholders
- resolving messages/enums/faqs with predictable locale overlay fallback
- safely editing locale files
- formatting wrapped values (date/datetime/number/enum)

## Philosophy

- **Explicit over magic**
- **Fail loudly** on unknown locales, malformed data, missing paths, and invalid placeholders
- **Top-level placeholders only** (`{name}`, `{amount}`, `{created_at}`)
- **One fallback model everywhere** (messages, enums, faqs)

---

## Installation / Requirements

- Python 3.11+
- No heavy framework dependencies

---

## Expected project layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

### `manifest.json`

```json
{
  "default_locale": "fa",
  "locales": {
    "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
    "en": {"label": "English", "native_name": "English", "direction": "ltr"}
  }
}
```

Rules:
- `default_locale` can be **any declared locale**
- unknown locales are rejected
- `locales` must be non-empty

---

## Runtime architecture

### `LocaleRepository`
- Loads/validates manifest
- Loads/saves locale JSON files
- Resolves locale (`None` -> default, unknown -> `LocaleNotFoundError`)

### `LocaleValidator`
- Validates locale JSON shape
- Validates placeholder compatibility against default locale
- Enforces top-level placeholder syntax only

### `I18nService`
- Message/enum/faq lookup
- Wrapper-aware formatting during `msg(...)`
- Uniform overlay fallback model

### `LocaleEditor`
- Path-based set/get/delete
- Blocks protected `_meta` edits
- Validates before saving
- delete on missing path raises `LocaleEditError`

### `LocaleValueFormatter`
Two-stage temporal formatting pipeline:
1) timezone normalization
2) locale renderer final string generation

---

## Uniform locale overlay fallback model

For any requested known locale:

1. Resolve locale (`None` -> default, unknown -> error)
2. Build effective document:
   - if locale == default: use default document
   - else: `effective = deep_merge(default_locale_data, requested_locale_data)`
3. Read `messages`, `enums`, and `faqs` from this same effective document

Merge rules:
- dicts merge recursively
- scalar values override
- lists replace

This behavior is used consistently by:
- `msg`
- `enum_group`, `enum_values`, `enum_item`, `enum_label`
- `faq_section`, `faq_items`, `faq_item`, `faq_question`, `faq_answer`

---

## Placeholder model (strict)

Supported fields:
- `{name}`
- `{user_name}`
- `{amount2}`

Unsupported (raise `PlaceholderError`):
- `{user.name}`
- `{items[0]}`
- `{user[name]}`

No nested placeholder traversal is implemented.

---

## Error semantics

- `LocaleNotFoundError`: locale not declared / locale file missing
- `MissingTranslationError`: path/value missing after overlay resolution
- `LocaleDataError`: path exists but type/shape is invalid
- `PlaceholderError`: unsupported placeholder forms or missing placeholder values
- `LocaleEditError`: invalid/protected edit operations (including deleting missing path)
- `ValueFormattingError`: invalid wrapped formatting input

---

## Formatter API (preferred)

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from localization import LocaleRenderer, LocaleValueFormatter

class PersianRenderer(LocaleRenderer):
    def render_date(self, value, *, locale, pattern=None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value, *, locale, pattern=None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(timezone.utc),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    default_timezone=timezone.utc,
    renderers={"fa": PersianRenderer()},
)
```

### Timezone resolution order
1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Renderer resolution order
1. `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

### Naive datetime behavior
- default: leave naive datetimes untouched
- if `naive_input_timezone` is set: attach that timezone, then normalize

---

## Wrapper-based formatting

Formatting is explicit and opt-in.

Wrappers:
- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Only wrapped values are specially formatted. Raw values are untouched.

---

## Complete usage example

```python
from datetime import date, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo

from localization import (
    LocaleRenderer,
    LocaleValueFormatter,
    build_i18n_runtime,
    enum_ref,
    grouped_number,
    wrapped_date,
    wrapped_datetime,
)

class OrderStatus(Enum):
    PENDING = "pending"

class PersianRenderer(LocaleRenderer):
    def render_date(self, value, *, locale, pattern=None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value, *, locale, pattern=None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(timezone.utc),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianRenderer()},
)

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="./locales",
    manifest_path="./manifest.json",
    value_formatter=formatter,
)

validator.validate_all()

# locale=None -> manifest default locale
print(i18n.msg("user.operation_failed"))

# unknown locale raises LocaleNotFoundError
print(i18n.msg("user.greeting", locale="en", name="Sara"))

# enum + faq lookups use the same overlay model
print(i18n.enum_label("order_status", "pending", locale="en"))
print(i18n.faq_answer("payment", "refund_time", locale="en"))

print(
    i18n.msg(
        "user.report",
        locale="fa",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=timezone.utc)),
        amount=grouped_number("1234567"),
        status=enum_ref("order_status", OrderStatus.PENDING),
        raw_date=date(2026, 4, 17),
    )
)

editor.set_value("fa", "messages.user.greeting", "درود {name}")
editor.delete_value("fa", "messages.user.operation_failed")
```

---

## Public API reference

### Runtime builders
- `build_i18n_runtime(...)`
- `build_runtime(...)`

### Core classes
- `LocaleRepository`
- `LocaleValidator`
- `I18nService`
- `LocaleEditor`
- `LocaleValueFormatter`
- `LocaleRenderer`
- `StrftimeRenderer`

### Wrapper helpers
- `wrapped_date`
- `wrapped_datetime`
- `grouped_number`
- `enum_ref`

### Exceptions
- `I18nError`
- `ManifestError`
- `LocaleNotFoundError`
- `LocaleDataError`
- `MissingTranslationError`
- `PlaceholderError`
- `ValueFormattingError`
- `LocaleEditError`

---

## Tests and example

- Run tests: `pytest -q`
- Example script: `examples/basic_usage.py`
