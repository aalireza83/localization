from __future__ import annotations

import re
from string import Formatter

from localization.exceptions import PlaceholderError

_TOP_LEVEL_PLACEHOLDER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def extract_top_level_placeholders(template: str, *, path: str) -> set[str]:
    """Extract placeholders and enforce top-level-only field syntax."""

    names: set[str] = set()
    for _, field_name, _, _ in Formatter().parse(template):
        if not field_name:
            continue
        if not _TOP_LEVEL_PLACEHOLDER_RE.fullmatch(field_name):
            raise PlaceholderError(
                f"Unsupported placeholder at '{path}': {field_name!r}. "
                "Only top-level identifiers are supported (e.g. {name}, {amount})."
            )
        names.add(field_name)
    return names
