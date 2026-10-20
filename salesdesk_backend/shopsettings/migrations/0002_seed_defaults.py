from decimal import Decimal

from django.db import migrations

WALLETS = ["bKash", "Nagad"]
DENOMINATIONS = ["1000", "500", "200", "100", "50", "20", "10"]


def seed(apps, schema_editor):
    Mfs = apps.get_model("shopsettings", "MfsAccount")
    Den = apps.get_model("shopsettings", "Denomination")
    for name in WALLETS:
        Mfs.objects.get_or_create(name=name)
    for v in DENOMINATIONS:
        Den.objects.get_or_create(value=Decimal(v))


class Migration(migrations.Migration):
    dependencies = [("shopsettings", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
