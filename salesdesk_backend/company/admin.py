from django.contrib import admin

from .models import Company, CompanyEntry

admin.site.register(Company)
admin.site.register(CompanyEntry)
