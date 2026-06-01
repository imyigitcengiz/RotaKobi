from django.urls import reverse
from django.views.generic import TemplateView, RedirectView
from django.views import View
import csv
from datetime import date
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .models import (
    SiteSettings, ServiceTypeOption, ProductOption, ProductColorOption, StatusOption, PriorityOption,
    WhatsAppTemplate, SolutionPartner, SolutionPartnerType, ServiceTeam, ServicePersonnel,
    PersonnelDepartment,
    PersonnelPayment, FinanceRecord,
)
from .forms import (
    GeneralSiteSettingsForm, SiteSettingsForm, ServiceTypeOptionForm, ProductOptionForm, StatusOptionForm,
    PriorityOptionForm, WhatsAppTemplateForm, SolutionPartnerForm, SolutionPartnerTypeForm,
    ServiceTeamForm, ServicePersonnelForm, PersonnelDepartmentForm, PersonnelPaymentForm, PersonnelAdvanceForm,
    PersonnelSalaryPayForm, PersonnelSalaryAddForm, PayrollPersonnelQuickForm,
    AccountingPersonnelForm, PayrollQuickAdvanceForm, FinanceRecordForm,
)
from .payroll import (
    build_period_summary,
    build_payroll_report,
    bulk_pay_pending_salaries,
    create_salary_payment,
    default_report_range,
    default_salary_payment_date,
    parse_period,
    period_label,
    process_cycle_salary,
    release_advances_on_salary_delete,
    update_personnel_salary_schedule,
)
from common.permissions import (
    can_manage_payroll, can_manage_finance, can_manage_teams, can_manage_personnel,
    can_access_accounting, can_manage_payroll_personnel, accounting_fallback_redirect,
)
from django.http import HttpResponse, JsonResponse
from common.decorators import json_auth_required, permission_required
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from decimal import Decimal
from core_settings.accounting_summary import _month_bounds
import os
import json


def _update_color_option(request, model, label):
    obj = get_object_or_404(model, pk=request.POST.get('id'))
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, f"{label}: isim boş olamaz.")
        return
    obj.name = name
    obj.color = request.POST.get('color', obj.color)
    obj.save()
    messages.success(request, f"{label} güncellendi.")


def _safe_delete_option(request, model, label):
    obj = model.objects.filter(pk=request.POST.get('id')).first()
    if not obj:
        messages.error(request, f"{label} bulunamadı.")
        return
    try:
        obj.delete()
        messages.info(request, f"{label} silindi.")
    except ProtectedError as exc:
        count = len(exc.protected_objects)
        messages.error(
            request,
            f"Bu {label.lower()} {count} servis kaydında kullanıldığı için silinemez. "
            f"Önce ilgili servislerin {label.lower()}ünü değiştirin.",
        )


SETTINGS_SECTION_META = {
    'genel': {
        'template': 'settings/genel.html',
        'url_name': 'settings_genel',
        'title': 'Genel bilgiler',
        'icon': 'building-2',
    },
    'urunler': {
        'template': 'settings/urunler.html',
        'url_name': 'settings_products',
        'title': 'Ürünler',
        'icon': 'package',
    },
    'ariza-tipleri': {
        'template': 'settings/ariza_tipleri.html',
        'url_name': 'settings_service_types',
        'title': 'Arıza tipleri',
        'icon': 'wrench',
    },
    'durumlar': {
        'template': 'settings/durumlar.html',
        'url_name': 'settings_statuses',
        'title': 'Durumlar',
        'icon': 'list-checks',
    },
    'oncelikler': {
        'template': 'settings/oncelikler.html',
        'url_name': 'settings_priorities',
        'title': 'Öncelikler',
        'icon': 'flag',
    },
    'cozum-turleri': {
        'template': 'settings/cozum_turleri.html',
        'url_name': 'settings_partner_types',
        'title': 'Çözüm ortağı türleri',
        'icon': 'handshake',
    },
}


class SiteSettingsView(TemplateView):
    """Site genel ayarları — /ayarlar/<bölüm>/ (servis modülünden bağımsız)."""
    section = 'genel'

    def dispatch(self, request, *args, **kwargs):
        self.section = kwargs.pop('section', self.section)
        if self.section not in SETTINGS_SECTION_META:
            self.section = 'genel'
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [SETTINGS_SECTION_META[self.section]['template']]

    def _build_options_context(self):
        service_types = ServiceTypeOption.objects.prefetch_related('products').all().order_by('name')
        products = ProductOption.objects.prefetch_related('service_types', 'color_options').all().order_by('name')
        return {
            'settings_section': self.section,
            'settings_section_meta': SETTINGS_SECTION_META,
            'settings_form': GeneralSiteSettingsForm(instance=SiteSettings.objects.first()),
            'service_type_form': ServiceTypeOptionForm(),
            'product_form': ProductOptionForm(),
            'status_form': StatusOptionForm(),
            'priority_form': PriorityOptionForm(),
            'solution_partner_type_form': SolutionPartnerTypeForm(),
            'service_types': service_types,
            'products': products,
            'all_service_types': service_types,
            'all_products': products,
            'statuses': StatusOption.objects.order_by('sort_order', 'name'),
            'priorities': PriorityOption.objects.all(),
            'solution_partner_types': SolutionPartnerType.objects.all(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_options_context())
        meta = SETTINGS_SECTION_META[self.section]
        context['page_title'] = meta['title']
        context['page_icon'] = meta['icon']
        return context

    def _redirect_after_post(self):
        return redirect(SETTINGS_SECTION_META[self.section]['url_name'])

    def post(self, request, *args, **kwargs):
        if 'update_site' in request.POST:
            settings = SiteSettings.objects.first()
            form = GeneralSiteSettingsForm(request.POST, request.FILES, instance=settings)
            try:
                if form.is_valid():
                    obj = form.save()
                    from common.weather_service import refresh_site_coordinates
                    refresh_site_coordinates(obj)
                    messages.success(request, "Site ayarları güncellendi.")
                else:
                    # Show detailed form errors to help debugging
                    messages.error(request, f"Ayarlar güncellenirken hata oluştu: {form.errors.as_text()}")
            except Exception as e:
                messages.error(request, f"Ayarlar kaydedilirken beklenmeyen hata oluştu: {str(e)}")
                
        elif 'add_service_type' in request.POST:
            form = ServiceTypeOptionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Servis tipi eklendi.")
            else:
                messages.error(request, "Geçersiz servis tipi verisi.")
                
        elif 'add_product' in request.POST:
            form = ProductOptionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Ürün eklendi.")
            else:
                messages.error(request, "Geçersiz ürün verisi.")
                
        elif 'add_status' in request.POST:
            form = StatusOptionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Durum seçeneği eklendi.")
            else:
                messages.error(request, "Geçersiz durum verisi. İsim ve renk gerekli.")
                
        elif 'add_priority' in request.POST:
            form = PriorityOptionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Öncelik seçeneği eklendi.")
            else:
                messages.error(request, "Geçersiz öncelik verisi. İsim ve renk gerekli.")
                
        elif 'add_solution_partner_type' in request.POST:
            form = SolutionPartnerTypeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Çözüm ortağı türü eklendi.")
            else:
                messages.error(request, "Geçersiz tür verisi.")
        elif 'update_service_type' in request.POST:
            obj = get_object_or_404(ServiceTypeOption, pk=request.POST.get('id'))
            obj.products.set(request.POST.getlist('product_ids'))
            messages.success(request, "Servis tipi ürün ilişkileri güncellendi.")
        elif 'update_product' in request.POST:
            obj = get_object_or_404(ProductOption, pk=request.POST.get('id'))
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, "Ürün: isim boş olamaz.")
            else:
                obj.name = name
                obj.color = request.POST.get('color', obj.color)
                obj.save()
                obj.service_types.set(request.POST.getlist('service_type_ids'))
                messages.success(request, "Ürün güncellendi.")
        elif 'add_product_color' in request.POST:
            product = get_object_or_404(ProductOption, pk=request.POST.get('product_id'))
            color_name = request.POST.get('color_name', '').strip()
            if not color_name:
                messages.error(request, "Renk adı boş olamaz.")
            elif ProductColorOption.objects.filter(product=product, name__iexact=color_name).exists():
                messages.error(request, "Bu ürün için aynı renk adı zaten var.")
            else:
                ProductColorOption.objects.create(
                    product=product,
                    name=color_name,
                    color=request.POST.get('color', '#0284c7'),
                )
                messages.success(request, f"{product.name} için renk eklendi.")
        elif 'delete_product_color' in request.POST:
            color = ProductColorOption.objects.filter(pk=request.POST.get('color_id')).first()
            if color:
                label = f"{color.product.name} — {color.name}"
                try:
                    color.delete()
                    messages.info(request, f"Renk silindi: {label}")
                except Exception:
                    messages.error(request, "Bu renk satış kayıtlarında kullanıldığı için silinemez.")
        elif 'update_status' in request.POST:
            _update_color_option(request, StatusOption, 'Durum')
        elif 'update_priority' in request.POST:
            _update_color_option(request, PriorityOption, 'Öncelik')
        elif 'update_solution_partner_type' in request.POST:
            obj = get_object_or_404(SolutionPartnerType, pk=request.POST.get('id'))
            form = SolutionPartnerTypeForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, "Çözüm ortağı türü güncellendi.")
            else:
                messages.error(request, "Tür güncellenemedi.")
        elif 'delete_service_type' in request.POST:
            _safe_delete_option(request, ServiceTypeOption, 'Servis tipi')
        elif 'delete_product' in request.POST:
            _safe_delete_option(request, ProductOption, 'Ürün')
        elif 'delete_status' in request.POST:
            _safe_delete_option(request, StatusOption, 'Durum')
        elif 'delete_priority' in request.POST:
            _safe_delete_option(request, PriorityOption, 'Öncelik')
        elif 'delete_solution_partner_type' in request.POST:
            try:
                SolutionPartnerType.objects.filter(id=request.POST.get('id')).delete()
                messages.info(request, "Çözüm ortağı türü silindi.")
            except Exception:
                messages.error(request, "Bu tür kullanımda olduğu için silinemedi.")

        return self._redirect_after_post()



class WhatsAppTemplatesView(TemplateView):
    template_name = 'crm/whatsapp_templates.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['whatsapp_form'] = WhatsAppTemplateForm()
        context['whatsapp_templates'] = WhatsAppTemplate.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        if 'add_whatsapp' in request.POST:
            form = WhatsAppTemplateForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "WhatsApp şablonu eklendi.")
            else:
                messages.error(request, "Geçersiz şablon verisi.")
        elif 'update_whatsapp' in request.POST:
            obj = get_object_or_404(WhatsAppTemplate, pk=request.POST.get('id'))
            title = request.POST.get('title', '').strip()
            message = request.POST.get('message', '').strip()
            if not title or not message:
                messages.error(request, "Şablon başlığı ve mesajı gerekli.")
            else:
                obj.title = title
                obj.message = message
                obj.save()
                messages.success(request, "WhatsApp şablonu güncellendi.")
        elif 'delete_whatsapp' in request.POST:
            WhatsAppTemplate.objects.filter(id=request.POST.get('id')).delete()
            messages.info(request, "Şablon silindi.")
        return redirect('contact_whatsapp_templates')


class SolutionNetworkView(TemplateView):
    template_name = 'crm/solution_network.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        t = self.request.GET.get('type', '').strip()
        active = self.request.GET.get('active', '').strip()

        partners = SolutionPartner.objects.all().order_by('name')
        if q:
            partners = partners.filter(
                Q(name__icontains=q) | Q(phone__icontains=q) | Q(notes__icontains=q)
            )
        if t and t.isdigit():
            partners = partners.filter(partner_type_id=int(t))
        if active == '1':
            partners = partners.filter(is_active=True)
        elif active == '0':
            partners = partners.filter(is_active=False)

        context['solution_partner_form'] = SolutionPartnerForm()
        context['solution_partners'] = partners
        context['partner_types'] = SolutionPartnerType.objects.order_by('name')
        context['active_count'] = SolutionPartner.objects.filter(is_active=True).count()
        context['total_count'] = SolutionPartner.objects.count()
        return context

    def post(self, request, *args, **kwargs):
        if 'add_solution_partner' in request.POST:
            form = SolutionPartnerForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Çözüm ortağı eklendi.")
            else:
                messages.error(request, "Geçersiz çözüm ortağı verisi.")
        elif 'update_solution_partner' in request.POST:
            obj = get_object_or_404(SolutionPartner, pk=request.POST.get('id'))
            form = SolutionPartnerForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, "Çözüm ortağı güncellendi.")
            else:
                messages.error(request, "Çözüm ortağı güncellenemedi.")
        elif 'delete_solution_partner' in request.POST:
            SolutionPartner.objects.filter(id=request.POST.get('id')).delete()
            messages.info(request, "Çözüm ortağı silindi.")
        return redirect('solution_network')


class TeamNetworkView(TemplateView):
    template_name = 'crm/team_network.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_manage_teams'] = can_manage_teams(self.request.user)
        context['team_form'] = ServiceTeamForm()
        context['teams'] = ServiceTeam.objects.prefetch_related('product_groups').all().order_by('name')
        return context

    def post(self, request, *args, **kwargs):
        if not can_manage_teams(request.user):
            messages.error(request, 'Ekip yönetimi için yetkiniz yok.')
            return redirect('team_network')
        if 'add_team' in request.POST:
            form = ServiceTeamForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Ekip eklendi.')
            else:
                messages.error(request, 'Ekip kaydı eklenemedi.')
        elif 'update_team' in request.POST:
            obj = get_object_or_404(ServiceTeam, pk=request.POST.get('id'))
            form = ServiceTeamForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, 'Ekip güncellendi.')
            else:
                messages.error(request, 'Ekip güncellenemedi.')
        elif 'delete_team' in request.POST:
            try:
                ServiceTeam.objects.filter(id=request.POST.get('id')).delete()
                messages.info(request, 'Ekip silindi.')
            except Exception:
                messages.error(request, 'Ekip silinemedi.')
        return redirect('team_network')


class PersonnelNetworkView(RedirectView):
    """Personel yönetimi Muhasebe modülüne taşındı."""
    pattern_name = 'accounting_personnel'
    permanent = False


class AccountingPersonnelView(TemplateView):
    template_name = 'muhasebe/personnel.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_payroll_personnel(request.user):
            messages.error(request, 'Personel yönetimi için yetkiniz yok.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def _show_product_groups(self):
        return can_manage_personnel(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        team = self.request.GET.get('team', '').strip()
        department = self.request.GET.get('department', '').strip()
        period = parse_period(self.request.GET.get('period'))
        show_skills = self._show_product_groups()

        personnel = ServicePersonnel.objects.select_related('team', 'department').prefetch_related('product_groups').order_by('name')
        if q:
            personnel = personnel.filter(
                Q(name__icontains=q)
                | Q(company_phone__icontains=q)
                | Q(notes__icontains=q)
                | Q(job_title__icontains=q)
                | Q(department__name__icontains=q),
            )
        if team and team.isdigit():
            personnel = personnel.filter(team_id=int(team))
        if department and department.isdigit():
            personnel = personnel.filter(department_id=int(department))

        payroll_by_person = {}
        if can_manage_payroll(self.request.user):
            for row in build_period_summary(period)['rows']:
                payroll_by_person[row['personnel'].id] = row

        personnel_rows = [
            {'personnel': p, 'payroll': payroll_by_person.get(p.id)}
            for p in personnel
        ]

        context.update({
            'personnel_form': AccountingPersonnelForm(show_product_groups=show_skills),
            'department_form': PersonnelDepartmentForm(),
            'show_product_groups': show_skills,
            'teams': ServiceTeam.objects.filter(is_active=True).order_by('name'),
            'departments': PersonnelDepartment.objects.filter(is_active=True).order_by('name'),
            'all_departments': PersonnelDepartment.objects.order_by('name'),
            'personnel_list': personnel,
            'personnel_rows': personnel_rows,
            'period': period,
            'period_str': period.strftime('%Y-%m'),
            'period_label': period_label(period),
            'can_payroll': can_manage_payroll(self.request.user),
        })
        return context

    def _apply_pay_date(self, person, form):
        pay_date = form.cleaned_data.get('salary_pay_date')
        if pay_date:
            update_personnel_salary_schedule(person, pay_date=pay_date)

    def post(self, request, *args, **kwargs):
        if not can_manage_payroll_personnel(request.user):
            messages.error(request, 'Personel yönetimi için yetkiniz yok.')
            return redirect('accounting_personnel')

        period_qs = ''
        if request.GET.get('period'):
            period_qs = f'?period={request.GET.get("period")}'
        if request.GET.get('team'):
            period_qs += ('&' if period_qs else '?') + f'team={request.GET.get("team")}'
        if request.GET.get('department'):
            period_qs += ('&' if period_qs else '?') + f'department={request.GET.get("department")}'
        if request.GET.get('q'):
            period_qs += ('&' if period_qs else '?') + f'q={request.GET.get("q")}'

        show_skills = self._show_product_groups()

        if 'add_department' in request.POST:
            form = PersonnelDepartmentForm(request.POST)
            if form.is_valid():
                dept = form.save()
                messages.success(request, f'{dept.name} departmanı eklendi.')
            else:
                messages.error(request, 'Departman eklenemedi.')
        elif 'update_department' in request.POST:
            obj = get_object_or_404(PersonnelDepartment, pk=request.POST.get('id'))
            form = PersonnelDepartmentForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, 'Departman güncellendi.')
            else:
                messages.error(request, 'Departman güncellenemedi.')
        elif 'delete_department' in request.POST:
            try:
                PersonnelDepartment.objects.filter(id=request.POST.get('id')).delete()
                messages.info(request, 'Departman silindi.')
            except Exception:
                messages.error(request, 'Departman silinemedi — bağlı personel olabilir.')
        elif 'add_personnel' in request.POST:
            form = AccountingPersonnelForm(request.POST, show_product_groups=show_skills)
            if form.is_valid():
                person = form.save()
                self._apply_pay_date(person, form)
                messages.success(request, f'{person.name} eklendi.')
            else:
                messages.error(request, 'Personel eklenemedi.')
        elif 'update_personnel' in request.POST:
            obj = get_object_or_404(ServicePersonnel, pk=request.POST.get('id'))
            form = AccountingPersonnelForm(request.POST, instance=obj, show_product_groups=show_skills)
            if form.is_valid():
                person = form.save()
                self._apply_pay_date(person, form)
                messages.success(request, f'{person.name} güncellendi.')
            else:
                messages.error(request, 'Personel güncellenemedi.')
        elif 'delete_personnel' in request.POST:
            ServicePersonnel.objects.filter(id=request.POST.get('id')).delete()
            messages.info(request, 'Personel silindi.')
        return redirect(f"{reverse('accounting_personnel')}{period_qs}")


class AccountingHubView(TemplateView):
    template_name = 'muhasebe/index.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_access_accounting(request.user):
            messages.error(request, 'Muhasebe modülüne erişim yetkiniz yok.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from core_settings.accounting_summary import build_accounting_panel_context

        context = super().get_context_data(**kwargs)
        context.update(build_accounting_panel_context(self.request.user))
        return context


class AccountingReportsHubView(TemplateView):
    template_name = 'muhasebe/reports_hub.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        can_payroll = can_manage_payroll(user)
        can_sales = user.is_superuser or user.has_perm_codename('sales.reports')
        if not can_payroll and not can_sales:
            messages.error(request, 'Raporlar için yetkiniz yok.')
            return accounting_fallback_redirect(user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['show_payroll_report'] = can_manage_payroll(user)
        context['show_sales_report'] = user.is_superuser or user.has_perm_codename('sales.reports')
        context['show_finance_report'] = can_manage_finance(user)
        return context


class AccountingPayrollView(TemplateView):
    template_name = 'muhasebe/payroll.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'Maaş/avans kayıtları için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def _selected_period(self):
        return parse_period(self.request.GET.get('period'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self._selected_period()
        period_str = period.strftime('%Y-%m')
        payment_personnel = self.request.GET.get('payment_personnel', '').strip()

        personnel_qs = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        if payment_personnel and payment_personnel.isdigit():
            personnel_qs = personnel_qs.filter(id=int(payment_personnel))

        summary = build_period_summary(period, personnel_qs)
        payments = PersonnelPayment.objects.select_related(
            'personnel', 'recorded_by', 'settled_by',
        ).filter(period=period)
        if payment_personnel and payment_personnel.isdigit():
            payments = payments.filter(personnel_id=int(payment_personnel))

        context['period'] = period
        context['period_str'] = period_str
        context['period_label'] = period_label(period)
        context['payroll_summary'] = summary
        context['advance_form'] = PersonnelAdvanceForm(period_default=period_str)
        context['salary_form'] = PersonnelSalaryAddForm(period_default=period_str)
        context['personnel_form'] = PayrollPersonnelQuickForm()
        context['teams'] = ServiceTeam.objects.filter(is_active=True).order_by('name')
        context['pending_pay_count'] = sum(1 for r in summary['rows'] if r['can_pay'])
        context['recent_payments'] = payments.order_by('-payment_date', '-created_at')
        context['all_personnel'] = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        context['filter_personnel'] = payment_personnel
        rows_by_id = {r['personnel'].id: r for r in summary['rows']}
        context['personnel_pay_meta'] = {
            str(p.id): {
                'due_date': default_salary_payment_date(p, period).isoformat(),
                'gross': str(p.monthly_salary) if p.monthly_salary else '',
                'pay_day': p.salary_pay_day or '',
                'advances': str(rows_by_id.get(p.id, {}).get('advances_total') or '0'),
                'net': str(rows_by_id.get(p.id, {}).get('net') or ''),
            }
            for p in context['all_personnel']
        }
        return context

    def post(self, request, *args, **kwargs):
        period = parse_period(request.POST.get('period') or request.GET.get('period'))
        period_qs = f'?period={period.strftime("%Y-%m")}'
        personnel_filter = request.POST.get('payment_personnel') or request.GET.get('payment_personnel', '')
        if personnel_filter:
            period_qs += f'&payment_personnel={personnel_filter}'

        if not can_manage_payroll(request.user):
            messages.error(request, 'Maaş/avans kaydı için yetkiniz yok.')
            return redirect('accounting_payroll')

        if 'add_personnel' in request.POST:
            form = PayrollPersonnelQuickForm(request.POST)
            if form.is_valid():
                person = form.save()
                pay_date = form.cleaned_data.get('salary_pay_date')
                if pay_date:
                    update_personnel_salary_schedule(person, pay_date=pay_date)
                messages.success(request, f'{person.name} personel listesine eklendi.')
            else:
                messages.error(request, 'Personel eklenemedi. Ad soyad zorunludur.')
        elif 'quick_advance' in request.POST:
            form = PayrollQuickAdvanceForm(request.POST)
            if form.is_valid():
                pay_period = parse_period(form.cleaned_data['period'])
                payment = PersonnelPayment.objects.create(
                    personnel=form.cleaned_data['personnel'],
                    payment_type=PersonnelPayment.TYPE_ADVANCE,
                    period=pay_period,
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data.get('payment_date') or timezone.localdate(),
                    notes=form.cleaned_data.get('notes') or '',
                    recorded_by=request.user if request.user.is_authenticated else None,
                )
                from common.currency import format_money

                messages.success(
                    request,
                    f'{payment.personnel.name} için {format_money(payment.amount)} avans kaydedildi.',
                )
            else:
                messages.error(request, 'Hızlı avans kaydedilemedi.')
        elif 'bulk_pay_salaries' in request.POST:
            result = bulk_pay_pending_salaries(period, request.user if request.user.is_authenticated else None)
            if result['paid']:
                names = ', '.join(result['paid'][:5])
                if len(result['paid']) > 5:
                    names += '…'
                messages.success(request, f"{len(result['paid'])} personelin maaşı ödendi: {names}")
            for name, reason in result['skipped'][:3]:
                messages.warning(request, f'{name}: {reason}')
            if not result['paid'] and not result['skipped']:
                messages.info(request, 'Bu dönemde ödenecek bekleyen maaş yok.')
        elif 'add_advance' in request.POST:
            form = PersonnelAdvanceForm(request.POST, period_default=period.strftime('%Y-%m'))
            if form.is_valid():
                payment = form.save(commit=False)
                if request.user.is_authenticated:
                    payment.recorded_by = request.user
                payment.save()
                messages.success(request, f'{payment.personnel.name} için avans kaydedildi.')
            else:
                messages.error(request, 'Avans kaydı eklenemedi.')
        elif 'add_salary' in request.POST:
            form = PersonnelSalaryAddForm(request.POST, period_default=period.strftime('%Y-%m'))
            if form.is_valid():
                personnel = form.cleaned_data['personnel']
                pay_period = form.cleaned_data['period']
                try:
                    create_salary_payment(
                        personnel=personnel,
                        period=pay_period,
                        payment_date=form.cleaned_data['payment_date'],
                        recorded_by=request.user if request.user.is_authenticated else None,
                        gross_override=form.cleaned_data.get('gross_amount'),
                        notes=form.cleaned_data.get('notes') or '',
                    )
                    messages.success(request, f'{personnel.name} — {period_label(pay_period)} maaşı kaydedildi.')
                except ValueError as exc:
                    messages.error(request, str(exc))
            else:
                messages.error(request, 'Maaş kaydı eklenemedi.')
        elif 'pay_salary' in request.POST:
            form = PersonnelSalaryPayForm(request.POST)
            if form.is_valid():
                personnel = form.cleaned_data['personnel']
                pay_period = parse_period(form.cleaned_data['period'])
                try:
                    create_salary_payment(
                        personnel=personnel,
                        period=pay_period,
                        payment_date=form.cleaned_data['payment_date'],
                        recorded_by=request.user if request.user.is_authenticated else None,
                        notes=form.cleaned_data.get('notes') or '',
                    )
                    messages.success(request, f'{personnel.name} — {period_label(pay_period)} maaşı net olarak kaydedildi.')
                except ValueError as exc:
                    messages.error(request, str(exc))
            else:
                messages.error(request, 'Maaş ödemesi kaydedilemedi.')
        elif 'cycle_salary' in request.POST:
            personnel_id = request.POST.get('personnel')
            person = ServicePersonnel.objects.filter(pk=personnel_id, is_active=True).first()
            if not person:
                messages.error(request, 'Personel bulunamadı.')
            else:
                raw_date = (request.POST.get('salary_pay_date') or request.POST.get('payment_date') or '').strip()
                notes = (request.POST.get('notes') or '').strip()
                try:
                    payment_date = date.fromisoformat(raw_date) if raw_date else default_salary_payment_date(person, period)
                    process_cycle_salary(
                        personnel=person,
                        period=period,
                        payment_date=payment_date,
                        recorded_by=request.user if request.user.is_authenticated else None,
                        notes=notes,
                    )
                    messages.success(
                        request,
                        f'{person.name} — {period_label(period)} maaşı kaydedildi; '
                        f'her ay {payment_date.day}. gün döngüye alındı.',
                    )
                except ValueError as exc:
                    messages.error(request, str(exc))
        elif 'update_pay_schedule' in request.POST:
            personnel_id = request.POST.get('personnel')
            raw_pay_date = (request.POST.get('salary_pay_date') or '').strip()
            person = ServicePersonnel.objects.filter(pk=personnel_id, is_active=True).first()
            if not person:
                messages.error(request, 'Personel bulunamadı.')
            elif not raw_pay_date:
                messages.error(request, 'Maaş tarihi seçin.')
            else:
                try:
                    pay_date = date.fromisoformat(raw_pay_date)
                    update_personnel_salary_schedule(person, pay_date=pay_date)
                    messages.success(request, f'{person.name} için maaş günü her ay {pay_date.day}. gün olacak şekilde kaydedildi.')
                except ValueError as exc:
                    messages.error(request, str(exc))
        elif 'update_monthly_salary' in request.POST:
            personnel_id = request.POST.get('personnel')
            raw_salary = (request.POST.get('monthly_salary') or '').strip().replace(',', '.')
            raw_pay_date = (request.POST.get('salary_pay_date') or '').strip()
            raw_pay_day = (request.POST.get('salary_pay_day') or '').strip()
            person = ServicePersonnel.objects.filter(pk=personnel_id, is_active=True).first()
            if not person:
                messages.error(request, 'Personel bulunamadı.')
            else:
                from decimal import Decimal

                if raw_salary:
                    person.monthly_salary = Decimal(raw_salary)
                else:
                    person.monthly_salary = None
                update_fields = ['monthly_salary']
                if raw_pay_date:
                    try:
                        person.salary_pay_day = date.fromisoformat(raw_pay_date).day
                        update_fields.append('salary_pay_day')
                    except ValueError as exc:
                        messages.error(request, str(exc))
                        return redirect(f"{reverse('accounting_payroll')}{period_qs}")
                elif raw_pay_day:
                    day = int(raw_pay_day)
                    if day < 1 or day > 31:
                        messages.error(request, 'Maaş günü 1–31 arasında olmalı.')
                        return redirect(f"{reverse('accounting_payroll')}{period_qs}")
                    person.salary_pay_day = day
                    update_fields.append('salary_pay_day')
                person.save(update_fields=update_fields)
                messages.success(request, f'{person.name} maaş bilgileri güncellendi.')
        elif 'delete_payment' in request.POST:
            payment = PersonnelPayment.objects.filter(id=request.POST.get('id')).first()
            if not payment:
                messages.error(request, 'Kayıt bulunamadı.')
            elif payment.payment_type == PersonnelPayment.TYPE_ADVANCE and payment.settled_by_id:
                messages.error(request, 'Mahsup edilmiş avans silinemez. Önce ilgili maaş kaydını silin.')
            else:
                if payment.payment_type == PersonnelPayment.TYPE_SALARY:
                    release_advances_on_salary_delete(payment)
                payment.delete()
                messages.info(request, 'Ödeme kaydı silindi.')
        return redirect(f"{reverse('accounting_payroll')}{period_qs}")


class AccountingPayrollReportsView(TemplateView):
    template_name = 'muhasebe/payroll_reports.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'Maaş raporları için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def _report_params(self):
        default_from, default_to = default_report_range()
        period_from = parse_period(self.request.GET.get('period_from') or default_from.strftime('%Y-%m'))
        period_to = parse_period(self.request.GET.get('period_to') or default_to.strftime('%Y-%m'))
        personnel_id = self.request.GET.get('personnel', '').strip()
        personnel_qs = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        if personnel_id.isdigit():
            personnel_qs = personnel_qs.filter(id=int(personnel_id))
        return period_from, period_to, personnel_qs, personnel_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period_from, period_to, personnel_qs, personnel_id = self._report_params()
        report = build_payroll_report(period_from, period_to, personnel_qs)
        context.update(report)
        context['period_from_str'] = period_from.strftime('%Y-%m')
        context['period_to_str'] = period_to.strftime('%Y-%m')
        context['filter_personnel'] = personnel_id
        context['all_personnel'] = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        context['export_query'] = self.request.GET.urlencode()
        return context


class AccountingPayrollExportView(View):
    def get(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'Dışa aktarma için yetkiniz yok.')
            return redirect('accounting_reports')

        default_from, default_to = default_report_range()
        period_from = parse_period(request.GET.get('period_from') or default_from.strftime('%Y-%m'))
        period_to = parse_period(request.GET.get('period_to') or default_to.strftime('%Y-%m'))
        personnel_id = request.GET.get('personnel', '').strip()
        personnel_qs = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        if personnel_id.isdigit():
            personnel_qs = personnel_qs.filter(id=int(personnel_id))

        report = build_payroll_report(period_from, period_to, personnel_qs)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="maas-avans-{period_from.strftime("%Y-%m")}-{period_to.strftime("%Y-%m")}.csv"'
        )
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Dönem', 'Personel', 'Ekip', 'Brüt', 'Avans (toplam)', 'Bekleyen avans', 'Net (beklenen)', 'Net (ödenen)', 'Durum'])
        for row in report['rows']:
            writer.writerow([
                row['period_label'],
                row['personnel'].name,
                row['personnel'].team.name if row['personnel'].team_id else '—',
                row['gross'],
                row['advances_all'],
                row['advances_open'],
                row['net_expected'] if row['net_expected'] is not None else '',
                row['net_paid'],
                row['status'],
            ])
        writer.writerow([])
        writer.writerow(['TOPLAM', '', '', report['totals']['gross'], report['totals']['advances'], '', report['totals']['pending_net'], report['totals']['net_paid'], ''])
        return response


class AccountingPayrollLedgerExportView(View):
    """Ham maaş/avans hareketleri — içe aktarma formatıyla uyumlu."""

    def get(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'Dışa aktarma için yetkiniz yok.')
            return redirect('accounting_data_exchange')
        from common.csv_io import csv_response
        from core_settings.csv_exchange import export_payroll_payments_rows

        default_from, default_to = default_report_range()
        period_from = parse_period(request.GET.get('period_from') or default_from.strftime('%Y-%m'))
        period_to = parse_period(request.GET.get('period_to') or default_to.strftime('%Y-%m'))
        personnel_id = request.GET.get('personnel', '').strip()
        personnel_qs = ServicePersonnel.objects.filter(is_active=True).order_by('name')
        if personnel_id.isdigit():
            personnel_qs = personnel_qs.filter(id=int(personnel_id))
        rows, _, _ = export_payroll_payments_rows(period_from, period_to, personnel_qs)
        return csv_response(
            f'maas-avans-hareketleri-{period_from.strftime("%Y-%m")}.csv',
            rows,
            header=['DÖNEM', 'PERSONEL', 'TÜR', 'TUTAR', 'TARİH', 'NOT'],
        )


class AccountingPayrollReportsPrintView(TemplateView):
    template_name = 'muhasebe/payroll_reports_print.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'Maaş raporları için yetkiniz yok.')
            return redirect('accounting_reports')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view = AccountingPayrollReportsView()
        view.request = self.request
        context.update(view.get_context_data())
        return context


class AccountingPayrollImportCsvView(View):
    def post(self, request, *args, **kwargs):
        if not can_manage_payroll(request.user):
            messages.error(request, 'İçe aktarma için yetkiniz yok.')
            return redirect('accounting_data_exchange')
        from core_settings.csv_exchange import import_payroll_csv

        uploaded = request.FILES.get('file')
        if not uploaded:
            messages.error(request, 'CSV dosyası seçin.')
            return redirect('accounting_data_exchange')
        try:
            result = import_payroll_csv(uploaded, user=request.user)
            messages.success(request, f'{result["created"]} ödeme kaydı içe aktarıldı.')
            if result.get('skipped'):
                messages.warning(request, f'{result["skipped"]} satır atlandı (personel/tür bulunamadı).')
        except Exception as exc:
            messages.error(request, f'İçe aktarma başarısız: {exc}')
        return redirect('accounting_data_exchange')


class AccountingFinanceExportView(View):
    def get(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Dışa aktarma için yetkiniz yok.')
            return redirect('accounting_finance')
        from common.csv_io import csv_response
        from core_settings.csv_exchange import FINANCE_CSV_HEADER, finance_record_csv_row

        view = AccountingFinanceView()
        view.request = request
        ctx = view.get_context_data()
        rows = [finance_record_csv_row(rec) for rec in ctx['recent_records']]
        return csv_response(
            f'gelir-gider-{ctx["finance_period_str"]}.csv',
            rows,
            header=FINANCE_CSV_HEADER,
        )


class AccountingFinanceImportCsvView(View):
    def post(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'İçe aktarma için yetkiniz yok.')
            return redirect('accounting_data_exchange')
        from core_settings.csv_exchange import import_finance_csv

        uploaded = request.FILES.get('file')
        if not uploaded:
            messages.error(request, 'CSV dosyası seçin.')
            return redirect('accounting_data_exchange')
        try:
            result = import_finance_csv(uploaded, user=request.user)
            messages.success(request, f'{result["created"]} gelir/gider kaydı içe aktarıldı.')
        except Exception as exc:
            messages.error(request, f'İçe aktarma başarısız: {exc}')
        period = request.POST.get('_redirect_period', '')
        suffix = f'?period={period}' if period else ''
        return redirect(reverse('accounting_finance') + suffix)


class AccountingFinancePrintView(TemplateView):
    template_name = 'muhasebe/finance_report_print.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Gelir/gider raporu için yetkiniz yok.')
            return redirect('accounting_finance')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view = AccountingFinanceView()
        view.request = self.request
        context.update(view.get_context_data())
        return context


class AccountingDataExchangeView(TemplateView):
    template_name = 'muhasebe/data_exchange.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        can_payroll = can_manage_payroll(user)
        can_finance = can_manage_finance(user)
        can_sales = (
            user.has_perm_codename('sales.manage')
            or user.has_perm_codename('sales.export')
            or user.has_perm_codename('sales.reports')
        )
        can_customers = user.has_perm_codename('contact.customers')
        can_firms = user.has_perm_codename('contact.firms')
        if not (can_payroll or can_finance or can_sales or can_customers or can_firms):
            messages.error(request, 'Veri alışverişi için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_payroll'] = can_manage_payroll(user)
        context['can_finance'] = can_manage_finance(user)
        context['can_sales_manage'] = user.has_perm_codename('sales.manage')
        context['can_sales_export'] = user.has_perm_codename('sales.export')
        context['can_sales'] = context['can_sales_manage'] or context['can_sales_export'] or user.has_perm_codename('sales.reports')
        context['can_customers'] = user.has_perm_codename('contact.customers')
        context['can_firms'] = user.has_perm_codename('contact.firms')
        today = timezone.localdate()
        from core_settings.payroll import period_start
        period = period_start(today)
        period_str = period.strftime('%Y-%m')
        default_from, default_to = default_report_range()
        context['finance_period_str'] = self.request.GET.get('period') or period_str
        context['payroll_period_from'] = self.request.GET.get('payroll_from') or default_from.strftime('%Y-%m')
        context['payroll_period_to'] = self.request.GET.get('payroll_to') or default_to.strftime('%Y-%m')
        context['payroll_export_query'] = (
            f'period_from={context["payroll_period_from"]}&period_to={context["payroll_period_to"]}'
        )
        return context


class AccountingFinanceView(TemplateView):
    template_name = 'muhasebe/finance.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Gelir/gider kayıtları için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record_type = self.request.GET.get('record_type', '').strip()
        period_str = self.request.GET.get('period', '').strip()
        today = timezone.localdate()
        if period_str:
            from core_settings.payroll import parse_period
            period = parse_period(period_str)
        else:
            from core_settings.payroll import period_start
            period = period_start(today)
        month_start, month_end = _month_bounds(period)

        records = FinanceRecord.objects.select_related(
            'recorded_by', 'cash_account', 'sales_lead__customer', 'operational_project',
        ).filter(
            record_date__gte=month_start,
            record_date__lte=month_end,
        )
        if record_type in (FinanceRecord.TYPE_INCOME, FinanceRecord.TYPE_EXPENSE):
            records = records.filter(record_type=record_type)

        income = records.filter(record_type=FinanceRecord.TYPE_INCOME).aggregate(
            total=Sum('amount'),
        )['total'] or Decimal('0')
        expense = records.filter(record_type=FinanceRecord.TYPE_EXPENSE).aggregate(
            total=Sum('amount'),
        )['total'] or Decimal('0')

        context['finance_form'] = FinanceRecordForm()
        context['recent_records'] = records.order_by('-record_date', '-created_at')[:100]
        context['finance_period_str'] = period.strftime('%Y-%m')
        context['finance_period_label'] = period_label(period)
        context['finance_income_total'] = income
        context['finance_expense_total'] = expense
        context['finance_net_total'] = income - expense
        context['finance_filter_type'] = record_type
        return context

    def _finance_redirect(self, request):
        period = request.POST.get('_redirect_period') or request.GET.get('period', '')
        record_type = request.POST.get('_redirect_record_type') or request.GET.get('record_type', '')
        qs = []
        if period:
            qs.append(f'period={period}')
        if record_type:
            qs.append(f'record_type={record_type}')
        suffix = ('?' + '&'.join(qs)) if qs else ''
        return redirect(reverse('accounting_finance') + suffix)

    def post(self, request, *args, **kwargs):
        if 'add_finance' in request.POST:
            if not can_manage_finance(request.user):
                messages.error(request, 'Gelir/gider kaydı için yetkiniz yok.')
                return self._finance_redirect(request)
            post = request.POST.copy()
            for key in ('cash_account', 'sales_lead', 'operational_project'):
                if not (post.get(key) or '').strip():
                    post.pop(key, None)
            form = FinanceRecordForm(post)
            if form.is_valid():
                record = form.save(commit=False)
                if request.user.is_authenticated:
                    record.recorded_by = request.user
                if not record.cash_account_id:
                    from core_settings.cash_accounts import ensure_default_account
                    record.cash_account = ensure_default_account()
                record.save()
                messages.success(request, 'Kayıt eklendi.')
            else:
                messages.error(request, 'Kayıt eklenemedi.')
        elif 'delete_finance' in request.POST:
            if not can_manage_finance(request.user):
                messages.error(request, 'Gelir/gider kaydı için yetkiniz yok.')
                return self._finance_redirect(request)
            FinanceRecord.objects.filter(id=request.POST.get('id')).delete()
            messages.info(request, 'Kayıt silindi.')
        return self._finance_redirect(request)


@json_auth_required
@permission_required('access.settings')
def settings_api(request):
    """SiteSettings JSON API — kimlik doğrulama, CSRF ve access.settings zorunlu."""
    try:
        settings = SiteSettings.objects.first()
        if request.method == 'GET':
            return JsonResponse({
                'site_name': settings.site_name if settings else '',
                'company_phone': settings.company_phone if settings else '',
                'company_address': settings.company_address if settings else '',
                'ai_chat_enabled': settings.ai_chat_enabled if settings else False,
                'ai_system_prompt': settings.ai_system_prompt if settings else '',
            })

        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            form = SiteSettingsForm(data, files=None, instance=settings)
            if form.is_valid():
                form.save()
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'validation_error', 'details': form.errors}, status=400)

        return JsonResponse({'error': 'Method not allowed'}, status=405)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON'}, status=400)
    except Exception:
        return JsonResponse({'error': 'İşlem başarısız.'}, status=500)


def _serialize_option(obj):
    return {'id': obj.id, 'name': obj.name, 'color': obj.color_hex}


@json_auth_required
@permission_required('access.services', 'access.settings', any_perm=True)
def options_catalog_api(request):
    """Servis formu için tüm seçenekler ve ürün–servis tipi eşlemesi."""
    from core_settings.catalog import build_options_catalog

    return JsonResponse(build_options_catalog())


@json_auth_required
@permission_required('access.services', 'access.settings', any_perm=True)
def service_types_for_products_api(request):
    """Seçili ürünlere göre servis tiplerini döndürür."""
    raw = request.GET.get('product_ids', '')
    product_ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
    all_types = list(ServiceTypeOption.objects.order_by('name'))

    if not product_ids:
        return JsonResponse({
            'service_types': [_serialize_option(s) for s in all_types],
            'filter_mode': 'none',
            'message': 'Ürün seçilmedi; tüm servis tipleri listeleniyor.',
        })

    from core_settings.catalog import resolve_allowed_service_type_ids

    allowed_ids, mode = resolve_allowed_service_type_ids(product_ids)
    if mode == 'all_fallback':
        filtered = all_types
        message = (
            'Seçili ürünlerde tanımlı arıza tipi yok veya en az bir üründe eşleme yok; '
            'tüm tipler gösteriliyor.'
        )
    else:
        filtered = [s for s in all_types if s.id in allowed_ids]
        message = f'{len(filtered)} servis tipi bu ürün(ler) için tanımlı.'

    return JsonResponse({
        'service_types': [_serialize_option(s) for s in filtered],
        'filter_mode': mode,
        'message': message,
    })


@json_auth_required
@permission_required('services.manage', 'access.settings', any_perm=True)
def quick_option_create_api(request):
    """Servis formundan hızlı seçenek ekleme."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON'}, status=400)

    kind = data.get('type')
    name = (data.get('name') or '').strip()
    color = data.get('color') or '#3b82f6'

    if not name:
        return JsonResponse({'error': 'İsim gerekli'}, status=400)

    model_map = {
        'status': StatusOption,
        'priority': PriorityOption,
        'product': ProductOption,
        'service_type': ServiceTypeOption,
    }
    model = model_map.get(kind)
    if not model:
        return JsonResponse({'error': 'Geçersiz tip'}, status=400)

    obj = model.objects.create(name=name, color=color)
    payload = _serialize_option(obj)
    if kind == 'product':
        st_ids = data.get('service_type_ids') or []
        if st_ids:
            obj.service_types.set(st_ids)
        payload['service_type_ids'] = list(obj.service_types.values_list('id', flat=True))
    if kind == 'service_type':
        product_ids = [int(x) for x in data.get('product_ids') or [] if str(x).isdigit()]
        for product in ProductOption.objects.filter(id__in=product_ids):
            product.service_types.add(obj)
        payload['product_ids'] = list(obj.products.values_list('id', flat=True))

    from config.live_sync import publish_live_event

    publish_live_event(
        kind='options',
        action='created',
        message='Yeni seçenek eklendi.',
        user_id=getattr(request.user, 'id', None),
    )
    return JsonResponse({'ok': True, 'item': payload, 'type': kind})


@json_auth_required
@permission_required('services.manage', 'access.settings', any_perm=True)
def quick_option_update_api(request):
    """Servis formundan hızlı seçenek güncelleme."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON'}, status=400)

    kind = data.get('type')
    pk = data.get('id')
    name = (data.get('name') or '').strip()
    if not pk or not name:
        return JsonResponse({'error': 'id ve name gerekli'}, status=400)

    model_map = {
        'status': StatusOption,
        'priority': PriorityOption,
        'product': ProductOption,
        'service_type': ServiceTypeOption,
    }
    model = model_map.get(kind)
    if not model:
        return JsonResponse({'error': 'Geçersiz tip'}, status=400)

    obj = get_object_or_404(model, pk=pk)
    obj.name = name
    if 'color' in data:
        obj.color = data['color']
    obj.save()

    if kind == 'product' and 'service_type_ids' in data:
        obj.service_types.set(data['service_type_ids'] or [])

    if kind == 'service_type' and 'product_ids' in data:
        product_ids = [int(x) for x in data.get('product_ids') or [] if str(x).isdigit()]
        for product in ProductOption.objects.filter(id__in=product_ids):
            product.service_types.add(obj)

    payload = _serialize_option(obj)
    if kind == 'product':
        payload['service_type_ids'] = list(obj.service_types.values_list('id', flat=True))
    if kind == 'service_type':
        payload['product_ids'] = list(obj.products.values_list('id', flat=True))

    from config.live_sync import publish_live_event

    publish_live_event(
        kind='options',
        action='updated',
        message='Seçenek güncellendi.',
        user_id=getattr(request.user, 'id', None),
    )
    return JsonResponse({'ok': True, 'item': payload})


class AccountingCashView(TemplateView):
    template_name = 'muhasebe/cash.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Kasa görüntüleme için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.cash import save_cash_settings

        if not can_manage_finance(request.user):
            return accounting_fallback_redirect(request.user)
        try:
            opening = Decimal(str(request.POST.get('opening_balance', '0')).replace(',', '.'))
        except Exception:
            opening = Decimal('0')
        raw_date = (request.POST.get('opening_date') or '').strip()
        opening_date = date.fromisoformat(raw_date) if raw_date else None
        save_cash_settings(
            opening_balance=opening,
            opening_date=opening_date,
            include_payroll=request.POST.get('include_payroll') == 'on',
            include_sales=request.POST.get('include_sales') == 'on',
        )
        messages.success(request, 'Kasa ayarları kaydedildi.')
        return redirect('accounting_cash')

    def get_context_data(self, **kwargs):
        from core_settings.cash import build_cash_snapshot, get_cash_settings

        context = super().get_context_data(**kwargs)
        context['cash_snapshot'] = build_cash_snapshot()
        context['cash_settings'] = get_cash_settings()
        return context


class AccountingReceivablesView(TemplateView):
    template_name = 'muhasebe/receivables.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        allowed = (
            user.is_superuser
            or user.has_perm_codename('sales.reports')
            or user.has_perm_codename('sales.manage')
            or user.has_perm_codename('sales.export')
        )
        if not allowed:
            messages.error(request, 'Alacak listesi için yetkiniz yok.')
            return accounting_fallback_redirect(user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from sales_leads.receivables import build_receivables_context

        context = super().get_context_data(**kwargs)
        overdue_days = 30
        raw = self.request.GET.get('overdue_days', '')
        if raw.isdigit():
            overdue_days = max(1, int(raw))
        context.update(build_receivables_context(overdue_days=overdue_days))
        return context


class AccountingStockView(TemplateView):
    template_name = 'muhasebe/stock.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Stok görüntüleme için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def _redirect_stock(self, request):
        product = request.POST.get('product') or request.GET.get('product', '')
        low = request.GET.get('low') or request.POST.get('low', '')
        url = reverse('accounting_stock')
        params = []
        if product and str(product).isdigit():
            params.append(f'product={product}')
        if low == '1':
            params.append('low=1')
        if params:
            url += '?' + '&'.join(params)
        return redirect(url)

    def post(self, request, *args, **kwargs):
        from decimal import Decimal, InvalidOperation

        from core_settings.models import Material, ProductOption, ProductRecipeLine, StockMovement
        from core_settings.stock import (
            InsufficientStockError,
            apply_movement,
            save_stock_settings,
        )

        if not can_manage_finance(request.user):
            return accounting_fallback_redirect(request.user)

        if request.POST.get('save_stock_settings'):
            save_stock_settings(
                auto_deduct_on_sale=request.POST.get('auto_deduct_on_sale') == 'on',
                auto_deduct_on_service=request.POST.get('auto_deduct_on_service') == 'on',
                block_negative_stock=request.POST.get('block_negative_stock') == 'on',
            )
            messages.success(request, 'Stok ayarları kaydedildi.')
            return self._redirect_stock(request)

        if request.POST.get('add_material'):
            name = (request.POST.get('name') or '').strip()
            if not name:
                messages.error(request, 'Malzeme adı gerekli.')
                return self._redirect_stock(request)
            unit = request.POST.get('unit', Material.UNIT_PIECE)
            if unit not in dict(Material.UNIT_CHOICES):
                unit = Material.UNIT_PIECE
            Material.objects.create(
                name=name,
                unit=unit,
                sku=(request.POST.get('sku') or '').strip(),
            )
            messages.success(request, f'Malzeme eklendi: {name}')
            return self._redirect_stock(request)

        if request.POST.get('update_material'):
            material_id = request.POST.get('material_id', '')
            if material_id.isdigit():
                material = Material.objects.filter(pk=int(material_id)).first()
                if material:
                    raw = (request.POST.get('min_stock_level') or '0').replace(',', '.')
                    try:
                        material.min_stock_level = Decimal(raw)
                    except InvalidOperation:
                        material.min_stock_level = Decimal('0')
                    material.save(update_fields=['min_stock_level', 'updated_at'])
                    messages.success(request, f'{material.name} kritik seviye güncellendi.')
            return self._redirect_stock(request)

        if request.POST.get('add_recipe_line'):
            product_id = request.POST.get('product', '')
            material_id = request.POST.get('material_id', '')
            raw_qty = (request.POST.get('quantity') or '1').replace(',', '.')
            if not product_id.isdigit() or not material_id.isdigit():
                messages.error(request, 'Ürün ve malzeme seçin.')
                return self._redirect_stock(request)
            try:
                qty = Decimal(raw_qty)
            except InvalidOperation:
                qty = Decimal('1')
            if qty <= 0:
                messages.error(request, 'Miktar 0\'dan büyük olmalı.')
                return self._redirect_stock(request)
            product = ProductOption.objects.filter(pk=int(product_id)).first()
            material = Material.objects.filter(pk=int(material_id), is_active=True).first()
            if not product or not material:
                messages.error(request, 'Ürün veya malzeme bulunamadı.')
                return self._redirect_stock(request)
            ProductRecipeLine.objects.update_or_create(
                product=product,
                material=material,
                defaults={'quantity': qty},
            )
            messages.success(request, f'{product.name} reçetesine {material.name} eklendi.')
            return self._redirect_stock(request)

        if request.POST.get('delete_recipe_line'):
            line_id = request.POST.get('line_id', '')
            if line_id.isdigit():
                ProductRecipeLine.objects.filter(pk=int(line_id)).delete()
                messages.success(request, 'Reçete satırı silindi.')
            return self._redirect_stock(request)

        if request.POST.get('add_movement'):
            material_id = request.POST.get('material_id', '')
            movement_kind = request.POST.get('movement_kind', 'in')
            raw_qty = (request.POST.get('quantity') or '').replace(',', '.')
            note = (request.POST.get('note') or '').strip()
            if not material_id.isdigit() or not raw_qty:
                messages.error(request, 'Malzeme ve miktar gerekli.')
                return self._redirect_stock(request)
            try:
                quantity = Decimal(raw_qty)
            except InvalidOperation:
                messages.error(request, 'Geçerli miktar girin.')
                return self._redirect_stock(request)
            if quantity <= 0:
                messages.error(request, 'Miktar 0\'dan büyük olmalı.')
                return self._redirect_stock(request)
            delta = quantity if movement_kind == 'in' else -quantity
            reason = (
                StockMovement.REASON_PURCHASE
                if movement_kind == 'in'
                else StockMovement.REASON_MANUAL
            )
            material = Material.objects.filter(pk=int(material_id), is_active=True).first()
            if not material:
                messages.error(request, 'Malzeme bulunamadı.')
                return self._redirect_stock(request)
            try:
                apply_movement(
                    material,
                    delta,
                    reason=reason,
                    note=note,
                    recorded_by=request.user,
                    force=True,
                )
                messages.success(request, f'{material.name}: {delta:+} kaydedildi.')
            except InsufficientStockError as exc:
                messages.error(request, str(exc))
            return self._redirect_stock(request)

        return self._redirect_stock(request)

    def get_context_data(self, **kwargs):
        from core_settings.stock import build_stock_context

        context = super().get_context_data(**kwargs)
        low_only = self.request.GET.get('low') == '1'
        product_raw = self.request.GET.get('product', '')
        recipe_product_id = int(product_raw) if product_raw.isdigit() else None
        context.update(build_stock_context(
            low_only=low_only,
            recipe_product_id=recipe_product_id,
        ))
        return context
