# localization

Small, explicit, production-oriented Python localization for JSON files.

It focuses on a clear runtime:

- load locale JSON from disk
- validate locale schema and placeholders
- query messages / enums / FAQs
- edit locale files safely
- format wrapped values explicitly (dates, datetimes, numbers, enum references)

No hidden magic, no large framework abstractions.

---

## Requirements

- Python 3.11+

---

## Expected file layout

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
  "default_locale": "fa",
  "locales": {
    "en": {"label": "English", "native_name": "English", "direction": "ltr"},
    "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"}
  }
}
```

Notes:

- `default_locale` can be **any** declared locale.
- `locales` must be non-empty.
- unknown locale codes raise `LocaleNotFoundError`.

---

## High-level design

### Explicit formatting philosophy

Only wrapped values are specially formatted:

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Raw values are passed through normally.

### Locale overlay model (single fallback rule)

For non-default locales, runtime reads from an **effective locale view**:

`effective = deep_merge(default_locale_data, requested_locale_data)`

Merge rules:

- dicts merge recursively
- scalars in requested locale override default values
- lists in requested locale replace default lists

The same model is used for:

- `msg`
- enum lookups
- FAQ lookups

---

## Placeholder limitation (intentional)

Only top-level placeholder names are supported.

Supported:

- `{name}`
- `{user_name}`
- `{amount2}`

Not supported:

- `{user.name}`
- `{items[0]}`
- `{user[name]}`

Unsupported placeholder forms raise `PlaceholderError` in validation/runtime.

---

## Runtime architecture

### 1) `LocaleRepository`

- reads manifest + locale files
- validates manifest shape
- resolves locale codes
- `None` locale resolves to configured default locale
- unknown locale raises `LocaleNotFoundError`

### 2) `LocaleValidator`

- validates per-locale JSON schema
- validates placeholders
- validates placeholder compatibility against default locale for shared message keys

### 3) `I18nService`

- high-level message + enum + FAQ APIs
- applies the uniform locale overlay model
- resolves wrapped values with `LocaleValueFormatter`

### 4) `LocaleEditor`

- safe path-based set/delete
- rejects protected paths (`_meta`)
- validates before saving
- delete on missing path raises `LocaleEditError`

### 5) `LocaleValueFormatter`

Two-stage temporal pipeline:

1. timezone normalization (`datetime`)
2. locale renderer converts to final `str`

---

## Error semantics

- `LocaleNotFoundError`: unknown locale or missing locale file
- `ManifestError`: invalid manifest
- `MissingTranslationError`: missing path/value after fallback overlay
- `LocaleDataError`: malformed data/type mismatch
- `PlaceholderError`: invalid/missing placeholders
- `LocaleEditError`: unsafe or invalid edit operation
- `ValueFormattingError`: invalid wrapped value formatting input

---

## Formatter API (preferred)

### Renderer contract

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

### Timezone resolution

For `datetime` formatting:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Naive datetime behavior

- if `naive_input_timezone` is not set: naive datetime remains naive (no timezone conversion)
- if set: naive datetime is treated as that source timezone, then normalized to target timezone

---

## Usage examples

### Build runtime with non-English default locale

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="./locales",
    manifest_path="./manifest.json",
)

print(repo.default_locale)  # e.g. "fa"
```

### Unknown locale raises

```python
from localization.exceptions import LocaleNotFoundError

try:
    i18n.msg("user.greeting", locale="unknown", name="Ali")
except LocaleNotFoundError:
    ...
```

### Message lookup

```python
text = i18n.msg("user.greeting", locale="fa", name="Sara")
```

### Enum lookup

```python
label = i18n.enum_label("order_status", "pending", locale="fa")
```

### FAQ lookup

```python
answer = i18n.faq_answer("payment", "refund_time", locale="fa")
```

### Wrapped datetime + grouped number + enum ref

```python
from datetime import date, datetime, timezone
from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime

text = i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=timezone.utc)),
    amount=grouped_number("1234567"),
    status=enum_ref("order_status", "pending"),
    raw_date=date(2026, 4, 17),
)
```

### Locale-specific renderer + timezone (Persian-style output)

```python
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from localization import LocaleRenderer, LocaleValueFormatter

class PersianRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(timezone.utc),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    default_timezone=timezone.utc,
    renderers={"fa": PersianRenderer()},
)
```

### Editor set/delete

```python
editor.set_value("fa", "messages.user.greeting", "سلام {name}")
editor.delete_value("fa", "faqs.payment.items.refund_time")
```

If delete path does not exist, `LocaleEditError` is raised.

---

## Public API reference

### Runtime

- `build_i18n_runtime(...)`
- `build_runtime(...)`
- `I18nRuntime`

### Core components

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

### Wrapper dataclasses

- `LocalizedDate`
- `LocalizedDateTime`
- `GroupedNumber`
- `EnumReference`

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

## Example and tests

- Example script: `examples/basic_usage.py`
- Run tests: `pytest -q`
