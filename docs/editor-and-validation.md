# Validation & Editing

This guide covers locale validation rules and safe editing through runtime APIs.

## LocaleValidator usage

Create a validator from the runtime builder:

```python
from localization import build_i18n_runtime

repo, validator, i18n, editor = build_i18n_runtime(
    base_dir="locales",
    manifest_path="manifest.json",
)
```

Run full validation:

```python
validator.validate_all()
```

Validate one locale:

```python
validator.validate_single_locale("fa")
```

## Validation rules summary

### Root requirements

Each locale must be an object with required keys:

- `_meta`
- `messages`
- `enums`
- `faqs`

`_meta.locale` must match the locale identifier and `_meta.version` must be an integer.

### Message rules

- Message trees must be objects.
- Final values must be strings.
- Placeholders must be simple top-level identifiers.

### Enum rules

- Each enum group is an object.
- `values` is required object.
- Each enum item requires `label` string.
- Optional: `title` string, `description` string, `order` integer.

### FAQ rules

- Each FAQ section is an object.
- `items` is required object.
- Each FAQ item requires `question` and `answer` strings.
- Optional: `order` integer, `tags` list of strings.

### Cross-locale rules

For non-default locales:

- Message placeholders must match the default locale's placeholders.
- If `require_complete_locales=True`, missing keys compared to default locale are errors.

## LocaleEditor usage

`LocaleEditor` performs path-based edits and validates before writing.

### Read a value

```python
value = editor.get_value("fa", "messages.user.greeting")
```

### Set a value safely

```python
editor.set_value("fa", "messages.user.operation_failed", "خطا در انجام عملیات")
```

### Delete a value safely

```python
editor.delete_value("fa", "faqs.payment.items.refund_time")
```

## Safe editing behavior

- Writes are validated through `LocaleValidator` before save.
- Invalid edits raise exceptions instead of saving broken files.
- Protected paths under `_meta` cannot be edited.
- Invalid dot paths raise edit errors.
