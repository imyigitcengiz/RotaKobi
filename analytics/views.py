from decimal import Decimal, InvalidOperation

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from services.models import ServiceRecord
from customers.models import Customer
from core_settings.models import SiteSettings, StatusOption, PriorityOption
from django.utils import timezone
from datetime import timedelta
import json
from django.http import JsonResponse
import logging

import openai
from django.views.decorators.http import require_POST

from common.decorators import json_auth_required, permission_required
from .service_report import build_service_dashboard_report

logger = logging.getLogger(__name__)

class PublicLandingView(TemplateView):
    """Herkese açık tanıtım sayfası — girişten önce."""

    template_name = 'landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from common.landing_content import (
            LANDING_VERTICAL_COPY,
            LANDING_PILLARS,
            LANDING_SERVICES_FEATURES,
            LANDING_MUHASEBE_FEATURES,
            LANDING_REHBER_FEATURES,
            LANDING_OUTREACH_FEATURES,
            LANDING_INTEGRATION_DETAILS,
            LANDING_PLATFORM_FEATURES,
            LANDING_SETTINGS_FEATURES,
            LANDING_SECTORS,
            LANDING_FLOW_SAHA,
            LANDING_FLOW_HIZMET,
            LANDING_DEPLOY_PLATFORMS,
            LANDING_AUDIENCE,
            build_landing_particle_groups,
        )
        from common.module_catalog import (
            MODULE_KIND_APP,
            MODULE_KIND_INTEGRATION,
            MODULE_KIND_ROADMAP,
            MODULE_STATUS_ACTIVE,
            MODULE_STATUS_ROADMAP,
            MODULES,
        )

        context = super().get_context_data(**kwargs)
        apps = [
            m for m in MODULES
            if m['kind'] == MODULE_KIND_APP
            and m['status'] == MODULE_STATUS_ACTIVE
            and m['slug'] != 'settings'
            and not m['slug'].startswith('agency_')
        ]
        integrations = [
            m for m in MODULES
            if m['kind'] == MODULE_KIND_INTEGRATION and m['status'] == MODULE_STATUS_ACTIVE
        ]
        roadmap = [
            m for m in MODULES
            if m['kind'] == MODULE_KIND_ROADMAP and m['status'] == MODULE_STATUS_ROADMAP
        ]
        apps.sort(key=lambda a: (a.get('sort', 99), a['name']))
        integrations.sort(key=lambda a: (a.get('sort', 99), a['name']))
        roadmap.sort(key=lambda a: (a.get('sort', 99), a['name']))
        context['landing_vertical_copy'] = LANDING_VERTICAL_COPY['kobi']
        context['landing_apps'] = apps
        context['landing_integrations'] = integrations
        context['landing_roadmap'] = roadmap
        context['landing_pillars'] = LANDING_PILLARS
        context['landing_services_features'] = LANDING_SERVICES_FEATURES
        context['landing_muhasebe_features'] = LANDING_MUHASEBE_FEATURES
        context['landing_rehber_features'] = LANDING_REHBER_FEATURES
        context['landing_outreach_features'] = LANDING_OUTREACH_FEATURES
        context['landing_integration_details'] = LANDING_INTEGRATION_DETAILS
        context['landing_platform_features'] = LANDING_PLATFORM_FEATURES
        context['landing_settings_features'] = LANDING_SETTINGS_FEATURES
        context['landing_sectors'] = LANDING_SECTORS
        context['landing_flow_saha'] = LANDING_FLOW_SAHA
        context['landing_flow_hizmet'] = LANDING_FLOW_HIZMET
        context['landing_particle_groups'] = build_landing_particle_groups()
        context['landing_deploy_platforms'] = LANDING_DEPLOY_PLATFORMS
        context['landing_audience'] = LANDING_AUDIENCE
        return context


class HomeView(TemplateView):
    """Giriş sonrası modül kısayolları."""

    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        from common.permissions import can_access_accounting
        from core_settings.accounting_summary import build_accounting_panel_context
        from analytics.panel_summary import build_services_panel_context, build_outreach_panel_context
        from common.module_runtime import (
            build_panel_integration_groups,
            build_panel_integrations,
            build_panel_modules,
            panel_section_visible,
        )

        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not user.is_authenticated:
            return context

        context['panel_modules'] = build_panel_modules(user)
        context['panel_integrations'] = build_panel_integrations(user)
        context['panel_integration_groups'] = build_panel_integration_groups(user)
        context['can_manage_modules'] = (
            user.is_superuser or user.has_perm_codename('access.settings')
        )

        if panel_section_visible('contact') and user.has_perm_codename('access.contact'):
            context['contact_show_panel'] = True
        if can_access_accounting(user) and panel_section_visible('accounting'):
            context.update(build_accounting_panel_context(user))
        if panel_section_visible('services') and user.has_perm_codename('access.services'):
            context.update(build_services_panel_context(user))
        if panel_section_visible('outreach') and user.has_perm_codename('access.outreach'):
            context.update(build_outreach_panel_context(user))

        context['panel_has_content'] = bool(
            context['panel_modules']
            or context['panel_integrations']
            or context.get('contact_show_panel')
            or context.get('services_show_panel')
            or context.get('accounting_show_payroll')
            or context.get('accounting_show_finance')
            or context.get('accounting_show_reports')
            or context.get('accounting_show_sales')
            or context.get('outreach_show_panel')
            or context['can_manage_modules']
        )
        return context


class ModuleHubView(TemplateView):
    """Modül merkezi — kurulum aç/kapa."""

    template_name = 'common/module_hub.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from common.module_runtime import build_module_hub_context

        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        context.update(build_module_hub_context(self.request.user, query=query))
        context['can_manage_modules'] = (
            self.request.user.is_superuser
            or self.request.user.has_perm_codename('access.settings')
        )
        return context

    def post(self, request, *args, **kwargs):
        from common.middleware import _is_api_request
        from common.module_toggle import toggle_module_slug

        if not (request.user.is_superuser or request.user.has_perm_codename('access.settings')):
            if _is_api_request(request):
                return JsonResponse({'ok': False, 'error': 'Modül ayarları için yetkiniz yok.'}, status=403)
            messages.error(request, 'Modül ayarları için yetkiniz yok.')
            return redirect('module_hub')

        settings = SiteSettings.objects.first()
        if not settings:
            settings = SiteSettings.objects.create()

        redirect_qs = ''
        if request.GET.get('q'):
            redirect_qs = f'?q={request.GET.get("q")}'

        if 'apply_sector' in request.POST:
            sector_slug = request.POST.get('sector_slug', '').strip()
            from common.sector_catalog import sector_by_slug, apply_sector_preset

            if not sector_by_slug(sector_slug):
                messages.error(request, 'Geçersiz sektör profili.')
            else:
                apply_sector_preset(settings, sector_slug)
                sec = sector_by_slug(sector_slug)
                messages.success(
                    request,
                    f'"{sec["name"]}" sektör paketi uygulandı — modüller güncellendi.',
                )

        elif 'toggle_module' in request.POST:
            slug = request.POST.get('module_slug', '').strip()
            result = toggle_module_slug(request.user, slug)
            if _is_api_request(request):
                status = 200 if result.get('ok') else 400
                if not result.get('ok') and 'yetkiniz' in result.get('error', ''):
                    status = 403
                return JsonResponse(result, status=status)
            if result.get('ok'):
                level = result.get('level', 'success')
                if level == 'info':
                    messages.info(request, result['message'])
                else:
                    messages.success(request, result['message'])
            else:
                messages.error(request, result.get('error', 'İşlem başarısız.'))

        from django.urls import reverse
        return redirect(f"{reverse('module_hub')}{redirect_qs}")


class CapabilitiesHubView(TemplateView):
    """Entegrasyon merkezi."""

    template_name = 'common/capabilities_hub.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from common.capability_hub import build_capabilities_hub_context

        context = super().get_context_data(**kwargs)
        context.update(build_capabilities_hub_context(
            self.request.user,
            section=(self.request.GET.get('section') or '').strip() or None,
        ))
        context['can_manage_modules'] = (
            self.request.user.is_superuser
            or self.request.user.has_perm_codename('access.settings')
        )
        return context


class DashboardView(TemplateView):
    template_name = 'services_dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = build_service_dashboard_report()
        context.update(report)
        context['total_customers'] = Customer.objects.count()
        context['statuses'] = StatusOption.objects.order_by('sort_order', 'name')
        context['priorities'] = PriorityOption.objects.order_by('name')
        context['monthly_chart'] = json.dumps({
            'labels': report['monthly_labels'],
            'active': report['monthly_active'],
            'pending': report['monthly_pending'],
            'closed': report['monthly_closed'],
            'cancelled': report['monthly_cancelled'],
            'total': report['monthly_total'],
        }, ensure_ascii=False)
        context['product_chart'] = json.dumps({
            'labels': report['product_labels'],
            'counts': report['product_counts'],
            'colors': report['product_colors'],
        }, ensure_ascii=False)
        return context

class AIPanelView(TemplateView):
    template_name = 'services_dashboard/analytics/ai_panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SiteSettings.objects.first()
        context['site_settings'] = settings
        context['stats'] = {
            'total_customers': Customer.objects.count(),
            'total_services': ServiceRecord.objects.count(),
            'product_count': ServiceRecord.objects.values('products').distinct().count(),
        }
        return context

@require_POST
@json_auth_required
@permission_required('tools.ai')
def ai_chat_view(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        settings = SiteSettings.objects.first()
        if not settings or not settings.ai_chat_enabled:
            return JsonResponse({'error': 'AI Chat is disabled'}, status=403)
            
        # Prepare context for AI
        total_customers = Customer.objects.count()
        total_services = ServiceRecord.objects.count()
        recent_services = ServiceRecord.objects.order_by('-created_at')[:5]
        service_summary = "\n".join([f"- {s.customer.name}: {s.status.name} ({s.priority.name})" for s in recent_services])
        
        system_context = f"""
        {settings.ai_system_prompt}
        
        Sistem Bilgileri:
        - Toplam Müşteri: {total_customers}
        - Toplam Servis Kaydı: {total_services}
        
        Son Servis Kayıtları:
        {service_summary}
        
        Kullanıcıya yardımcı ol, verileri analiz et ve istendiğinde tavsiyelerde bulun.
        """
        
        response_text = ""
        
        # Try Google AI (Gemini) first if key exists
        if settings.google_api_key:
            try:
                from google import genai

                client = genai.Client(api_key=settings.google_api_key)
                chat_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{system_context}\n\nKullanıcı: {user_message}",
                )
                response_text = chat_response.text
            except Exception as e:
                logger.warning('Gemini error: %s', e)
                
        # If Gemini failed or no key, try OpenAI
        if not response_text and settings.openai_api_key:
            try:
                client = openai.OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_context},
                        {"role": "user", "content": user_message}
                    ]
                )
                response_text = completion.choices[0].message.content
            except Exception as e:
                logger.warning('OpenAI error: %s', e)
                
        if not response_text:
            return JsonResponse({'error': 'AI providers failed or keys missing'}, status=500)
            
        return JsonResponse({'message': response_text})
        
    except Exception:
        logger.exception('AI chat request failed')
        return JsonResponse({'error': 'AI isteği işlenemedi.'}, status=500)
