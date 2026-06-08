from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from core_settings.backup import backup_status_summary
from core_settings.forms import AISettingsForm
from core_settings.models import SiteSettings
from core_settings.system_backup_handlers import handle_system_backup_post
from customers.models import Customer
from services.models import ServiceRecord
from users.mixins import SuperuserRequiredMixin


class SettingsAISettingsView(TemplateView):
    template_name = 'settings/ai_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SiteSettings.objects.first()
        context['ai_form'] = AISettingsForm(instance=settings)
        context['ai_enabled'] = bool(settings and settings.ai_chat_enabled)
        return context

    def post(self, request, *args, **kwargs):
        settings = SiteSettings.objects.first()
        if not settings:
            settings = SiteSettings.objects.create(site_name='Kobi Hub')
        form = AISettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'AI ayarları kaydedildi.')
        else:
            messages.error(request, f'Ayarlar kaydedilemedi: {form.errors.as_text()}')
        return redirect('settings_ai_settings')


class SettingsAIReportingView(TemplateView):
    template_name = 'settings/ai_reporting.html'

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


class SettingsSystemBackupView(SuperuserRequiredMixin, TemplateView):
    template_name = 'settings/system_backup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backup_status'] = backup_status_summary()
        from core_settings.backup import FACTORY_RESET_CONFIRM_PHRASE
        context['factory_reset_confirm_phrase'] = FACTORY_RESET_CONFIRM_PHRASE
        return context

    def post(self, request, *args, **kwargs):
        return handle_system_backup_post(request, redirect_name='settings_system_backup')
