from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    with TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        locales = root / "locales"
        manifest_path = root / "manifest.json"

        manifest = {
            "default_locale": "fa",
            "locales": {
                "fa": {"label": "فارسی", "native_name": "فارسی", "direction": "rtl"},
                "en": {"label": "English", "native_name": "English", "direction": "ltr"},
            },
        }

        fa = {
            "_meta": {"locale": "fa", "version": 1},
            "messages": {
                "user": {
                    "operation_failed": "عملیات ناموفق بود.",
                    "greeting": "سلام {name}",
                    "report": "تاریخ {date}، زمان {dt}، مبلغ {amount}، وضعیت {status}، خام {raw_date}",
                }
            },
            "enums": {
                "order_status": {
                    "title": "وضعیت سفارش",
                    "values": {
                        "pending": {"label": "در انتظار پرداخت", "description": "Awaiting payment", "order": 10}
                    },
                }
            },
            "faqs": {
                "payment": {
                    "title": "سوالات پرداخت",
                    "items": {
                        "refund_time": {
                            "question": "بازپرداخت چقدر طول می‌کشد؟",
                            "answer": "معمولاً بین ۳ تا ۷ روز کاری.",
                            "order": 20,
                            "tags": ["payment", "refund"],
                        }
                    },
                }
            },
        }

        en = {
            "_meta": {"locale": "en", "version": 1},
            "messages": {
                "user": {
                    "greeting": "Hello {name}",
                    "report": "Date {date}, datetime {dt}, amount {amount}, status {status}, raw {raw_date}",
                }
            },
            "enums": {
                "order_status": {
                    "values": {
                        "pending": {"label": "Pending payment"}
                    }
                }
            },
            "faqs": {
                "payment": {
                    "items": {
                        "refund_time": {
                            "question": "How long does a refund take?",
                            "answer": "Refunds usually take 3 to 7 business days.",
                        }
                    }
                }
            },
        }

        _write_json(manifest_path, manifest)
        _write_json(locales / "fa.json", fa)
        _write_json(locales / "en.json", en)

        formatter = LocaleValueFormatter(
            default_now=lambda: datetime.now(timezone.utc),
            locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
            default_timezone=timezone.utc,
            renderers={"fa": PersianRenderer()},
        )

        repo, validator, i18n, editor = build_i18n_runtime(
            base_dir=locales,
            manifest_path=manifest_path,
            value_formatter=formatter,
        )

        validator.validate_all()

        print(i18n.msg("user.operation_failed"))  # locale=None -> default locale (fa)
        print(i18n.msg("user.greeting", locale="en", name="Sara"))
        print(
            i18n.msg(
                "user.report",
                locale="fa",
                date=wrapped_date(date(2026, 4, 17)),
                dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=timezone.utc)),
                amount=grouped_number("1234567"),
                status=enum_ref("order_status", OrderStatus.PENDING),
                raw_date=date(2026, 4, 17),
            )
        )

        editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
        print(i18n.msg("user.operation_failed", locale="fa"))

        try:
            editor.delete_value("fa", "messages.user.not_existing")
        except Exception as exc:  # demo only
            print(type(exc).__name__, exc)

        print(formatter.now_as_text(locale="en"))

        repo.clear_cache()


if __name__ == "__main__":
    main()
