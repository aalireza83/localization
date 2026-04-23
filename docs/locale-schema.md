# Locale Schema

Locale files are JSON documents with a fixed root structure.

## Required root keys

Each locale file must include:

- `_meta`
- `messages`
- `enums`
- `faqs`

## `_meta`

`_meta` must be an object with:

- `locale` (must exactly match the locale file identity)
- `version` (integer)

Example:

```json
"_meta": {"locale": "fa", "version": 1}
```

## `messages`

`messages` is a nested object tree where all leaf values are strings.

```json
"messages": {
  "user": {
    "greeting": "Hello {name}",
    "report": "Date {date}, amount {amount}"
  }
}
```

Rules:

- Any nested node must be an object.
- Any leaf in `messages` must be a string.
- Placeholders must use top-level identifier names only (for example `{user_name}`).

## `enums`

`enums` is an object of enum groups.

```json
"enums": {
  "order_status": {
    "title": "Order status",
    "values": {
      "pending": {
        "label": "Pending payment",
        "description": "Awaiting payment",
        "order": 10
      }
    }
  }
}
```

Rules:

- Each enum group must be an object.
- `title` is optional; if present it must be a string.
- `values` is required and must be an object.
- Each value item must be an object with required `label` string.
- `description` is optional string.
- `order` is optional integer.

## `faqs`

`faqs` is an object of FAQ sections.

```json
"faqs": {
  "payment": {
    "title": "Payment",
    "items": {
      "refund_time": {
        "question": "How long does a refund take?",
        "answer": "Refunds usually take 3 to 7 business days.",
        "order": 1,
        "tags": ["refund", "timing"]
      }
    }
  }
}
```

Rules:

- Each section must be an object.
- `title` is optional string.
- `items` is required object.
- Each item must include:
  - `question` (string)
  - `answer` (string)
- Optional fields:
  - `order` (integer)
  - `tags` (list of strings)

## Cross-locale expectations

- Non-default locales are validated against the default locale for placeholder compatibility in `messages`.
- If `require_complete_locales=True`, all keys from the default locale must exist in each non-default locale.

## Example minimal locale

```json
{
  "_meta": {"locale": "en", "version": 1},
  "messages": {"app": {"title": "Demo"}},
  "enums": {},
  "faqs": {}
}
```
