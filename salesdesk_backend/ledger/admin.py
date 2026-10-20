from django.contrib import admin

from .models import DayClosing, DayClosingCount

admin.site.register(DayClosing)
admin.site.register(DayClosingCount)
