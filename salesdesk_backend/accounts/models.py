from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    def create_user(self, name, password=None, **extra):
        if not name or not name.strip():
            raise ValueError("A user needs a name.")
        user = self.model(name=name.strip(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, name, password=None, **extra):
        extra.setdefault("role", User.Role.OWNER)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(name, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """A shop user. Sign-in is by name (not case sensitive) and password."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"

    name = models.CharField(max_length=80, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CASHIER)
    # Shown in the profile menu (for example "Sales Man").
    designation = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "name"
    objects = UserManager()

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="uniq_user_name_ci")]

    def save(self, *args, **kwargs):
        if not self.designation:
            self.designation = self.get_role_display()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
