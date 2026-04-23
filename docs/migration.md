# Migration Guide

This project keeps backward compatibility while moving to a clearer formatting model.

## What changed

Older design centered around converter methods that returned temporal values:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

New design separates concerns into two explicit stages:

1. timezone normalization
2. final rendering to `str`

## Why this changed

Locale-specific calendar formatting (for example Persian/Jalali output) often needs direct string rendering. Returning only `date`/`datetime` from locale hooks was too restrictive.

## Converter → renderer model

### New preferred API

Use renderers (`LocaleRenderer`) with:

- `render_date(...) -> str`
- `render_datetime(...) -> str`

### Compatibility behavior

`LocaleValueFormatter` still accepts older converter APIs:

- `converters={...}` and `default_converter=...`
- callable converters (`Callable[[date | datetime], date | datetime]`)
- object-based legacy converters with `convert_date` / `convert_datetime`

Legacy converters are adapted internally to renderer behavior, so migration can be incremental.

## Migration notes

- Existing converter-based code does not need immediate rewrites.
- New code should implement `LocaleRenderer` for final output control.
- If you need locale calendars (for example Jalali/Shamsi), render directly to `str` in the renderer.
- Keep wrapped placeholders (`wrapped_date`, `wrapped_datetime`, etc.) unchanged during migration; behavior remains compatible.
