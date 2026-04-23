# Getting Started

This guide expands on the quick start flow and shows the full runtime setup for `localization`.

## Requirements

- Python 3.11+

## Setup

Install the package:

```bash
pip install localization
```

Or install locally for development:

```bash
pip install -e .
```

## 1) Create `manifest.json`

The manifest declares available locales and the default locale.

```json
{
  "default_locale": "fa",
  "locales": {
    "fa": {"label": "Farsi", "native_name": "فارسی", "direction": "rtl"},
    "en": {"label": "English", "native_name": "English", "direction": "ltr"}
  }
}
```

Rules:
- `default_locale` must be a non-empty string and must exist in `locales`.
- `locales` must be a non-empty object.
- `direction` must be `ltr` or `rtl`.

## 2) Create locale files

Create `locales/fa.json` and `locales/en.json` with this minimum root structure:

- `_meta`
- `messages`
- `enums`
- `faqs`

Example (`fa.json`):

```json
{
  "_meta": {"locale": "fa", "version": 1},
  "messages": {
    "user": {
      "greeting": "سلام {name}",
      "report": "تاریخ {date}، زمان {dt}"
    }
  },
  "enums": {},
  "faqs": {}
}
```

Example (`en.json`):

```json
{
  "_meta": {"locale": "en", "version": 1},
  "messages": {
    "user": {
      "greeting": "Hello {name}",
      "report": "Date {date}, datetime {dt}"
    }
  },
  "enums": {},
  "faqs": {}
}
```

## 3) Build runtime components

`build_i18n_runtime(...)` wires repository, validator, service, and editor in one step.

```python
from pathlib import Path
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir=Path("locales"),
    manifest_path=Path("manifest.json"),
)
```

Returned components:
- `repo`: `LocaleRepository`
- `validator`: `LocaleValidator`
- `i18n`: `I18nService`
- `editor`: `LocaleEditor`

## 4) Validate locale data

```python
validator.validate_all()
```

Validation checks schema shape, placeholder rules, and cross-locale placeholder compatibility.

## 5) Resolve messages

```python
print(i18n.msg("user.greeting", name="Sara"))
print(i18n.msg("user.greeting", locale="en", name="Sara"))
```

By default, `i18n.msg(...)` uses the manifest default locale when `locale` is not provided.

## Full walkthrough example

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
        "messages": {"user": {"greeting": "سلام {name}", "report": "تاریخ {date}، زمان {dt}"}},
        "enums": {},
        "faqs": {},
    }
    en = {
        "_meta": {"locale": "en", "version": 1},
        "messages": {"user": {"greeting": "Hello {name}", "report": "Date {date}, datetime {dt}"}},
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

See a larger runnable sample in [`examples/basic_usage.py`](../examples/basic_usage.py).
