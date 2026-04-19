from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

Direction = Literal["ltr", "rtl"]


@dataclass(frozen=True, slots=True)
class LocaleDescriptor:
    """Metadata for a locale declared in the manifest."""

    code: str
    label: str
    native_name: str
    direction: Direction = "ltr"


class ManifestLocaleEntry(TypedDict, total=False):
    label: str
    native_name: str
    direction: Direction


class ManifestData(TypedDict):
    default_locale: str
    locales: dict[str, ManifestLocaleEntry]
