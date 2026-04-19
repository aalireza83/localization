# localization

Small, explicit, production-oriented Python localization for JSON locale files.

It provides:
- repository-backed locale loading/saving,
- schema + placeholder validation,
- runtime lookup for messages / enums / FAQs,
- safe path-based editing,
- explicit wrapper-based value formatting,
- two-stage temporal formatting (timezone normalization + locale renderer).

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

## Core design

### 1) Uniform locale overlay model

For a requested locale:
1. resolve locale (`None` => default locale, unknown => `LocaleNotFoundError`)
2. load default locale document
3. if requested != default, deep-merge default with requested

Merge behavior:
- dict + dict: recursive merge
- scalar override: requested wins
- list override: requested replaces default list

All reads use this **same effective document**:
- `msg`
- enum APIs
- FAQ APIs

This guarantees one consistent fallback mental model.

### 2) Explicit formatting philosophy

Only wrapped values are specially formatted:
- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Raw values are not auto-localized.

### 3) Placeholder limitation (deliberate)

Supported placeholders: top-level identifiers only.
Examples:
- `{name}`
- `{user_name}`
- `{amount2}`

Unsupported:
- `{user.name}`
- `{items[0]}`
- `{user[name]}`

Unsupported forms raise `PlaceholderError` in validation/runtime.

---

## Runtime architecture

- `LocaleRepository`: manifest + locale JSON loading/saving, locale resolution, cache.
- `LocaleValidator`: locale schema checks + cross-locale placeholder compatibility.
- `I18nService`: message/enum/FAQ runtime API using the uniform overlay model.
- `LocaleEditor`: safe set/delete with protected paths and validation-before-save.
- `LocaleValueFormatter`: wrapper value formatting.

---

## Error semantics

- `LocaleNotFoundError`: unknown locale or missing locale file.
- `MissingTranslationError`: missing value/path after overlay resolution.
- `LocaleDataError`: malformed JSON structure/type mismatch.
- `PlaceholderError`: placeholder mismatch or unsupported placeholder form.
- `LocaleEditError`: invalid/protected edit path or delete missing path.
- `ValueFormattingError`: invalid wrapped formatting value.

---

## Formatter API (preferred)

Two-stage temporal pipeline:

### Stage 1: timezone normalization (`datetime`)
Resolution order:
1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

Naive datetime behavior:
- default: unchanged
- if `naive_input_timezone` set: treat naive input as that timezone, then normalize

### Stage 2: rendering (`date` / `datetime`)
Resolution order:
1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

`LocaleRenderer` protocol:

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        ...

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        ...
```

---

## Usage examples

### Build runtime with non-English default locale

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="./locales",
    manifest_path="./manifest.json",
)
validator.validate_all()
```

### Unknown locale raises

```python
from localization.exceptions import LocaleNotFoundError

try:
    i18n.msg("user.greeting", locale="de", name="Ali")
except LocaleNotFoundError:
    ...
```

### Message / enum / FAQ lookup

```python
print(i18n.msg("user.greeting", name="Ali"))
print(i18n.enum_label("order_status", "pending", locale="en"))
print(i18n.faq_answer("payment", "refund_time", locale="fa"))
```

### Wrapped datetime + locale renderer (Persian-style)

```python
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from localization import LocaleRenderer, LocaleValueFormatter, wrapped_date, wrapped_datetime

class PersianRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(timezone.utc),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianRenderer()},
)

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, tzinfo=timezone.utc)),
    amount=grouped_number("1234567"),
    status=enum_ref("order_status", "pending"),
    raw_date=date(2026, 4, 17),
))
```

### Editor behavior

```python
editor.set_value("fa", "messages.user.greeting", "سلام {name}")
editor.delete_value("fa", "messages.user.operation_failed")
# deleting a missing path raises LocaleEditError
```

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
