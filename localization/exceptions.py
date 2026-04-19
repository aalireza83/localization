from __future__ import annotations


class I18nError(Exception):
    """Base exception for all localization package errors."""


class ManifestError(I18nError):
    """Raised when the manifest file is missing or invalid."""


class LocaleNotFoundError(I18nError):
    """Raised when a locale is not declared in the manifest or file is missing."""


class LocaleDataError(I18nError):
    """Raised when locale JSON content does not match the expected schema."""


class MissingTranslationError(I18nError):
    """Raised when a requested translation key cannot be resolved."""


class PlaceholderError(I18nError):
    """Raised when placeholders are invalid or mismatched."""


class ValueFormattingError(I18nError):
    """Raised when an explicitly wrapped placeholder value cannot be formatted."""


class LocaleEditError(I18nError):
    """Raised when an edit operation cannot be applied safely."""


# Backward-compatible aliases.
TranslationValidationError = LocaleDataError
TranslationKeyNotFoundError = MissingTranslationError
