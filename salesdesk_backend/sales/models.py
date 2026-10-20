from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=120, unique=True)
    phone = models.CharField(max_length=30)
    # Digits only, so "01700 000000" and "01700000000" are the same number (BR-12).
    phone_digits = models.CharField(max_length=30, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="uniq_customer_name_ci")]

    def save(self, *args, **kwargs):
        self.phone_digits = "".join(ch for ch in self.phone if ch.isdigit())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Method(models.TextChoices):
    CASH = "CASH", "Cash"
    MFS = "MFS", "MFS"
    CARD = "CARD", "Card"
    DUE = "DUE", "Due"
    DUE_RECEIVED = "DUE_RECEIVED", "Due received"
    REFUND = "REFUND", "Refund"


class Transaction(models.Model):
    """One line in the daily ledger. Lines are never edited or deleted."""

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(max_length=14, choices=Method.choices)
    wallet = models.ForeignKey(
        "shopsettings.MfsAccount", null=True, blank=True, on_delete=models.PROTECT, related_name="transactions"
    )
    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.PROTECT, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["occurred_at", "method"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="tx_amount_positive"),
            models.CheckConstraint(
                condition=~models.Q(method="DUE") | models.Q(customer__isnull=False),
                name="tx_due_needs_customer",
            ),
            models.CheckConstraint(
                condition=~models.Q(method="DUE_RECEIVED") | models.Q(customer__isnull=False),
                name="tx_due_received_needs_customer",
            ),
            models.CheckConstraint(
                condition=~models.Q(method="MFS") | models.Q(wallet__isnull=False),
                name="tx_mfs_needs_wallet",
            ),
        ]

    def __str__(self):
        return f"{self.method} {self.amount}"


class DailyOpening(models.Model):
    """Opening balance typed in Daily Sales; if missing, the previous closing is used."""

    date = models.DateField(unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    set_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-date"]
