from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Method

ZERO = Decimal("0.00")
_MONEY = DecimalField(max_digits=14, decimal_places=2)


def with_balances(qs):
    """Annotate customers with due_total, received_total and remaining (BR-05)."""
    qs = qs.annotate(
        due_total=Coalesce(
            Sum("transactions__amount", filter=Q(transactions__method=Method.DUE)), Value(ZERO), output_field=_MONEY
        ),
        received_total=Coalesce(
            Sum("transactions__amount", filter=Q(transactions__method=Method.DUE_RECEIVED)),
            Value(ZERO),
            output_field=_MONEY,
        ),
    )
    return qs.annotate(
        remaining=ExpressionWrapper(F("due_total") - F("received_total"), output_field=_MONEY)
    ).order_by("name")


def search_customers(qs, text):
    """Search by part of a name or part of a phone number."""
    text = (text or "").strip()
    if not text:
        return qs
    digits = "".join(ch for ch in text if ch.isdigit())
    cond = Q(name__icontains=text)
    if digits:
        cond |= Q(phone_digits__contains=digits)
    return qs.filter(cond)


def remaining_due(customer):
    agg = customer.transactions.aggregate(
        due=Coalesce(Sum("amount", filter=Q(method=Method.DUE)), Value(ZERO), output_field=_MONEY),
        got=Coalesce(Sum("amount", filter=Q(method=Method.DUE_RECEIVED)), Value(ZERO), output_field=_MONEY),
    )
    return agg["due"] - agg["got"]
