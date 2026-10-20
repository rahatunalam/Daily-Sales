from decimal import Decimal

from rest_framework import serializers


class OpeningSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))


class CountSerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=0)


class CloseDaySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    counts = CountSerializer(many=True)
