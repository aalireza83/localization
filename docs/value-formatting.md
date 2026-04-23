# Value Formatting

`LocaleValueFormatter` formats wrapped placeholder values with explicit, predictable rules.

## Wrapper model

Special formatting is applied only to wrapped values:

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Unwrapped values are passed through Python formatting unchanged.

## Two-stage temporal pipeline

Temporal formatting for wrapped date/datetime values is split into two stages.

### Stage 1: timezone normalization (`datetime` values)

Resolution order:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

This stage normalizes datetime values to a target timezone before string rendering.

### Stage 2: string rendering (`date` and `datetime`)

Renderer resolution order:

1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer` fallback

This ensures there is always a deterministic string output path.

## Naive vs aware datetimes

### Aware datetimes

Aware values are normalized with `astimezone(resolved_timezone)`.

### Naive datetimes

Naive handling is explicit:

- If `naive_input_timezone` is **not** set, naive datetimes are left unchanged.
- If `naive_input_timezone` **is** set, naive values are interpreted in that timezone and then normalized to the resolved target timezone.

## Renderer contract

Use `LocaleRenderer` for locale-specific output:

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

A renderer returns the final string, which makes custom calendar output (for example Jalali/Shamsi rendering) straightforward.

## Configuration examples

### Default timezone + default renderer fallback

```python
from datetime import UTC, datetime
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
)

print(formatter.format_datetime(datetime(2026, 4, 15, 8, 30, tzinfo=UTC), locale="en"))
```

### Locale-specific timezone

```python
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from localization import LocaleValueFormatter

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(tz=UTC),
    locale_timezones={"fa": ZoneInfo("Asia/Tehran")},
    default_timezone=ZoneInfo("UTC"),
)
```

### Locale-specific renderer

```python
from datetime import date, datetime
from localization import LocaleRenderer, LocaleValueFormatter

class PrefixRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return f"{locale}:{value.strftime(pattern or '%Y/%m/%d')}"

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return f"{locale}:{value.strftime(pattern or '%Y/%m/%d %H:%M:%S')}"

formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    renderers={"fa": PrefixRenderer()},
)
```

### Wrapped values in placeholders

```python
from datetime import UTC, date, datetime
from localization import grouped_number, wrapped_date, wrapped_datetime

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),  # remains raw
))
```
