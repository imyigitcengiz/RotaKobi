from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from common.brand_scope import filter_by_brand
from common.decorators import permission_required
from django.utils.decorators import method_decorator

from restaurant.models import RestaurantCategory, RestaurantMenuItem, RestaurantTable


@method_decorator(permission_required('access.restaurant'), name='dispatch')
class RestaurantHubView(LoginRequiredMixin, TemplateView):
    template_name = 'restaurant/hub.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        brand = getattr(self.request, 'active_brand', None)
        ctx['category_count'] = (
            filter_by_brand(RestaurantCategory.objects.all(), self.request).count()
            if brand else 0
        )
        ctx['menu_item_count'] = (
            filter_by_brand(RestaurantMenuItem.objects.all(), self.request).count()
            if brand else 0
        )
        ctx['table_count'] = (
            filter_by_brand(RestaurantTable.objects.all(), self.request).count()
            if brand else 0
        )
        return ctx
