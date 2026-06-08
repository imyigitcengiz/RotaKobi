from decimal import Decimal, InvalidOperation

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
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
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from common.decorators import json_auth_required, permission_required
from .service_report import build_service_dashboard_report

logger = logging.getLogger(__name__)

class PublicLandingView(TemplateView):
    """Herkese açık tanıtım sayfası — girişten önce."""

    template_name = 'landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from users.impersonation import get_real_user, is_impersonating

            user = get_real_user(request)
            if user.is_superuser and not is_impersonating(request):
                return redirect('admin_dashboard')
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
        from core_settings.models import Plan
        context['plans'] = Plan.objects.filter(is_active=True).order_by('price')
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
            context.update(build_accounting_panel_context(self.request))
        if panel_section_visible('services') and user.has_perm_codename('access.services'):
            context.update(build_services_panel_context(self.request))
        if panel_section_visible('outreach') and user.has_perm_codename('access.outreach'):
            context.update(build_outreach_panel_context(request))

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

        # Abonelik özet kartı için
        from core_settings.models import BrandMembership
        from common.brand_scope import user_brands

        context['active_plan'] = user.active_plan
        context['user_brands'] = list(user_brands(user))
        context['owned_brands_count'] = BrandMembership.objects.filter(
            user=user,
            role=BrandMembership.ROLE_OWNER
        ).count()

        return context


class SubscriptionView(LoginRequiredMixin, TemplateView):
    """Abonelik & Bayi / Franchise Yönetimi — ayrı sayfa."""
    template_name = 'panel_subscription.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        from core_settings.models import Plan, BillingInvoice, BrandMembership, BusinessBrand
        from common.brand_scope import user_brands, get_active_brand
        from common.module_runtime import build_subscription_modules_context

        context = super().get_context_data(**kwargs)
        user = self.request.user
        plan = user.active_plan
        context['active_plan'] = plan
        context['plans'] = Plan.objects.filter(is_active=True).order_by('price')
        context['user_brands'] = list(user_brands(user))
        context['active_brand'] = get_active_brand(self.request)
        owned = BrandMembership.objects.filter(
            user=user, role=BrandMembership.ROLE_OWNER, brand__is_active=True,
        ).select_related('brand')
        context['owned_brands_count'] = owned.count()
        context['owned_hq_count'] = owned.filter(brand__panel_kind=BusinessBrand.PANEL_HQ).count()
        context['owned_dealer_count'] = owned.filter(brand__panel_kind=BusinessBrand.PANEL_DEALER).count()
        context['hq_limit'] = getattr(plan, 'max_hq_brands', None) or plan.max_brands
        context['dealer_limit'] = getattr(plan, 'max_dealer_panels', 0)
        context['invoices'] = BillingInvoice.objects.filter(user=user).order_by('-created_at')[:20]
        context.update(build_subscription_modules_context(user))
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        action = request.POST.get('form_action')
        user = request.user

        if action == 'brand_create':
            from common.brand_scope import create_brand_for_user, get_active_brand, set_active_brand
            from common.tenant import build_brand_public_url
            from core_settings.models import BusinessBrand

            brand_name = request.POST.get('name', '').strip()
            is_dealer = request.POST.get('panel_kind') == BusinessBrand.PANEL_DEALER
            parent = get_active_brand(request) if is_dealer else None
            if is_dealer and parent and parent.panel_kind == BusinessBrand.PANEL_DEALER:
                parent = parent.parent_brand
            tenant_routing = request.POST.get('tenant_routing') or BusinessBrand.TENANT_SUBDOMAIN
            if tenant_routing not in {BusinessBrand.TENANT_SUBDOMAIN, BusinessBrand.TENANT_PATH}:
                tenant_routing = BusinessBrand.TENANT_SUBDOMAIN
            try:
                if is_dealer and not parent:
                    raise ValueError('Bayi paneli oluşturmak için önce merkez markanızı seçin.')
                brand = create_brand_for_user(
                    user,
                    brand_name,
                    panel_kind=BusinessBrand.PANEL_DEALER if is_dealer else BusinessBrand.PANEL_HQ,
                    parent_brand=parent,
                    tenant_routing=tenant_routing,
                    legal_name=request.POST.get('legal_name', '').strip(),
                    phone=request.POST.get('phone', '').strip(),
                )
                set_active_brand(request, brand.pk)
                panel_url = build_brand_public_url(brand, request)
                kind_label = 'Bayi' if is_dealer else 'Merkez'
                messages.success(
                    request,
                    f'"{brand.name}" {kind_label} paneli oluşturuldu. Giriş adresi: {panel_url}',
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect('subscription_dashboard')

        elif action == 'brand_switch':
            from common.brand_scope import set_active_brand
            try:
                brand_id = int(request.POST.get('brand_id', ''))
                if set_active_brand(request, brand_id):
                    messages.success(request, 'Aktif panel değiştirildi.')
                else:
                    messages.error(request, 'Bu panele erişiminiz yok.')
            except (TypeError, ValueError):
                messages.error(request, 'Geçersiz panel seçimi.')
            return redirect('subscription_dashboard')

        elif action == 'upgrade_plan':
            from common.module_plan import clamp_owner_modules_to_plan
            from core_settings.models import Plan, BillingInvoice
            try:
                plan = Plan.objects.get(pk=request.POST.get('plan_id'), is_active=True)
                user.plan = plan
                user.save(update_fields=['plan'])
                clamp_owner_modules_to_plan(user)
                BillingInvoice.objects.create(user=user, plan=plan, amount=plan.price, status='paid')
                messages.success(request, f'Aboneliğiniz "{plan.name}" planına güncellendi.')
            except Plan.DoesNotExist:
                messages.error(request, 'Geçersiz plan seçimi.')
            return redirect('subscription_dashboard')

        return redirect('subscription_dashboard')


class ModuleHubView(TemplateView):
    """Eski modül merkezi — abonelik sayfasına yönlendir."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser:
            return redirect('admin_plans')
        return redirect(reverse('subscription_dashboard') + '#moduller')


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
