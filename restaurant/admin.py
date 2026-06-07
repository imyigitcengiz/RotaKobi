from django.contrib import admin

from restaurant.models import RestaurantCategory, RestaurantMenuItem, RestaurantTable


@admin.register(RestaurantCategory)
class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'sort_order', 'is_active')
    list_filter = ('brand', 'is_active')


@admin.register(RestaurantMenuItem)
class RestaurantMenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'is_available')
    list_filter = ('brand', 'is_available')


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'branch', 'capacity', 'status')
    list_filter = ('brand', 'status')
