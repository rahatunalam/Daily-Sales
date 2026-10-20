from decimal import Decimal

from django.db import transaction as db_tx
from rest_framework import serializers

from shopsettings.models import MfsAccount

from .models import Customer, Method, Transaction
from .services import remaining_due


class CustomerSerializer(serializers.ModelSerializer):
    due_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    received_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "due_total", "received_total", "remaining", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the customer name.")
        qs = Customer.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A customer with this name already exists.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 6:
            raise serializers.ValidationError("Enter a valid phone number.")
        qs = Customer.objects.filter(phone_digits=digits)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    wallet_name = serializers.CharField(source="wallet.name", read_only=True, default=None)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    wallet = serializers.PrimaryKeyRelatedField(queryset=MfsAccount.objects.all(), required=False, allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))

    class Meta:
        model = Transaction
        fields = [
            "id", "occurred_at", "method", "wallet", "wallet_name",
            "customer", "customer_name", "amount",
        ]
        read_only_fields = ["id", "occurred_at"]

    def validate(self, attrs):
        method = attrs["method"]
        wallet = attrs.get("wallet")
        customer = attrs.get("customer")
        if method == Method.MFS and wallet is None:
            raise serializers.ValidationError({"wallet": "Pick the wallet (bKash, Nagad...)."})
        if method != Method.MFS:
            attrs["wallet"] = None
        if method in (Method.DUE, Method.DUE_RECEIVED) and customer is None:
            raise serializers.ValidationError({"customer": "Search and pick the customer."})  # BR-02, BR-03
        if method in (Method.CASH, Method.MFS, Method.CARD):
            attrs["customer"] = None
        return attrs

    def create(self, validated):
        user = self.context["request"].user
        with db_tx.atomic():
            customer = validated.get("customer")
            if validated["method"] == Method.DUE_RECEIVED:
                # Lock the customer row so two receipts cannot overpay the same due (BR-03).
                customer = Customer.objects.select_for_update().get(pk=customer.pk)
                owed = remaining_due(customer)
                if validated["amount"] > owed:
                    raise serializers.ValidationError({"amount": f"That is more than the {owed} due."})
            return Transaction.objects.create(created_by=user, **validated)


class ReceiveSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
