# Migration Guide

This project keeps backward compatibility while moving to a clearer formatting model.

## What changed

Older design centered on converter methods returning temporal Python objects:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

New design uses a two-step model:

1. Timezone normalization
2. Final rendering to `str`

## Why this changed

Locale-specific calendar output (for example Persian/Jalali) often requires direct final string rendering. Restricting hooks to `date`/`datetime` outputs made that harder than necessary.

## Compatibility behavior

`LocaleValueFormatter` still accepts older converter-style configuration:

- `converters={...}` and `default_converter=...`
- callable converters (`Callable[[date | datetime], date | datetime]`)
- object-based converters with `convert_date` / `convert_datetime`

These are internally adapted to renderer behavior, so migration can be incremental.

## Suggested migration path

1. Keep existing converter configuration working as-is.
2. Add renderer-based implementations for locales that need custom final output.
3. Move locale-specific display logic to `LocaleRenderer`.
4. Remove converter-specific code after parity is confirmed.
