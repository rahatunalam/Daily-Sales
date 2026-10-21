from django.db import models

# Create your models here.
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

# ---------- users ----------
class UserManager(BaseUserManager):
    def create_user(self, name, password=None, **extra):
        user = self.model(name=name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, name, password=None, **extra):
        extra.update(role='owner', is_staff=True, is_superuser=True)
        extra.setdefault('designation', 'Owner')
        return self.create_user(name, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [('owner', 'Owner'), ('manager', 'Manager'), ('cashier', 'Cashier')]
    name = models.CharField(max_length=80, unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default='cashier')
    designation = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'name'
    objects = UserManager()

    def __str__(self):
        return self.name

# ---------- settings data ----------
class MfsAccount(models.Model):
    name = models.CharField(max_length=60, unique=True)
    account = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return self.name

class Denomination(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2, unique=True)

    class Meta:
        ordering = ['-value']

# ---------- customers and transactions ----------
class Customer(models.Model):
    name = models.CharField(max_length=120, unique=True)
    phone = models.CharField(max_length=30)
    phone_digits = models.CharField(max_length=30, unique=True, editable=False)
    due_ledger = models.BooleanField(default=False)
    wholesale_ledger = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.phone_digits = ''.join(ch for ch in self.phone if ch.isdigit())
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    METHODS = [('CASH', 'Cash'), ('MFS', 'MFS'), ('CARD', 'Card'), ('REFUND', 'Refund'),
               ('DUE', 'Due'), ('DUE_RECEIVED', 'Due received'),
               ('WHOLESALE', 'Whole Sale'), ('WHOLESALE_RECEIVED', 'Whole Sale received')]
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(max_length=20, choices=METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    wallet = models.ForeignKey(MfsAccount, null=True, blank=True, on_delete=models.SET_NULL)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='transactions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-occurred_at', '-id']

# ---------- daily balance ----------
class OpeningBalance(models.Model):
    date = models.DateField(unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class DayClosing(models.Model):
    date = models.DateField(unique=True)
    counted_total = models.DecimalField(max_digits=12, decimal_places=2)
    counts = models.JSONField(default=dict)            # {"1000.00": 3, "500.00": 2}
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    closed_at = models.DateTimeField(auto_now_add=True)

# ---------- company payment ----------
class Company(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class CompanyEntry(models.Model):
    """One row per bill or payment. A payment is an entry with bill_amount = 0."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='entries')
    bill_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']