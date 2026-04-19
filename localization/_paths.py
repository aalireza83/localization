from __future__ import annotations

from typing import Any


PathParts = tuple[str, ...]


def split_path(path: str) -> PathParts:
    """Split a dot path and reject invalid inputs."""
    cleaned = path.strip()
    if not cleaned:
        raise ValueError("Path cannot be empty.")
    parts = tuple(part.strip() for part in cleaned.split("."))
    if any(not part for part in parts):
        raise ValueError(f"Invalid path '{path}'. Empty segments are not allowed.")
    return parts


def get_path(data: dict[str, Any], path: str) -> Any | None:
    node: Any = data
    for part in split_path(path):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = split_path(path)
    node = data
    for part in parts[:-1]:
        current = node.get(part)
        if current is None:
            node[part] = {}
            current = node[part]
        if not isinstance(current, dict):
            raise ValueError(f"Cannot create '{path}': '{part}' is not an object.")
        node = current
    node[parts[-1]] = value


def delete_path(data: dict[str, Any], path: str) -> bool:
    parts = split_path(path)
    node = data
    for part in parts[:-1]:
        current = node.get(part)
        if not isinstance(current, dict):
            return False
        node = current
    return node.pop(parts[-1], None) is not None
