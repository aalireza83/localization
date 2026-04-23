# Locale Schema

This document describes the expected structure of locale JSON files and the conventions used by the library.

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
  "messages": {
    "user": {
      "greeting": "Hello {name}"
    }
  },
  "enums": {
    "order_status": {
      "values": {
        "pending": {
          "label": "Pending payment",
          "description": "Awaiting payment"
        }
      }
    }
  },
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

## `messages`

- Organized as nested objects.
- Leaves are translation strings.
- Placeholders use Python `str.format(...)` style, such as `{name}`.
- Placeholder names must be simple tokens (for example `{user.name}` is invalid).

## `enums`

Use `enums` for structured label lookup (for example status values).

Expected pattern:

```json
{
  "enums": {
    "enum_name": {
      "values": {
        "value_key": {
          "label": "...",
          "description": "..."
        }
      }
    }
  }
}
```

- `label` is commonly used in UI output.
- `description` is optional metadata.

## `faqs`

Use `faqs` for grouped FAQ content.

Expected pattern:

```json
{
  "faqs": {
    "group": {
      "items": {
        "item_key": {
          "question": "...",
          "answer": "..."
        }
      }
    }
  }
}
```

## Rules and expectations

- Locale files should align with manifest locale keys.
- Keep placeholder sets compatible across locales for equivalent message paths.
- Keep schema shape consistent across locales where possible.
- Treat unknown locale requests as errors.

## Related APIs

- Message lookup: `i18n.msg(...)`
- Enum reference wrapper: `enum_ref(...)`
- Validation: `LocaleValidator`
