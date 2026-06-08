"""Yol haritası muhasebe modülleri — borç, çoklu kasa, proje maliyeti, dış aktarım, zaman, projeler."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from common.permissions import accounting_fallback_redirect, can_manage_finance, can_manage_installation_schedule
from core_settings.models import (
    CashAccount,
    InstallationScheduleEntry,
    OperationalProject,
    SupplierPayable,
    TimeEntry,
)


def _finance_guard(view_method):
    def wrapper(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Bu ekran için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return view_method(self, request, *args, **kwargs)
    return wrapper


class AccountingPayablesView(TemplateView):
    template_name = 'muhasebe/payables.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Tedarikçi borçları için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.payables import create_payable, parse_decimal, record_payment

        action = request.POST.get('action', '')
        if action == 'create':
            try:
                amount = parse_decimal(request.POST.get('amount', '0'))
                due_raw = (request.POST.get('due_date') or '').strip()
                due_date = date.fromisoformat(due_raw) if due_raw else None
                create_payable(
                    supplier_name=request.POST.get('supplier_name', ''),
                    amount=amount,
                    due_date=due_date,
                    invoice_ref=request.POST.get('invoice_ref', ''),
                    notes=request.POST.get('notes', ''),
                    request=request,
                )
                messages.success(request, 'Tedarikçi borcu eklendi.')
            except ValueError as exc:
                messages.error(request, str(exc))
        elif action == 'pay':
            from common.brand_scope import filter_by_brand
            payable = get_object_or_404(
                filter_by_brand(SupplierPayable.objects.all(), request),
                pk=request.POST.get('payable_id'),
            )
            try:
                amount = parse_decimal(request.POST.get('pay_amount', '0'))
                record_payment(payable, amount, request.user, request=request)
                messages.success(request, 'Ödeme kaydedildi ve gider oluşturuldu.')
            except ValueError as exc:
                messages.error(request, str(exc))
        return redirect('accounting_payables')

    def get_context_data(self, **kwargs):
        from core_settings.payables import build_payables_context

        context = super().get_context_data(**kwargs)
        overdue_days = 30
        raw = self.request.GET.get('overdue_days', '')
        if raw.isdigit():
            overdue_days = max(1, int(raw))
        context.update(build_payables_context(request=self.request, overdue_days=overdue_days))
        return context


class AccountingCashAccountsView(TemplateView):
    template_name = 'muhasebe/cash_accounts.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Hesap listesi için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.cash_accounts import create_account

        action = request.POST.get('action', '')
        if action == 'create':
            try:
                opening = Decimal(str(request.POST.get('opening_balance', '0')).replace(',', '.'))
            except InvalidOperation:
                opening = Decimal('0')
            create_account(
                name=request.POST.get('name', ''),
                account_type=request.POST.get('account_type', CashAccount.TYPE_CASH),
                opening_balance=opening,
                is_default=request.POST.get('is_default') == 'on',
            )
            messages.success(request, 'Hesap eklendi.')
        return redirect('accounting_cash_accounts')

    def get_context_data(self, **kwargs):
        from core_settings.cash_accounts import build_accounts_context

        context = super().get_context_data(**kwargs)
        context.update(build_accounts_context())
        return context


class AccountingProjectCostingView(TemplateView):
    template_name = 'muhasebe/project_costing.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Proje maliyet ekranı için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from core_settings.project_costing import build_project_costing_context

        context = super().get_context_data(**kwargs)
        lead_raw = self.request.GET.get('lead', '')
        lead_id = int(lead_raw) if lead_raw.isdigit() else None
        context.update(build_project_costing_context(lead_id=lead_id))
        return context


class AccountingEExportView(TemplateView):
    template_name = 'muhasebe/e_export.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Dış aktarım için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.e_export import build_combined_csv, save_advisor_note

        action = request.POST.get('action', '')
        if action == 'note':
            save_advisor_note(request.POST.get('advisor_note', ''))
            messages.success(request, 'Mali müşavir notu kaydedildi.')
            return redirect('accounting_e_export')

        start_raw = (request.POST.get('start') or '').strip()
        end_raw = (request.POST.get('end') or '').strip()
        try:
            start = date.fromisoformat(start_raw)
            end = date.fromisoformat(end_raw)
        except ValueError:
            messages.error(request, 'Geçerli tarih aralığı seçin.')
            return redirect('accounting_e_export')

        csv_text = build_combined_csv(request=request, start=start, end=end)
        response = HttpResponse(csv_text, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="coolops-dis-aktarim-{start}_{end}.csv"'
        return response

    def get_context_data(self, **kwargs):
        from core_settings.e_export import build_e_export_summary

        context = super().get_context_data(**kwargs)
        start = end = None
        start_raw = self.request.GET.get('start', '')
        end_raw = self.request.GET.get('end', '')
        if start_raw and end_raw:
            try:
                start = date.fromisoformat(start_raw)
                end = date.fromisoformat(end_raw)
            except ValueError:
                pass
        context.update(build_e_export_summary(request=self.request, start=start, end=end))
        return context


class AccountingTimesheetView(TemplateView):
    template_name = 'muhasebe/timesheet.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_finance(request.user):
            messages.error(request, 'Zaman kaydı için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.timesheet_ops import create_time_entry

        action = request.POST.get('action', '')
        if action == 'create':
            try:
                hours = Decimal(str(request.POST.get('hours', '0')).replace(',', '.'))
                entry_date = date.fromisoformat(request.POST.get('entry_date', ''))
                create_time_entry(
                    entry_date=entry_date,
                    hours=hours,
                    description=request.POST.get('description', ''),
                    personnel_id=request.POST.get('personnel_id') or None,
                    sales_lead_id=request.POST.get('sales_lead_id') or None,
                    project_id=request.POST.get('project_id') or None,
                    billable=request.POST.get('billable') == 'on',
                    user=request.user,
                )
                messages.success(request, 'Zaman kaydı eklendi.')
            except (ValueError, InvalidOperation) as exc:
                messages.error(request, str(exc) or 'Kayıt eklenemedi.')
        elif action == 'toggle_invoiced':
            from common.brand_scope import get_active_brand_id
            from django.db.models import Q
            entry_qs = TimeEntry.objects.filter(pk=request.POST.get('entry_id'))
            bid = get_active_brand_id(request)
            if bid:
                entry_qs = entry_qs.filter(
                    Q(personnel__brand_id=bid) | Q(sales_lead__customer__brand_id=bid),
                )
            entry = get_object_or_404(entry_qs)
            entry.invoiced = not entry.invoiced
            entry.save(update_fields=['invoiced'])
            messages.success(request, 'Faturalama durumu güncellendi.')
        year = request.POST.get('year') or timezone.localdate().year
        month = request.POST.get('month') or timezone.localdate().month
        return redirect(f'{request.path}?year={year}&month={month}')

    def get_context_data(self, **kwargs):
        from core_settings.timesheet_ops import build_timesheet_context

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))
        context.update(build_timesheet_context(request=self.request, year=year, month=month))
        from core_settings.models import OperationalProject
        from sales_leads.models import SalesLead
        context['timesheet_projects'] = OperationalProject.objects.order_by('name')[:50]
        context['timesheet_sales'] = SalesLead.objects.select_related('customer').order_by('-sale_date')[:50]
        return context


class AccountingProjectsView(TemplateView):
    template_name = 'muhasebe/projects.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_installation_schedule(request.user):
            messages.error(request, 'Montaj programı için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core_settings.installation_schedule import (
            create_schedule_entry,
            save_schedule_settings,
            schedule_redirect_url,
            update_schedule_entry,
        )
        from core_settings.models import SiteSettings

        action = request.POST.get('action', '')
        settings = SiteSettings.objects.first()

        if action == 'create_entry':
            raw_date = (request.POST.get('scheduled_date') or '').strip()
            customer_id = request.POST.get('customer_id')
            if not raw_date or not customer_id:
                messages.error(request, 'Gün ve müşteri zorunludur.')
            else:
                try:
                    create_schedule_entry(
                        scheduled_date=date.fromisoformat(raw_date),
                        customer_id=int(customer_id),
                        team_id=request.POST.get('team_id') or None,
                        sales_lead_id=request.POST.get('sales_lead_id') or None,
                        work_type=request.POST.get('work_type', ''),
                        notes=request.POST.get('notes', ''),
                    )
                    messages.success(request, 'Montaj planı eklendi.')
                except (ValueError, TypeError):
                    messages.error(request, 'Geçersiz tarih veya müşteri.')
                except Exception:
                    messages.error(request, 'Kayıt eklenemedi — müşteri ve tarihi kontrol edin.')

        elif action == 'update_entry':
            from common.brand_scope import get_active_brand_id
            entry_qs = InstallationScheduleEntry.objects.filter(pk=request.POST.get('entry_id'))
            bid = get_active_brand_id(request)
            if bid:
                entry_qs = entry_qs.filter(customer__brand_id=bid)
            entry = get_object_or_404(entry_qs)
            raw_date = (request.POST.get('scheduled_date') or '').strip()
            try:
                fields = {
                    'customer_id': int(request.POST.get('customer_id') or entry.customer_id),
                    'team_id': request.POST.get('team_id') or None,
                    'sales_lead_id': request.POST.get('sales_lead_id') or None,
                    'work_type': request.POST.get('work_type', entry.work_type),
                    'notes': request.POST.get('notes', ''),
                }
                if raw_date:
                    fields['scheduled_date'] = date.fromisoformat(raw_date)
                update_schedule_entry(entry, **fields)
                messages.success(request, 'Kayıt güncellendi.')
            except (ValueError, TypeError):
                messages.error(request, 'Güncelleme başarısız.')

        elif action == 'delete_entry':
            from common.brand_scope import get_active_brand_id
            entry_qs = InstallationScheduleEntry.objects.filter(pk=request.POST.get('entry_id'))
            bid = get_active_brand_id(request)
            if bid:
                entry_qs = entry_qs.filter(customer__brand_id=bid)
            entry = get_object_or_404(entry_qs)
            entry.delete()
            messages.info(request, 'Montaj planı silindi.')

        elif action == 'save_schedule_settings' and settings:
            save_schedule_settings(
                settings,
                saturday_working=request.POST.get('schedule_saturday_working') == 'on',
                sunday_working=request.POST.get('schedule_sunday_working') == 'on',
                saturday_default_work=request.POST.get(
                    'schedule_saturday_default_work',
                    InstallationScheduleEntry.TYPE_INSTALLATION,
                ),
                weather_city=(request.POST.get('schedule_weather_city') or '').strip(),
            )
            messages.success(request, 'Montaj planı ve hava ayarları kaydedildi.')

        return redirect(schedule_redirect_url(request))

    def get_context_data(self, **kwargs):
        from core_settings.installation_schedule import (
            build_schedule_calendar,
            schedule_form_context,
        )
        from core_settings.models import ServiceTeam
        from customers.models import Customer
        from sales_leads.models import SalesLead

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))
        view = self.request.GET.get('view', 'month')
        week_raw = self.request.GET.get('week')
        week_index = int(week_raw) if week_raw is not None and week_raw.isdigit() else None

        from common.brand_scope import filter_customers, filter_sales_leads

        context.update(build_schedule_calendar(
            request=self.request,
            year=year,
            month=month,
            view=view if view in ('month', 'week') else 'month',
            week_index=week_index,
        ))
        context.update(schedule_form_context(self.request))
        context['schedule_customers'] = filter_customers(Customer.objects.order_by('name'), self.request)[:200]
        context['schedule_teams'] = ServiceTeam.objects.filter(is_active=True).order_by('name')
        context['schedule_sales_leads'] = (
            filter_sales_leads(SalesLead.objects.select_related('customer').order_by('-sale_date'), self.request)[:80]
        )
        context['selected_day'] = self.request.GET.get('day', '')
        return context


class AccountingProjectsPrintView(TemplateView):
    template_name = 'muhasebe/projects_print.html'

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_installation_schedule(request.user):
            messages.error(request, 'Yazdırma için yetkiniz yok.')
            return accounting_fallback_redirect(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from core_settings.installation_schedule import build_schedule_calendar

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))
        view = self.request.GET.get('view', 'month')
        week_raw = self.request.GET.get('week')
        week_index = int(week_raw) if week_raw is not None and week_raw.isdigit() else None

        context.update(build_schedule_calendar(
            request=self.request,
            year=year,
            month=month,
            view=view if view in ('month', 'week') else 'month',
            week_index=week_index,
        ))
        context['print_scope_label'] = (
            f'Hafta {week_index + 1}' if view == 'week' and week_index is not None
            else context.get('calendar_month_label', '')
        )
        return context
