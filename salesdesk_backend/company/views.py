from django.db import transaction as db_tx
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsOwnerOrManager

from .models import Company, CompanyEntry
from .serializers import BillSerializer, CompanySerializer, PaySerializer
from .services import ZERO, company_due, with_balances


class CompanyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Company Payment: company list, details table (bill, paid, due), add company."""

    serializer_class = CompanySerializer
    permission_classes = [IsOwnerOrManager]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = with_balances(Company.objects.all())
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(name__icontains=search)  # "Search By company"
        return qs

    @extend_schema(parameters=[OpenApiParameter("search", str, description="part of a company name")])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = s.save()
        return Response(self.get_serializer(self.get_queryset().get(pk=obj.pk)).data, status=201)

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """The 'Total due remaining' card: sum of the due of every company."""
        agg = CompanyEntry.objects.aggregate(
            b=Coalesce(Sum("bill_amount"), Value(ZERO)), p=Coalesce(Sum("paid_amount"), Value(ZERO))
        )
        return Response({"total_bill": agg["b"], "total_paid": agg["p"], "total_due": agg["b"] - agg["p"]})

    @extend_schema(request=PaySerializer, responses=BillSerializer)
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Pay part of a company's due later. Cannot exceed the due (BR-09); reduces the closing balance (BR-10)."""
        s = PaySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with db_tx.atomic():
            company = Company.objects.select_for_update().get(pk=self.get_object().pk)
            due = company_due(company)
            if s.validated_data["amount"] > due:
                return Response({"detail": f"That is more than the {due} due."}, status=400)
            entry = CompanyEntry.objects.create(
                company=company, bill_amount=ZERO, paid_amount=s.validated_data["amount"], created_by=request.user
            )
        return Response(BillSerializer(entry).data, status=201)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """View: company name, Remaining Due and every bill/payment (oldest first) with a running remaining."""
        company = self.get_object()
        running = ZERO
        rows = []
        for e in company.entries.order_by("occurred_at", "id"):
            running += e.bill_amount - e.paid_amount
            rows.append(
                {"date": e.occurred_at, "bill_amount": e.bill_amount, "paid_amount": e.paid_amount, "remaining": running}
            )
        return Response({"company": {"id": company.pk, "name": company.name}, "remaining_due": running, "rows": rows})


class CompanyEntryViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Bill Amount page: record a bill and what was paid now."""

    serializer_class = BillSerializer
    permission_classes = [IsOwnerOrManager]

    def get_queryset(self):
        qs = CompanyEntry.objects.select_related("company")
        p = self.request.query_params
        if p.get("company"):
            qs = qs.filter(company_id=p["company"])
        if p.get("from"):
            qs = qs.filter(occurred_at__date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(occurred_at__date__lte=p["to"])
        return qs
