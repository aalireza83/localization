# Value Formatting

`LocaleValueFormatter` handles wrapped placeholder values and provides explicit, predictable temporal behavior.

## Two-stage temporal pipeline

Temporal wrapped values are processed in two stages.

1. **Timezone normalization** (`datetime` values)
2. **String rendering** (`date` and `datetime` values)

## Stage 1: timezone normalization

Timezone resolution order:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Aware datetimes

Aware values are normalized using `astimezone(resolved_timezone)`.

### Naive datetimes

One explicit rule is used:

- If `naive_input_timezone` is not set, naive datetimes are left unchanged.
- If `naive_input_timezone` is set, naive values are first interpreted in that timezone and then normalized to the resolved target timezone.

## Stage 2: renderer system

Renderer resolution order:

1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

This makes locale formatting deterministic and easy to reason about.

## Renderer contract

Implement `LocaleRenderer` for locale-specific rendering output.

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

## Wrapper helpers

Only wrapped values are specially processed in placeholder formatting:

- `wrapped_date(...)`
- `wrapped_datetime(...)`
- `grouped_number(...)`
- `enum_ref(...)`

Unwrapped values are passed through Python formatting unchanged.

### Wrapped `date`

```python
from datetime import date
from localization import wrapped_date

value = wrapped_date(date(2026, 4, 17))
```

### Wrapped `datetime`

```python
from datetime import UTC, datetime
from localization import wrapped_datetime

value = wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC))
```

### Mixed placeholders (wrapped + raw)

```python
from datetime import UTC, date, datetime
from localization import grouped_number, wrapped_date, wrapped_datetime

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    raw_date=date(2026, 4, 17),  # remains raw, not auto-formatted
))
```

## Configuration examples

### Default timezone + default renderer only

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

### Fallback to default renderer

```python
formatter = LocaleValueFormatter(
    default_now=lambda: datetime.now(),
    default_renderer=PrefixRenderer(),
)
```
