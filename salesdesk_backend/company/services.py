from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce

ZERO = Decimal("0.00")
_MONEY = DecimalField(max_digits=14, decimal_places=2)


def with_balances(qs):
    """Annotate companies with bill_total, paid_total and due (BR-09)."""
    qs = qs.annotate(
        bill_total=Coalesce(Sum("entries__bill_amount"), Value(ZERO), output_field=_MONEY),
        paid_total=Coalesce(Sum("entries__paid_amount"), Value(ZERO), output_field=_MONEY),
    )
    return qs.annotate(due=ExpressionWrapper(F("bill_total") - F("paid_total"), output_field=_MONEY)).order_by("name")


def company_due(company):
    agg = company.entries.aggregate(
        b=Coalesce(Sum("bill_amount"), Value(ZERO), output_field=_MONEY),
        p=Coalesce(Sum("paid_amount"), Value(ZERO), output_field=_MONEY),
    )
    return agg["b"] - agg["p"]
