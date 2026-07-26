from django.contrib import admin

from .models import AddressCoordinates


@admin.register(AddressCoordinates)
class AddressCoordinatesAdmin(admin.ModelAdmin):
    list_display = ('address', 'latitude', 'longitude', 'updated_at')
    search_fields = ('address',)
    list_filter = ('updated_at',)
    readonly_fields = ('updated_at',)
