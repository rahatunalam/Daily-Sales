from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.db.models import DecimalField, Value
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Customer, Method, Transaction
from .serializers import CustomerSerializer, ReceiveSerializer, TransactionSerializer
from .services import ZERO, remaining_due, search_customers, with_balances


def _truthy(v):
    return str(v).lower() in ("1", "true", "yes")


class TransactionViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Daily Sales entries (Cash, MFS, Card, Due, Due received, Refund). Ledger lines are never edited."""

    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.select_related("wallet", "customer")
        p = self.request.query_params
        if p.get("date"):
            qs = qs.filter(occurred_at__date=p["date"])
        if p.get("from"):
            qs = qs.filter(occurred_at__date__gte=p["from"])
        if p.get("to"):
            qs = qs.filter(occurred_at__date__lte=p["to"])
        if p.get("method"):
            qs = qs.filter(method=p["method"].upper())
        if p.get("customer"):
            qs = qs.filter(customer_id=p["customer"])
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("date", str, description="YYYY-MM-DD (shop time zone)"),
            OpenApiParameter("from", str), OpenApiParameter("to", str),
            OpenApiParameter("method", str), OpenApiParameter("customer", int),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CustomerViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Customers and their dues (Due screen, customer search, Add Customer)."""

    serializer_class = CustomerSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = with_balances(Customer.objects.all())
        qs = search_customers(qs, self.request.query_params.get("search"))
        if _truthy(self.request.query_params.get("has_due")):
            qs = qs.filter(remaining__gt=0)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="part of a name or phone number"),
            OpenApiParameter("has_due", bool, description="only customers who still owe money"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = s.save()
        data = self.get_serializer(self.get_queryset().get(pk=obj.pk)).data
        return Response(data, status=201)

    @extend_schema(request=ReceiveSerializer, responses=TransactionSerializer)
    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Pay (receive) money against a customer's due. Cannot exceed the remaining due (BR-03)."""
        customer = self.get_object()
        s = ReceiveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tx = TransactionSerializer(
            data={"method": Method.DUE_RECEIVED, "customer": customer.pk, "amount": s.validated_data["amount"]},
            context={"request": request},
        )
        tx.is_valid(raise_exception=True)
        tx.save()
        return Response(tx.data, status=201)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Due history: date, due amount, due paid and the running remaining."""
        customer = self.get_object()
        running = ZERO
        rows = []
        qs = customer.transactions.filter(method__in=[Method.DUE, Method.DUE_RECEIVED]).order_by("occurred_at", "id")
        for t in qs:
            due = t.amount if t.method == Method.DUE else ZERO
            paid = t.amount if t.method == Method.DUE_RECEIVED else ZERO
            running += due - paid
            rows.append({"date": t.occurred_at, "due": due, "paid": paid, "remaining": running})
        rows.reverse()  # newest first
        return Response(
            {"customer": {"id": customer.pk, "name": customer.name, "phone": customer.phone},
             "remaining": remaining_due(customer), "rows": rows}
        )

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"], url_path="due-summary")
    def due_summary(self, request):
        """Cards on the Due screen: Due received and Total due remaining."""
        agg = Transaction.objects.aggregate(
            due=Coalesce(Sum("amount", filter=Q(method=Method.DUE)), Value(ZERO),
                         output_field=DecimalField(max_digits=14, decimal_places=2)),
            got=Coalesce(Sum("amount", filter=Q(method=Method.DUE_RECEIVED)), Value(ZERO),
                         output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        return Response({"total_received": agg["got"], "total_remaining": agg["due"] - agg["got"]})
