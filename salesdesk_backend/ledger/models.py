from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class DayClosing(models.Model):
    """A closed day. Exists only after the counted cash matched the closing balance (BR-11)."""

    date = models.DateField(unique=True)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    counted_total = models.DecimalField(max_digits=14, decimal_places=2)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    closed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]


class DayClosingCount(models.Model):
    """Quantity counted per note/coin. The value is copied so later setting changes do not alter history."""

    closing = models.ForeignKey(DayClosing, on_delete=models.CASCADE, related_name="counts")
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["-value"]
        constraints = [models.UniqueConstraint(fields=["closing", "value"], name="uniq_closing_value")]
