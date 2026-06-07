from django.urls import path

from restaurant.views import RestaurantHubView

urlpatterns = [
    path('', RestaurantHubView.as_view(), name='restaurant_hub'),
]
