# Value Formatting

`LocaleValueFormatter` controls how wrapped placeholder values are transformed before template rendering.

## Two-stage temporal pipeline

Temporal formatting uses two explicit stages.

1) Timezone normalization (`datetime` values only)
2) Locale rendering to final string (`date` and `datetime`)

This separation keeps behavior predictable and allows custom locale-specific output strategies.

## Timezone normalization

For `datetime` values, target timezone resolution order is:

1. `locale_timezones[locale]`
2. `default_timezone`
3. UTC

### Naive vs aware `datetime`

Aware datetimes (`tzinfo` set):
- normalized with `astimezone(resolved_timezone)`

Naive datetimes (`tzinfo=None`):
- if `naive_input_timezone` is not set, values are left unchanged
- if `naive_input_timezone` is set, values are first interpreted in that timezone, then normalized to resolved timezone

## Renderer system

Renderer resolution order is:

1. locale renderer from `renderers[locale]`
2. `default_renderer`
3. built-in `StrftimeRenderer`

Renderer contract:

```python
from datetime import date, datetime
from localization import LocaleRenderer

class MyRenderer(LocaleRenderer):
    def render_date(self, value: date, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d")

    def render_datetime(self, value: datetime, *, locale: str, pattern: str | None = None) -> str:
        return value.strftime(pattern or "%Y/%m/%d %H:%M:%S")
```

## Wrapped values

Only explicit wrappers are specially formatted inside `i18n.msg(...)` context.

### `wrapped_date(...)`

```python
from datetime import date
from localization import wrapped_date

value = wrapped_date(date(2026, 4, 17))
```

### `wrapped_datetime(...)`

```python
from datetime import UTC, datetime
from localization import wrapped_datetime

value = wrapped_datetime(datetime(2026, 4, 17, 8, 45, tzinfo=UTC))
```

### `grouped_number(...)`

```python
from localization import grouped_number

value = grouped_number("1234567")  # -> 1,234,567
```

### `enum_ref(...)`

```python
from enum import Enum
from localization import enum_ref

class OrderStatus(Enum):
    PENDING = "pending"

value = enum_ref("order_status", OrderStatus.PENDING)
```

## Mixed placeholder example

```python
from datetime import UTC, date, datetime
from localization import enum_ref, grouped_number, wrapped_date, wrapped_datetime

print(i18n.msg(
    "user.report",
    locale="fa",
    date=wrapped_date(date(2026, 4, 17)),
    dt=wrapped_datetime(datetime(2026, 4, 17, 8, 45, 0, tzinfo=UTC)),
    amount=grouped_number("1234567"),
    status=enum_ref("order_status", "pending"),
    raw_date=date(2026, 4, 17),  # raw values stay raw
))
```

Unwrapped values are passed through normal Python formatting unchanged.
