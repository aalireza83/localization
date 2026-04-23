# Value Formatting

`LocaleValueFormatter` handles wrapper-based value formatting used in placeholders.

## Two-stage temporal pipeline

Temporal formatting is explicit and deterministic.

### Stage 1: timezone normalization (`datetime`)

Resolution order:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Stage 2: rendering (`date` and `datetime`)

Resolution order:

1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

This separation keeps timezone behavior independent from final display style.

## Timezone normalization behavior

### Aware datetime input

Aware values are normalized with:

- `value.astimezone(resolved_timezone)`

### Naive datetime input

- If `naive_input_timezone` is not set: naive values are left unchanged.
- If `naive_input_timezone` is set: naive values are interpreted in that timezone, then normalized to the resolved target timezone.

## Renderer system

Renderers implement the `LocaleRenderer` contract:

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

A renderer returns final strings, which makes non-Gregorian output (for example Jalali/Shamsi formatting) straightforward.

## Wrapped values

Only wrapped values receive special formatting behavior.

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Unwrapped values are passed through regular Python string formatting behavior.

Example:

```python
from datetime import UTC, date, datetime
from localization import grouped_number, wrapped_date, wrapped_datetime

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),
))
```
