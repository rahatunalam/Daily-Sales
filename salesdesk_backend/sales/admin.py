from django.contrib import admin

from .models import Customer, DailyOpening, Transaction

admin.site.register(Customer)
admin.site.register(Transaction)
admin.site.register(DailyOpening)
