# Migration Guide

This document summarizes backward compatibility and migration notes for formatter behavior.

## What changed

The old formatter approach centered around converters that returned temporal Python values:

- `convert_date(...) -> date`
- `convert_datetime(...) -> datetime`

The newer design separates concerns into:

1. timezone normalization
2. final rendering to `str`

## Why this changed

Locale-specific calendar output (for example Persian/Jalali rendering) often needs direct string output.
A render-to-string contract is more flexible than requiring only `date`/`datetime` converter outputs.

## Backward compatibility

`LocaleValueFormatter` still supports legacy converter styles:

- `converters={...}` and `default_converter=...`
- callable converters (`Callable[[date | datetime], date | datetime]`)
- object-based converters with `convert_date` / `convert_datetime`

These are adapted internally to the renderer system via converter adapters.

## Migration strategy

1. Keep existing converters in place; they continue to work.
2. Move locale-specific output logic into `LocaleRenderer` implementations.
3. Configure via `renderers={...}` / `default_renderer=...`.
4. Remove legacy converter usage when ready.

## Before (legacy style)

```python
formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    converters={"fa": some_legacy_converter},
)
```

## After (renderer style)

```python
formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    renderers={"fa": some_renderer},
)
```

Both can coexist during incremental migration.
