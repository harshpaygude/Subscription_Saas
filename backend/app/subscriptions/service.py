from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Iterable

MONTHS = {"monthly": Decimal("1"), "annual": Decimal("12"), "quarterly": Decimal("3"), "weekly": Decimal("12") / Decimal("52")}

def normalize_monthly(amount: Decimal | None, interval: str) -> Decimal | None:
    if amount is None or interval not in MONTHS: return None
    if interval == "weekly": return (amount * Decimal("52") / Decimal("12")).quantize(Decimal("0.000001"))
    return (amount / MONTHS[interval]).quantize(Decimal("0.000001"))

def month_start(value: date) -> date: return value.replace(day=1)

def month_end(value: date) -> date:
    return value.replace(day=monthrange(value.year, value.month)[1])

def upcoming(subscription, start: date, end: date) -> bool:
    return subscription.status == "ACTIVE" and subscription.next_renewal_date is not None and start <= subscription.next_renewal_date <= end

def aggregate_subscriptions(subscriptions: Iterable) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for item in subscriptions:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is not None: result[item.currency] = result.get(item.currency, Decimal("0")) + normalized
    return result
