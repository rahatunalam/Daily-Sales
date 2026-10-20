from django.core.management.base import BaseCommand

from accounts.models import User
from company.models import Company
from sales.models import Customer


class Command(BaseCommand):
    help = "Create demo users, a customer and companies (safe to run again)."

    def handle(self, *args, **opts):
        demo = [
            ("OWNER", "owner1234", User.Role.OWNER, "Owner"),
            ("RAHAT", "1234", User.Role.CASHIER, "Sales Man"),
        ]
        for name, pw, role, desig in demo:
            if not User.objects.filter(name__iexact=name).exists():
                User.objects.create_user(name, pw, role=role, designation=desig)
                self.stdout.write(f"created user {name} / {pw}")
        Customer.objects.get_or_create(name="Rahat", defaults={"phone": "01740 512345"})
        for c in ("Square Pharma", "Beximco"):
            Company.objects.get_or_create(name=c)
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
