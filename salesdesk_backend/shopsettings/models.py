from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class MfsAccount(models.Model):
    """A mobile wallet such as bKash or Nagad (Settings > Add MFS)."""

    name = models.CharField(max_length=60, unique=True)
    account = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="uniq_mfs_name_ci")]

    def __str__(self):
        return self.name


class Denomination(models.Model):
    """A note or coin value used in Day Closing (decimals allowed, e.g. 0.25)."""

    value = models.DecimalField(
        max_digits=10, decimal_places=2, unique=True, validators=[MinValueValidator(Decimal("0.01"))]
    )

    class Meta:
        ordering = ["-value"]

    def __str__(self):
        return str(self.value)
