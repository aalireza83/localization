# localization

Small, explicit, production-oriented Python localization for JSON locale files.

## Why this library?

`localization` gives you a strict, predictable i18n workflow for Python projects that store translations in JSON files. It combines manifest-based locale discovery, runtime message lookup, placeholder formatting, and validation/editing utilities so teams can ship multilingual features without hidden behavior.

## Features

- Manifest-based locale discovery
- Message lookup with fallback
- Structured translation lookup (`enums`, `faqs`)
- Explicit wrapper-based placeholder formatting
- Validation of locale schemas and placeholder compatibility
- Safe path-based locale editing
- Two-stage locale-aware date/datetime formatting:
  1. Timezone normalization
  2. Locale rendering

## Installation

### From source (local repository)

```bash
pip install .
```

### Editable install for development

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
from zoneinfo import ZoneInfo

from localization import (
    LocaleRenderer,
    LocaleValueFormatter,
    build_i18n_runtime,
    wrapped_date,
    wrapped_datetime,
)


class PersianRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"


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

    formatter = LocaleValueFormatter(
        default_now=lambda: datetime.now(tz=UTC),
        locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
        renderers={"fa": PersianRenderer()},
    )

    _, validator, i18n, _ = build_i18n_runtime(
        base_dir=locales_dir,
        manifest_path=root / "manifest.json",
        value_formatter=formatter,
    )

    validator.validate_all()

    print(i18n.msg("user.greeting", locale="fa", name="Sara"))
    print(i18n.msg(
        "user.report",
        locale="fa",
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
print(i18n.msg("user.greeting"))            # uses manifest default_locale
print(i18n.msg("user.greeting", locale="en"))
```

## Advanced Usage (Preview)

- Temporal wrappers: `wrapped_date`, `wrapped_datetime`
- Structured references: `enum_ref`
- Numeric formatting wrapper: `grouped_number`
- Formatter customization: locale timezones, renderers, and fallback behavior in `LocaleValueFormatter`

See the documentation pages below for full details.

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
