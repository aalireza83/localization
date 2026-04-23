# Getting Started

This guide walks through setting up a minimal `localization` runtime with JSON locale files.

## Requirements

- Python 3.11+

## Installation

### From PyPI (when published)

```bash
pip install localization
```

### Local development install

```bash
pip install -e .
```

## Project layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

## Step 1: Create `manifest.json`

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
- Unknown locales are errors (no silent fallback).

## Step 2: Add locale files

Create `locales/fa.json` and `locales/en.json`.

Example `fa.json`:

```json
{
  "_meta": {"locale": "fa", "version": 1},
  "messages": {
    "user": {
      "operation_failed": "عملیات ناموفق بود.",
      "greeting": "سلام {name}",
      "report": "تاریخ {date}، زمان {dt}، مبلغ {amount}، وضعیت {status}، خام {raw_date}"
    }
  },
  "enums": {
    "order_status": {
      "values": {
        "pending": {"label": "در انتظار پرداخت"}
      }
    }
  },
  "faqs": {
    "payment": {
      "items": {
        "refund_time": {
          "question": "بازپرداخت چقدر طول می‌کشد؟",
          "answer": "معمولاً بین ۳ تا ۷ روز کاری."
        }
      }
    }
  }
}
```

## Step 3: Build runtime

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="locales",
    manifest_path="manifest.json",
)
```

You can also use `build_runtime(...)` if you prefer a structured runtime object.

## Step 4: Validate locales

```python
validator.validate_all()
```

## Step 5: Use the service

```python
print(i18n.msg("user.greeting", locale="en", name="Sara"))
print(i18n.msg("user.greeting", name="Sara"))  # default locale from manifest
```

## Full walkthrough example

```python
from __future__ import annotations

from datetime import UTC, date, datetime
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
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d})"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"jalali({value.year}-{value.month:02d}-{value.day:02d} {value.hour:02d}:{value.minute:02d}:{value.second:02d})"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    renderers={"fa": PersianRenderer()},
)

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="locales",
    manifest_path="manifest.json",
    value_formatter=formatter,
)

validator.validate_all()

print(i18n.msg("user.greeting", name="Sara"))
print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    status=enum_ref("order_status", OrderStatus.PENDING),
    raw_date=date(2026, 4, 17),
))

editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
print(i18n.msg("user.operation_failed", locale="fa"))

repo.clear_cache()
```
