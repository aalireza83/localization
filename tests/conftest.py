from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def sample_i18n_files(tmp_path: Path) -> tuple[Path, Path]:
    locales_dir = tmp_path / "locales"
    manifest_path = tmp_path / "manifest.json"

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
                    "pending": {"label": "در انتظار پرداخت", "description": "Awaiting payment", "order": 10},
                    "canceled": {"label": "لغو شده", "order": 20},
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
                    "pending": {"label": "Pending payment"},
                    "canceled": {"label": "Canceled"},
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

    locales_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (locales_dir / "fa.json").write_text(json.dumps(fa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (locales_dir / "en.json").write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return locales_dir, manifest_path
