# localization

Small, explicit, production-oriented Python localization for JSON locale files.

## Why this library?

`localization` gives Python projects a predictable, file-based i18n workflow with strict locale validation, explicit runtime behavior, and safe editing tools for production use.

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

### From source (local development)

```bash
pip install -e .
```

### Standard install

```bash
pip install .
```

## Quick Start

```python
from datetime import UTC, date, datetime
from pathlib import Path
import json

from localization import build_i18n_runtime, wrapped_date, wrapped_datetime

root = Path(".")
(root / "locales").mkdir(exist_ok=True)

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
}

en = {
    "_meta": {"locale": "en", "version": 1},
    "messages": {
        "user": {
            "greeting": "Hello {name}",
            "report": "Date {date}, datetime {dt}",
        }
    },
}

(root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
(root / "locales" / "fa.json").write_text(json.dumps(fa, ensure_ascii=False, indent=2), encoding="utf-8")
(root / "locales" / "en.json").write_text(json.dumps(en, ensure_ascii=False, indent=2), encoding="utf-8")

_, _, i18n, _ = build_i18n_runtime(
    base_dir=root / "locales",
    manifest_path=root / "manifest.json",
)

print(i18n.msg("user.greeting", locale="fa", name="Sara"))
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

## Basic Usage

```python
from datetime import UTC, date, datetime
from enum import Enum
from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime

# message lookup
print(i18n.msg("user.greeting", locale="en", name="Sara"))

# placeholders (wrapped + raw values)
print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),
))

# locale selection
print(i18n.msg("user.greeting", locale="fa", name="Sara"))
print(i18n.msg("user.greeting", locale="en", name="Sara"))

class OrderStatus(Enum):
    PENDING = "pending"

print(i18n.msg("order.status", locale="fa", status=enum_ref("order_status", OrderStatus.PENDING)))
```

## Advanced Usage

Advanced formatting and renderer features are available for:

- `wrapped_date` / `wrapped_datetime`
- `enum_ref`
- `grouped_number`
- Locale renderer customization and temporal formatting behavior

See the full guides in `docs/`.

## Documentation

- Getting Started → `docs/getting-started.md`
- Locale Schema → `docs/locale-schema.md`
- Value Formatting → `docs/value-formatting.md`
- Validation & Editing → `docs/editor-and-validation.md`
- Migration Guide → `docs/migration.md`

## Run Tests

```bash
pytest -q
```

## Example Script

```bash
python examples/basic_usage.py
```
