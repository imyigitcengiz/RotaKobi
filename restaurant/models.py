"""Restoran modülü — BiDoluPos'tan parça parça taşınacak modeller.

Faz 1: menü, masa. Faz 2: sipariş, mutfak. Bkz. docs/RESTORAN_MIGRATION.md
"""

from django.db import models


class RestaurantCategory(models.Model):
    brand = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.CASCADE,
        related_name='restaurant_categories',
    )
    name = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Menü kategorisi'
        verbose_name_plural = 'Menü kategorileri'
        ordering = ('sort_order', 'name')
        unique_together = (('brand', 'name'),)

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    brand = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.CASCADE,
        related_name='restaurant_menu_items',
    )
    category = models.ForeignKey(
        RestaurantCategory,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Menü ürünü'
        verbose_name_plural = 'Menü ürünleri'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return self.name


class RestaurantTable(models.Model):
    STATUS_EMPTY = 'empty'
    STATUS_OCCUPIED = 'occupied'
    STATUS_BILL = 'bill_requested'
    STATUS_CHOICES = (
        (STATUS_EMPTY, 'Boş'),
        (STATUS_OCCUPIED, 'Dolu'),
        (STATUS_BILL, 'Hesap istendi'),
    )

    brand = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.CASCADE,
        related_name='restaurant_tables',
    )
    branch = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='restaurant_branch_tables',
        help_text='Bayi/franchise şubesi; boşsa merkez masası.',
    )
    name = models.CharField(max_length=50)
    capacity = models.PositiveSmallIntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_EMPTY)

    class Meta:
        verbose_name = 'Masa'
        verbose_name_plural = 'Masalar'
        unique_together = (('brand', 'branch', 'name'),)

    def __str__(self):
        return self.name
