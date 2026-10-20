import datetime

from django.db import transaction as db_tx
from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOwnerOrManager
from company.models import CompanyEntry
from sales.models import DailyOpening
from shopsettings.models import Denomination

from .models import DayClosing, DayClosingCount
from .serializers import CloseDaySerializer, OpeningSerializer
from .services import ZERO, figure_for, figures, summary_for


def _date_param(request, name="date"):
    raw = request.query_params.get(name)
    if not raw:
        return timezone.localdate()
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: "Use the YYYY-MM-DD format."})


class DailySummaryView(APIView):
    """Daily Sales summary: Cash, wallets, Card, Due, Due received, Refund and both totals."""

    @extend_schema(parameters=[OpenApiParameter("date", str)], responses=dict)
    def get(self, request):
        return Response(summary_for(_date_param(request)))


class OpeningBalanceView(APIView):
    """Opening balance for a day (Daily Sales header)."""

    @extend_schema(parameters=[OpenApiParameter("date", str)], responses=dict)
    def get(self, request):
        d = _date_param(request)
        return Response(
            {"date": d, "amount": figure_for(d)["opening"], "explicit": DailyOpening.objects.filter(date=d).exists()}
        )

    @extend_schema(request=OpeningSerializer, responses=dict)
    def put(self, request):
        s = OpeningSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data.get("date") or timezone.localdate()
        if DayClosing.objects.filter(date=d).exists():
            return Response({"detail": "This day is already closed."}, status=409)
        DailyOpening.objects.update_or_create(
            date=d, defaults={"amount": s.validated_data["amount"], "set_by": request.user}
        )
        return Response({"date": d, "amount": s.validated_data["amount"], "explicit": True})


class DayClosingView(APIView):
    """Day Closing: count cash by note/coin; the day closes only when the count equals the closing balance."""

    permission_classes = [IsOwnerOrManager]

    @extend_schema(parameters=[OpenApiParameter("date", str)], responses=dict)
    def get(self, request):
        d = _date_param(request)
        f = figure_for(d)
        closed = DayClosing.objects.filter(date=d).prefetch_related("counts").first()
        if closed:
            counts = [{"value": c.value, "quantity": c.quantity} for c in closed.counts.all()]
            total = closed.counted_total
        else:
            counts = [{"value": x.value, "quantity": 0} for x in Denomination.objects.all()]
            total = ZERO
        return Response(
            {
                "date": d, "opening_balance": f["opening"], "closing_balance": f["closing"],
                "counts": counts, "counted_total": total, "difference": total - f["closing"],
                "closed": closed is not None,
            }
        )

    @extend_schema(request=CloseDaySerializer, responses=dict)
    def post(self, request):
        s = CloseDaySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data.get("date") or timezone.localdate()
        known = {x.value for x in Denomination.objects.all()}
        total = ZERO
        clean = {}
        for c in s.validated_data["counts"]:
            if c["value"] not in known:
                return Response({"detail": f"{c['value']} is not a denomination in Money Setting."}, status=400)
            clean[c["value"]] = clean.get(c["value"], 0) + c["quantity"]
        for value, qty in clean.items():
            total += value * qty
        with db_tx.atomic():
            if DayClosing.objects.select_for_update().filter(date=d).exists():
                return Response({"detail": "This day is already closed."}, status=409)
            closing = figure_for(d)["closing"]
            diff = total - closing
            if diff != 0:  # BR-11
                word = "Over by" if diff > 0 else "Short by"
                return Response(
                    {
                        "detail": f"{word} {abs(diff)}. The total must match the closing balance.",
                        "counted_total": total, "closing_balance": closing, "difference": diff,
                    },
                    status=400,
                )
            rec = DayClosing.objects.create(date=d, closing_balance=closing, counted_total=total, closed_by=request.user)
            DayClosingCount.objects.bulk_create(
                [DayClosingCount(closing=rec, value=v, quantity=q) for v, q in clean.items() if q > 0]
            )
        return Response({"date": d, "closing_balance": closing, "counted_total": total, "closed": True}, status=201)


class DailyReportView(APIView):
    """Report: one row per active day, newest first. Use from/to or preset=today|yesterday|last7.

    Closing = opening + sales_received + due_receive - refund - company_paid. `due` is credit given, not cash.
    remaining_due and the company_* running figures stay in the payload for the Due and Company screens.
    """

    permission_classes = [IsOwnerOrManager]

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str), OpenApiParameter("to", str),
            OpenApiParameter("preset", str, enum=["today", "yesterday", "last7"]),
        ],
        responses=dict,
    )
    def get(self, request):
        today = timezone.localdate()
        preset = request.query_params.get("preset")
        if preset == "yesterday":
            start = end = today - datetime.timedelta(days=1)
        elif preset == "last7":
            start, end = today - datetime.timedelta(days=6), today
        elif request.query_params.get("from") or request.query_params.get("to"):
            start, end = _date_param(request, "from"), _date_param(request, "to")
        else:  # today
            start = end = today
        rows = [
            {
                "date": r["date"],
                "day": r["date"].strftime("%a"),
                "opening_balance": r["opening"],
                "sales_received": r["cash"] + r["mfs"] + r["card"],
                "due_receive": r["due_received"],
                "refund": r["refund"],
                "company_paid": r["company_paid"],
                "closing_balance": r["closing"],
                "due": r["due"],
                "remaining_due": r["remaining_due"],
                "company_bill_amount": r["company_bill"],
                "company_bill_paid": r["company_paid"],
                "company_remaining_bill": r["company_remaining"],
            }
            for r in reversed(figures(start=start, end=end, include=[today] if start <= today <= end else []))
        ]
        return Response({"from": start, "to": end, "rows": rows})


class ReportDetailView(APIView):
    """Report > Details modal for one date: the Sales and Due box and the Company Payment details table."""

    permission_classes = [IsOwnerOrManager]

    @extend_schema(parameters=[OpenApiParameter("date", str, required=True)], responses=dict)
    def get(self, request):
        if not request.query_params.get("date"):
            raise ValidationError({"date": "Pick a date (YYYY-MM-DD)."})
        d = _date_param(request)
        s = summary_for(d)
        companies = list(
            CompanyEntry.objects.filter(occurred_at__date=d, paid_amount__gt=0)
            .values("company_id", "company__name")
            .annotate(paid=Sum("paid_amount"))
            .order_by("company__name")
        )
        return Response(
            {
                "date": d,
                "day": d.strftime("%a"),
                "sales_and_due": {
                    # Refund is returned as a positive number; show it as a minus in the screen.
                    "rows": s["rows"],
                    "total_sales_with_due": s["total_sales_with_due"],
                    "total_sales_without_due": s["total_sales_without_due"],
                },
                "company_payments": [
                    {"company_id": c["company_id"], "company_name": c["company__name"], "paid_amount": c["paid"]}
                    for c in companies
                ],
                "company_paid_total": sum((c["paid"] for c in companies), ZERO),
            }
        )
