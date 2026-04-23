# localization

Small, explicit, production-oriented Python localization for JSON locale files.

## Why this library?

`localization` provides a predictable i18n workflow for Python applications that store translations in JSON files. It keeps runtime behavior explicit (locale resolution, fallback, placeholder checks, value formatting) so teams can ship and maintain multilingual features with confidence.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Two-stage locale-aware date/datetime formatting:
  1) timezone normalization
  2) locale rendering

## Installation

### From PyPI (when published)

```bash
pip install localization
```

### Local development install

```bash
pip install -e .
```

## Quick Start

Create the files below and run the script.

```python
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from localization import build_i18n_runtime, wrapped_date

root = Path(".")
locales_dir = root / "locales"
locales_dir.mkdir(exist_ok=True)

manifest = {
    "default_locale": "fa",
    "locales": {
        "fa": {"label": "Farsi", "native_name": "فارسی", "direction": "rtl"},
        "en": {"label": "English", "native_name": "English", "direction": "ltr"},
    },
}

fa = {
    "_meta": {"locale": "fa", "version": 1},
    "messages": {
        "user": {
            "greeting": "سلام {name}",
            "report": "تاریخ {date}",
        }
    },
    "enums": {},
    "faqs": {},
}

en = {
    "_meta": {"locale": "en", "version": 1},
    "messages": {
        "user": {
            "greeting": "Hello {name}",
            "report": "Date {date}",
        }
    },
    "enums": {},
    "faqs": {},
}

(root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(locales_dir / "fa.json").write_text(json.dumps(fa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(locales_dir / "en.json").write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir=locales_dir,
    manifest_path=root / "manifest.json",
)

validator.validate_all()

print(i18n.msg("user.greeting", locale="en", name="Sara"))
print(i18n.msg("user.report", locale="fa", date=wrapped_date(date(2026, 4, 17))))
```

## Expected File Layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

## Basic Usage

### Message lookup

```python
print(i18n.msg("user.greeting", locale="en", name="Sara"))
```

### Placeholders

```python
print(i18n.msg("user.greeting", locale="fa", name="سارا"))
```

### Locale selection

```python
# Uses the requested locale.
print(i18n.msg("user.greeting", locale="fa", name="Sara"))

# Uses the default locale from manifest when locale is omitted.
print(i18n.msg("user.greeting", name="Sara"))
```

## Advanced Usage (preview)

For advanced value formatting and customization, see the docs for:

- `wrapped_date` / `wrapped_datetime`
- `enum_ref`
- `grouped_number`
- `LocaleValueFormatter` customization with locale timezones and renderers

## Documentation

- Getting Started → `docs/getting-started.md`
- Locale Schema → `docs/locale-schema.md`
- Value Formatting → `docs/value-formatting.md`
- Validation & Editing → `docs/editor-and-validation.md`
- Migration Guide → `docs/migration.md`

## Run tests

```bash
pytest -q
```

## Example script

```bash
python examples/basic_usage.py
```
