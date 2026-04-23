# Validation & Editing

This library provides strict validation and controlled editing helpers for locale files.

## LocaleValidator

`LocaleValidator` checks locale and placeholder consistency.

## Common usage

```python
repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="locales",
    manifest_path="manifest.json",
)

validator.validate_all()
```

## Validation focus

The validator workflow is designed to catch issues such as:

- schema/data shape errors in locale files
- mismatch between manifest locale declarations and available locale data
- placeholder compatibility problems across translations

Run validation early during startup, CI, or release checks.

## LocaleEditor

`LocaleEditor` provides safe path-based updates for locale content.

## Common usage

```python
editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
```

## Safe editing behavior

- Edits target explicit locale + dotted key paths.
- Intended for controlled updates without direct manual JSON traversal.
- Pair with validation (`validate_all`) to keep data quality high.

## Recommended workflow

1. Build runtime.
2. Run `validator.validate_all()`.
3. Apply updates with `editor.set_value(...)`.
4. Re-validate if needed.
5. Clear repository cache when appropriate (`repo.clear_cache()`).
