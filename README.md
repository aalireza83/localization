# localization

Small, explicit, production-oriented Python localization for JSON locale files.

## Why this library?

`localization` gives you a clear, manifest-driven workflow for multilingual apps using plain JSON files. It focuses on predictable behavior (explicit locale resolution, strict validation, and wrapper-based value formatting) so teams can safely maintain translations in production.

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

### From PyPI

```bash
pip install localization
```

### Local development install

```bash
pip install -e .
```

## Quick Start

```python
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from localization import build_i18n_runtime, wrapped_date, wrapped_datetime

with TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    locales_dir = root / "locales"
    locales_dir.mkdir(parents=True, exist_ok=True)

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
                "report": "تاریخ {date}، زمان {dt}",
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
                "report": "Date {date}, datetime {dt}",
            }
        },
        "enums": {},
        "faqs": {},
    }

    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps(fa, ensure_ascii=False, indent=2), encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en, ensure_ascii=False, indent=2), encoding="utf-8")

    repo, validator, i18n, editor = build_i18n_runtime(
        base_dir=locales_dir,
        manifest_path=root / "manifest.json",
    )

    validator.validate_all()

    print(i18n.msg("user.greeting", name="Sara"))
    print(i18n.msg(
        "user.report",
        locale="en",
        date=wrapped_date(date(2026, 4, 17)),
        dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, tzinfo=UTC)),
    ))
```

## Expected File Layout

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

Manifest rules:
- `default_locale` must be one of the declared locale keys.
- `locales` must be non-empty.
- Unknown locales are errors (no silent fallback to undeclared locale codes).

## Basic Usage

### Message lookup

```python
print(i18n.msg("user.greeting", name="Sara"))
print(i18n.msg("user.greeting", locale="en", name="Sara"))
```

### Placeholders

```python
print(i18n.msg("user.greeting", name="Sara"))
```

### Locale selection

```python
# Uses default locale from manifest.
print(i18n.msg("user.greeting", name="Sara"))

# Uses explicit locale.
print(i18n.msg("user.greeting", locale="fa", name="Sara"))
```

## Advanced Usage (preview)

Advanced formatting and lookup tools are available through wrappers and formatter customization:

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `enum_ref(...)`
- `grouped_number(...)`
- `LocaleValueFormatter` custom renderers/timezones

See full details in:
- [Value Formatting](docs/value-formatting.md)
- [Locale Schema](docs/locale-schema.md)

## Documentation

- Getting Started → [docs/getting-started.md](docs/getting-started.md)
- Locale Schema → [docs/locale-schema.md](docs/locale-schema.md)
- Value Formatting → [docs/value-formatting.md](docs/value-formatting.md)
- Validation & Editing → [docs/editor-and-validation.md](docs/editor-and-validation.md)
- Migration Guide → [docs/migration.md](docs/migration.md)

## Run tests

```bash
pytest -q
```

## Example script

```bash
python examples/basic_usage.py
```
