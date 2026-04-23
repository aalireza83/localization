# Locale Schema

This document describes the JSON schema conventions used by the library.

## Root structure

Each locale file must be a JSON object with these required root keys:

- `_meta`
- `messages`
- `enums`
- `faqs`

Example:

```json
{
  "_meta": {"locale": "en", "version": 1},
  "messages": {},
  "enums": {},
  "faqs": {}
}
```

## `_meta`

Required shape:

- `_meta.locale`: must match the locale filename/code being validated.
- `_meta.version`: must be an integer.

Example:

```json
"_meta": {"locale": "fa", "version": 1}
```

## `messages`

`messages` is a nested object tree where leaf values must be strings.

```json
"messages": {
  "user": {
    "greeting": "Hello {name}",
    "report": "Date {date}, datetime {dt}"
  }
}
```

Placeholder rules:
- Placeholders are parsed from Python `str.format` templates.
- Only simple top-level identifiers are allowed (for example `{name}`, `{order_id}`).
- Complex expressions like `{user.name}` are rejected.

Cross-locale rule:
- For non-default locales, placeholder sets must match the default locale for corresponding message keys.

## `enums`

`enums` stores structured option labels and metadata.

Example:

```json
"enums": {
  "order_status": {
    "title": "Order status",
    "values": {
      "pending": {
        "label": "Pending payment",
        "description": "Awaiting payment",
        "order": 1
      }
    }
  }
}
```

Rules:
- `enums.<name>` must be an object.
- Optional `title` must be a string when present.
- `values` must be an object.
- Each value item must include `label` (string).
- Optional `description` must be a string when present.
- Optional `order` must be an integer when present.

## `faqs`

`faqs` stores structured FAQ sections.

Example:

```json
"faqs": {
  "payment": {
    "title": "Payments",
    "items": {
      "refund_time": {
        "question": "How long does a refund take?",
        "answer": "Refunds usually take 3 to 7 business days.",
        "order": 1,
        "tags": ["refund", "billing"]
      }
    }
  }
}
```

Rules:
- `faqs.<section>` must be an object.
- Optional `title` must be a string when present.
- `items` must be an object.
- Each FAQ item must include `question` and `answer` as strings.
- Optional `order` must be an integer when present.
- Optional `tags` must be a list of strings when present.

## Expectations for locale completeness

By default, the library deep-merges requested locale data over the default locale for reads.
That means missing keys can fall back to default values in lookups.

If you need strict completeness checks, enable validator construction with:

```python
LocaleValidator(repository, require_complete_locales=True)
```

With `require_complete_locales=True`, missing keys compared to the default locale cause validation errors.
