from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Company(models.Model):
    """A supplier the shop buys from."""

    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"
        constraints = [models.UniqueConstraint(Lower("name"), name="uniq_company_name_ci")]

    def __str__(self):
        return self.name


class CompanyEntry(models.Model):
    """A bill (bill_amount) and/or a payment (paid_amount). A payment-only line has bill_amount 0 (BR-09)."""

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="entries")
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    bill_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-occurred_at", "-id"]
        verbose_name_plural = "company entries"
        constraints = [
            models.CheckConstraint(condition=models.Q(bill_amount__gte=0), name="ce_bill_non_negative"),
            models.CheckConstraint(condition=models.Q(paid_amount__gte=0), name="ce_paid_non_negative"),
            models.CheckConstraint(
                condition=models.Q(bill_amount__gt=0) | models.Q(paid_amount__gt=0), name="ce_has_amount"
            ),
        ]
