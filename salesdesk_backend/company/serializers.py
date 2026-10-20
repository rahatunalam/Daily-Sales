from decimal import Decimal

from django.db import transaction as db_tx
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Company, CompanyEntry
from .services import company_due


class CompanySerializer(serializers.ModelSerializer):
    bill_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    paid_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Company
        fields = ["id", "name", "bill_total", "paid_total", "due", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the company name.")
        qs = Company.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This company already exists.")
        return value


class BillSerializer(serializers.ModelSerializer):
    """Bill Amount page: company + bill amount + paid amount (Due amount = bill - paid)."""

    company_name = serializers.CharField(source="company.name", read_only=True)
    bill_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    paid_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )
    due_amount = serializers.SerializerMethodField()

    class Meta:
        model = CompanyEntry
        fields = ["id", "company", "company_name", "occurred_at", "bill_amount", "paid_amount", "due_amount"]
        read_only_fields = ["id", "occurred_at"]

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_due_amount(self, obj):
        return obj.bill_amount - obj.paid_amount

    def create(self, validated):
        with db_tx.atomic():
            company = Company.objects.select_for_update().get(pk=validated["company"].pk)
            limit = validated["bill_amount"] + company_due(company)
            if validated["paid_amount"] > limit:
                raise serializers.ValidationError(
                    {"paid_amount": f"Paid amount is more than the total due of {limit}."}  # BR-09
                )
            return CompanyEntry.objects.create(created_by=self.context["request"].user, **validated)


class PaySerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
