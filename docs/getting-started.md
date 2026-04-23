# Getting Started

This guide covers end-to-end setup for a JSON-file localization runtime using `localization`.

## Requirements

- Python 3.11+

## Installation

```bash
pip install -e .
```

or:

```bash
pip install .
```

## Project Layout

```text
project/
  manifest.json
  locales/
    fa.json
    en.json
```

## 1) Create `manifest.json`

`manifest.json` declares available locales and the default locale.

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

- `locales` must be non-empty.
- `default_locale` must be one of declared locales.
- Unknown locales are treated as errors (no silent fallback).

## 2) Create locale files

Each locale file contains `_meta` and domain sections such as `messages`, `enums`, and `faqs`.

### `locales/fa.json`

```json
{
  "_meta": {"locale": "fa", "version": 1},
  "messages": {
    "user": {
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

### `locales/en.json`

```json
{
  "_meta": {"locale": "en", "version": 1},
  "messages": {
    "user": {
      "greeting": "Hello {name}",
      "report": "Date {date}, datetime {dt}, amount {amount}, status {status}, raw {raw_date}"
    }
  },
  "enums": {
    "order_status": {
      "values": {
        "pending": {
          "label": "Pending payment",
          "description": "Awaiting payment"
        }
      }
    }
  },
  "faqs": {
    "payment": {
      "items": {
        "refund_time": {
          "question": "How long does a refund take?",
          "answer": "Refunds usually take 3 to 7 business days."
        }
      }
    }
  }
}
```

## 3) Build runtime

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="locales",
    manifest_path="manifest.json",
)
```

Runtime parts:

- `repo`: locale repository with file-backed loading/cache
- `validator`: schema + placeholder validation
- `i18n`: runtime message lookup and formatting
- `editor`: safe path-based locale updates

## 4) Full usage walkthrough

```python
from datetime import UTC, date, datetime, timezone
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
    default_now=lambda: datetime.now(timezone.utc),
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

# Unknown locale fails loudly
try:
    i18n.msg("user.greeting", locale="de", name="Sara")
except Exception as exc:
    print(type(exc).__name__, exc)

editor.set_value("fa", "messages.user.greeting", "سلام کاربر")
print(i18n.msg("user.greeting", locale="fa", name="سارا"))

repo.clear_cache()
```

## See also

- Locale schema details: `docs/locale-schema.md`
- Formatting details: `docs/value-formatting.md`
- Editing and validation: `docs/editor-and-validation.md`
- Migration notes: `docs/migration.md`
