from django.contrib import admin

from .models import Denomination, MfsAccount

admin.site.register(MfsAccount)
admin.site.register(Denomination)
