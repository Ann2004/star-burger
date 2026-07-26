from django.db import models
from django.utils import timezone


class AddressCoordinates(models.Model):
    address = models.CharField(
        'адрес',
        max_length=200,
        unique=True,
        db_index=True,
    )
    latitude = models.FloatField(
        'широта',
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        'долгота',
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(
        'дата обновления',
        auto_now=True,
    )
    
    class Meta:
        verbose_name = 'координаты адреса'
        verbose_name_plural = 'координаты адресов'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.address} - ({self.latitude}, {self.longitude})"
    
    def __str__(self):
        if self.latitude is not None and self.longitude is not None:
            return f"{self.address} - ({self.latitude}, {self.longitude})"
        return f"{self.address} - (не найдены)"
