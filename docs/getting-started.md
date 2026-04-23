# Getting Started

This guide walks through the full setup flow for `localization`: defining a manifest, creating locale files, building a runtime, validating data, and rendering messages.

## 1) Project layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

## 2) Manifest setup

`manifest.json` declares available locales and default behavior:

```json
{
  "default_locale": "fa",
  "locales": {
    "fa": {"label": "Farsi", "native_name": "فارسی", "direction": "rtl"},
    "en": {"label": "English", "native_name": "English", "direction": "ltr"}
  }
}
```

Key rules:

- `locales` must be non-empty.
- `default_locale` must be one of the declared locales.
- Unknown locales are treated as errors (no silent fallback).

## 3) Create locale JSON files

Each locale file includes `_meta`, `messages`, and optional `enums`/`faqs` sections.

Example `locales/fa.json`:

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

Example `locales/en.json`:

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

## 4) Build runtime

Use `build_i18n_runtime(...)` to create repository, validator, service, and editor objects.

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir=locales_dir,
    manifest_path=manifest_path,
)
```

The returned objects are:

- `repo`: `LocaleRepository`
- `validator`: `LocaleValidator`
- `i18n`: `I18nService`
- `editor`: `LocaleEditor`

## 5) Full walkthrough example

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

For a runnable script using a richer dataset, see `examples/basic_usage.py`.
