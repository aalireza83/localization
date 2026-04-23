# Validation & Editing

This guide covers `LocaleValidator` and `LocaleEditor` for safe quality control and file updates.

## LocaleValidator

`LocaleValidator` validates locale documents and cross-locale compatibility.

## Basic usage

```python
from localization import LocaleValidator

validator = LocaleValidator(repository)
validator.validate_all()
```

### Validate one locale

```python
validator.validate_single_locale("fa")
```

## Validation rules summary

### Root-level checks

- Locale document must be a JSON object.
- Required keys: `_meta`, `messages`, `enums`, `faqs`.
- `_meta.locale` must match the locale code being validated.
- `_meta.version` must be an integer.

### Messages checks

- `messages` must be an object.
- Leafs must be strings.
- Placeholder names must be simple identifiers.

### Enums checks

- `enums` must be an object.
- Enum groups must include `values` object.
- Enum values must include `label` string.
- Optional `title`/`description` must be strings when present.
- Optional `order` must be integer when present.

### FAQs checks

- `faqs` must be an object.
- Sections must include `items` object.
- Items must include string `question` and `answer`.
- Optional `order` must be integer when present.
- Optional `tags` must be a list of strings when present.

### Cross-locale checks

- Placeholder sets for matching message keys must match the default locale.
- If `require_complete_locales=True`, non-default locales must include every key from the default locale structure.

## LocaleEditor

`LocaleEditor` supports safe dot-path edits with validation before save.

## Basic usage

```python
from localization import LocaleEditor

editor = LocaleEditor(repository, validator)
editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
```

## Reading values

```python
value = editor.get_value("fa", "messages.user.greeting")
```

## Deleting values

```python
editor.delete_value("fa", "faqs.payment.items.refund_time")
```

## Safe editing constraints

- Protected paths under `_meta` cannot be edited.
- Invalid paths raise `LocaleEditError`.
- Changes are validated before persisting to disk.
- A failing validation aborts the save operation.
