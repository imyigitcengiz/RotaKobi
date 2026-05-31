from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


@require_GET
def healthz(request):
    """Docker / Traefik sağlık kontrolü — auth yok, DB yok."""
    return HttpResponse('ok', content_type='text/plain')


class ContactHubView(TemplateView):
    template_name = 'crm/index.html'

    def get_context_data(self, **kwargs):
        from customers.customer_overview import build_rehber_hub_stats

        context = super().get_context_data(**kwargs)
        context.update(build_rehber_hub_stats())
        return context


class CrmHubView(ContactHubView):
    """Geriye dönük uyumluluk."""


class OrtakHubView(CrmHubView):
    """Geriye dönük uyumluluk."""
