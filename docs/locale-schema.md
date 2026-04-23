# Locale Schema

This document describes the expected structure for locale JSON files.

## Top-level structure

A locale file typically contains:

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

`_meta` identifies the file locale and schema version.

```json
{
  "_meta": {
    "locale": "fa",
    "version": 1
  }
}
```

Expectations:

- `_meta.locale` should match the file’s locale key in the manifest.
- `_meta.version` is an integer version marker.

## `messages`

`messages` stores nested translation keys for message lookup.

```json
{
  "messages": {
    "user": {
      "greeting": "Hello {name}",
      "report": "Date {date}, amount {amount}"
    }
  }
}
```

Usage behavior:

- Keys are looked up by dotted paths (for example, `user.greeting`).
- Placeholders (like `{name}`) must be compatible across locales for corresponding keys.

## `enums`

`enums` stores label maps for enum-like values.

```json
{
  "enums": {
    "order_status": {
      "values": {
        "pending": {
          "label": "Pending payment",
          "description": "Awaiting payment"
        }
      }
    }
  }
}
```

Common usage:

- `enum_ref("order_status", value)` resolves labels from this section.

## `faqs`

`faqs` stores FAQ groups and items.

```json
{
  "faqs": {
    "payment": {
      "items": {
        "refund_time": {
          "question": "How long does a refund take?",
          "answer": "Refunds usually take 3 to 7 business days."
        }
      }
    }
  }
}
```

## Manifest-level constraints (related)

From `manifest.json`:

- `locales` must be non-empty.
- `default_locale` can be any declared locale.
- Unknown locales are errors (no silent fallback).

## Practical rules

- Keep locale structures aligned across all languages.
- Keep placeholder names stable between corresponding message keys.
- Prefer explicit domains (`messages`, `enums`, `faqs`) instead of mixed ad-hoc structures.
