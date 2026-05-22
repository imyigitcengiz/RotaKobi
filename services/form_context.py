from django.contrib.auth import get_user_model

from core_settings.catalog import build_options_catalog


def build_service_form_context(service=None):
    catalog = build_options_catalog()
    ctx = {
        'options_catalog': catalog,
        'users_for_assign': get_user_model().objects.filter(is_active=True).order_by('username'),
    }
    if service:
        ctx['initial_product_ids'] = list(service.products.values_list('id', flat=True))
        ctx['initial_service_type_ids'] = list(service.service_types.values_list('id', flat=True))
    else:
        ctx['initial_product_ids'] = []
        ctx['initial_service_type_ids'] = []
    return ctx
