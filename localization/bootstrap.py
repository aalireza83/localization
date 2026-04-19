from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from localization.editor import LocaleEditor
from localization.formatter import LocaleValueFormatter
from localization.repository import LocaleRepository
from localization.service import I18nService
from localization.validator import LocaleValidator


@dataclass(frozen=True, slots=True)
class I18nRuntime:
    """Container object for localization runtime components."""

    repository: LocaleRepository
    validator: LocaleValidator
    i18n: I18nService
    editor: LocaleEditor


def build_i18n_runtime(
    *,
    base_dir: str | Path,
    manifest_path: str | Path,
    default_context_provider: Callable[[], dict[str, Any]] | None = None,
    strict_missing_keys: bool = True,
    require_complete_locales: bool = False,
    value_formatter: LocaleValueFormatter | None = None,
) -> tuple[LocaleRepository, LocaleValidator, I18nService, LocaleEditor]:
    """Build localization runtime components with consistent wiring."""

    repository = LocaleRepository(base_dir=base_dir, manifest_path=manifest_path)
    validator = LocaleValidator(repository, require_complete_locales=require_complete_locales)
    i18n = I18nService(
        repository=repository,
        default_context_provider=default_context_provider,
        strict_missing_keys=strict_missing_keys,
        value_formatter=value_formatter,
    )
    editor = LocaleEditor(repository=repository, validator=validator)
    return repository, validator, i18n, editor


def build_runtime(
    *,
    base_dir: str | Path,
    manifest_path: str | Path,
    default_context_provider: Callable[[], dict[str, Any]] | None = None,
    strict_missing_keys: bool = True,
    require_complete_locales: bool = False,
    value_formatter: LocaleValueFormatter | None = None,
) -> I18nRuntime:
    """Build localization runtime and return a structured runtime object."""

    repository, validator, i18n, editor = build_i18n_runtime(
        base_dir=base_dir,
        manifest_path=manifest_path,
        default_context_provider=default_context_provider,
        strict_missing_keys=strict_missing_keys,
        require_complete_locales=require_complete_locales,
        value_formatter=value_formatter,
    )
    return I18nRuntime(repository=repository, validator=validator, i18n=i18n, editor=editor)
