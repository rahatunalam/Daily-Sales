"""Balance rules from the BRD (section 4).

Closing = Opening + Cash + MFS + Card + Due received - Refund - Company payments   (BR-06..BR-10)
Due sales never touch the closing balance; they only raise the customer's due (BR-02).
"""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from company.models import CompanyEntry
from sales.models import DailyOpening, Method, Transaction
from shopsettings.models import MfsAccount

ZERO = Decimal("0.00")


def figures(start=None, end=None, include=()):
    """Return one dict per day, oldest first, with balances carried from day to day.

    Days with no activity are skipped, except today and any date in `include`.
    Remaining due and company remaining bill are running totals at the end of each day.
    """
    by_day = defaultdict(lambda: defaultdict(lambda: ZERO))
    for row in (
        Transaction.objects.annotate(d=TruncDate("occurred_at")).values("d", "method").annotate(total=Sum("amount"))
    ):
        by_day[row["d"]][row["method"]] += row["total"]

    co_day = {}
    for row in (
        CompanyEntry.objects.annotate(d=TruncDate("occurred_at"))
        .values("d")
        .annotate(bill=Sum("bill_amount"), paid=Sum("paid_amount"))
    ):
        co_day[row["d"]] = (row["bill"], row["paid"])

    openings = dict(DailyOpening.objects.values_list("date", "amount"))
    dates = set(by_day) | set(co_day) | set(openings) | {timezone.localdate()} | set(include)

    out, balance, outstanding, co_outstanding = [], ZERO, ZERO, ZERO
    for d in sorted(dates):
        m = by_day.get(d, {})
        cash, mfs, card = m.get(Method.CASH, ZERO), m.get(Method.MFS, ZERO), m.get(Method.CARD, ZERO)
        due, got, refund = m.get(Method.DUE, ZERO), m.get(Method.DUE_RECEIVED, ZERO), m.get(Method.REFUND, ZERO)
        bill, paid = co_day.get(d, (ZERO, ZERO))
        opening = openings.get(d, balance)
        closing = opening + cash + mfs + card + got - refund - paid
        balance = closing
        outstanding += due - got
        co_outstanding += bill - paid
        out.append(
            {
                "date": d, "opening": opening, "cash": cash, "mfs": mfs, "card": card, "due": due,
                "due_received": got, "refund": refund, "company_bill": bill, "company_paid": paid,
                "closing": closing, "remaining_due": outstanding, "company_remaining": co_outstanding,
            }
        )
    return [r for r in out if (start is None or r["date"] >= start) and (end is None or r["date"] <= end)]


def figure_for(date):
    rows = figures(start=date, end=date, include=[date])
    return rows[0]


def summary_for(date):
    """Daily Sales summary card: rows + the two totals."""
    f = figure_for(date)
    wallet_totals = {
        r["wallet__name"]: r["total"]
        for r in Transaction.objects.filter(occurred_at__date=date, method=Method.MFS)
        .values("wallet__name")
        .annotate(total=Sum("amount"))
    }
    rows = [{"label": "Cash", "amount": f["cash"]}]
    rows += [{"label": w.name, "amount": wallet_totals.get(w.name, ZERO)} for w in MfsAccount.objects.all()]
    rows += [
        {"label": "Card", "amount": f["card"]},
        {"label": "Due", "amount": f["due"]},
        {"label": "Due received", "amount": f["due_received"]},
        {"label": "Refund", "amount": f["refund"]},
    ]
    without_due = f["cash"] + f["mfs"] + f["card"] + f["due_received"] - f["refund"]  # BR-06
    return {
        "date": date,
        "rows": rows,
        "total_sales_without_due": without_due,
        "total_sales_with_due": without_due + f["due"],  # BR-07
        "opening_balance": f["opening"],
        "closing_balance": f["closing"],
    }
