from django.contrib import admin
from .models import MfsAccount, Denomination, Customer, Transaction, Company, CompanyEntry

# Register your models here.
admin.site.register([MfsAccount, Denomination, Customer, Transaction, Company, CompanyEntry])

