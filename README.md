# localization

`localization` is a small, explicit, production-oriented Python package for JSON-based i18n.

It focuses on:

- loading locale files from disk,
- validating structure and placeholders,
- message / enum / FAQ lookup,
- safe editing,
- explicit wrapped-value formatting,
- two-stage temporal formatting (timezone normalization + locale rendering).

## Design principles

- **Small and explicit** (not a framework).
- **Fail loudly** on unknown locale, missing keys, malformed data.
- **One fallback model** everywhere.
- **Top-level placeholders only** (`{name}`, `{amount}`, `{created_at}`).
- **Formatting is opt-in** via wrappers.

---

## Installation

```bash
pip install localization
```

(For local development, install in editable mode from this repo.)

---

## Expected file layout

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

- `default_locale` can be **any declared locale**.
- Unknown locale requests raise `LocaleNotFoundError`.

---

## Runtime architecture

### `LocaleRepository`

- Loads manifest and locale JSON files.
- Resolves locale codes (`None` => default locale).
- Raises on unknown locale.
- Provides optional in-memory cache.

### `LocaleValidator`

- Validates root schema, messages, enums, FAQs.
- Enforces placeholder compatibility against default locale for overlapping message keys.
- Enforces **top-level-only placeholders**.

### `I18nService`

- High-level lookup API for messages, enums, FAQs.
- Applies one consistent overlay model (see below).
- Resolves wrapped placeholder values through `LocaleValueFormatter`.

### `LocaleEditor`

- Safe path-based edits (`set_value`, `delete_value`).
- Protects `_meta` paths.
- Revalidates before saving.
- `delete_value` raises `LocaleEditError` if path does not exist.

### `LocaleValueFormatter`

- Explicit wrapper formatting only (`wrapped_date`, `wrapped_datetime`, `grouped_number`, `enum_ref`).
- Two-stage temporal pipeline:
  1) timezone normalization
  2) locale renderer returns final string

---

## Uniform fallback model (messages / enums / FAQs)

For requested locale `L`:

1. Resolve locale (`None` => default; unknown => error).
2. Load default locale document `D` and requested locale document `R`.
3. Effective locale is:
   - `D` if `L == default_locale`
   - `deep_merge(D, R)` otherwise

Merge rules:

- dicts merge recursively,
- scalar values in `R` override `D`,
- lists in `R` replace lists in `D`.

All lookup methods use this same effective view:

- `msg`
- `enum_group`, `enum_values`, `enum_item`, `enum_label`
- `faq_section`, `faq_items`, `faq_item`, `faq_question`, `faq_answer`

---

## Error semantics

- **`LocaleNotFoundError`**: unknown locale or missing locale file.
- **`MissingTranslationError`**: value/path missing after fallback resolution.
- **`LocaleDataError`**: value exists but has wrong type/shape.
- **`PlaceholderError`**: placeholder mismatch, unsupported placeholder syntax, or missing required placeholders.
- **`LocaleEditError`**: invalid/protected/missing edit path.
- **`ValueFormattingError`**: invalid wrapped-value formatting input.

---

## Placeholder model (strict)

Supported placeholders are **top-level identifiers only**:

- `{name}`
- `{user_name}`
- `{amount2}`

Unsupported placeholders (raise `PlaceholderError`):

- `{user.name}`
- `{items[0]}`
- `{user[name]}`

Nested placeholder addressing is intentionally out of scope.

---

## Formatter API (preferred)

### Two-stage temporal pipeline

For wrapped datetimes:

1. **Timezone normalization**
   - timezone resolution order:
     1. `locale_timezones[locale]`
     2. `default_timezone`
     3. UTC

2. **Locale rendering**
   - renderer resolution order:
     1. `renderers[locale]`
     2. `default_renderer`
     3. built-in `StrftimeRenderer`

### Naive vs aware datetimes

- Aware datetime: normalized with `astimezone(resolved_timezone)`.
- Naive datetime:
  - if `naive_input_timezone is None`: left unchanged,
  - else: interpreted in `naive_input_timezone`, then normalized.

### Wrapper helpers

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Only wrapped values are specially formatted.

---

## Usage examples

### Build runtime (non-English default locale)

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
    i18n.msg("user.greeting", locale="xx", name="Sara")
except LocaleNotFoundError:
    ...
```

### Message / enum / FAQ lookup

```python
print(i18n.msg("user.greeting", locale="en", name="Sara"))
print(i18n.enum_label("order_status", "pending", locale="en"))
print(i18n.faq_answer("payment", "refund_time", locale="en"))
```

### Locale renderer + timezone (Persian example)

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
    default_timezone=timezone.utc,
    renderers={"fa": PersianRenderer()},
)

print(
    i18n.msg(
        "user.report",
        locale="fa",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, tzinfo=timezone.utc)),
        amount="(raw amount remains raw unless grouped_number is used)",
        status="...",
        raw_date=date(2026, 4, 17),
    )
)
```

### Editor set/delete behavior

```python
editor.set_value("en", "messages.user.greeting", "Hi {name}")
editor.delete_value("en", "messages.user.greeting")

# deleting a missing path raises LocaleEditError
```

---

## Public API reference

### Builders

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

### Wrappers

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

## Development

Run tests:

```bash
pytest -q
```

See runnable example:

```bash
python examples/basic_usage.py
```
