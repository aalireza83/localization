# Migration Guide

This guide summarizes temporal formatting changes and compatibility behavior.

## Background

Older designs centered around converter methods returning Python temporal values:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

The current design separates:

1. timezone normalization
2. final rendering to `str`

## Why this changed

Locale-specific calendar output (for example Persian/Jalali) often needs direct string rendering.
Returning only `date`/`datetime` from locale hooks was too restrictive.

## Current model

`LocaleValueFormatter` now uses renderer-based final output with explicit resolution:

- locale renderer from `renderers[locale]`
- `default_renderer`
- built-in `StrftimeRenderer`

Timezone normalization stays explicit and deterministic before rendering.

## Backward compatibility

`LocaleValueFormatter` still accepts legacy converter APIs:

- `converters={...}` and `default_converter=...`
- callable converters (`Callable[[date | datetime], date | datetime]`)
- object-based converters implementing `convert_date` / `convert_datetime`

Legacy converters are adapted internally to renderer behavior, allowing incremental migration.

## Migration notes

- New code should prefer `LocaleRenderer` implementations.
- Existing converter-based code can remain in place and migrate gradually.
- Keep wrapper usage (`wrapped_date`, `wrapped_datetime`) unchanged at call sites.
