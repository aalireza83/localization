# Validation and Editing

This library includes validation and safe editing helpers for locale datasets.

## LocaleValidator

Use `LocaleValidator` to verify locale file structure and placeholder consistency.

```python
from localization import LocaleRepository, LocaleValidator

repo = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
validator = LocaleValidator(repo)
validator.validate_all()
```

### Validation focus areas

- Manifest and locale consistency
- Translation structure sanity checks
- Placeholder compatibility
- Rejection of invalid nested placeholder names (for example `{user.name}`)

## LocaleEditor

Use `LocaleEditor` for path-based updates and retrieval in locale files.

```python
from localization import LocaleEditor, LocaleRepository, LocaleValidator

repo = LocaleRepository(base_dir=locales_dir, manifest_path=manifest_path)
validator = LocaleValidator(repo)
editor = LocaleEditor(repo, validator)

editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
print(editor.get_value("fa", "messages.user.operation_failed"))
```

### Safe editing behavior

- Invalid or missing paths raise edit errors.
- Use explicit dotted paths (for example `messages.user.greeting`).
- Re-run validation after significant edits.
- Repository cache can be cleared when needed via `repo.clear_cache()`.
