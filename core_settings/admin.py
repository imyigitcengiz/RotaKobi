from django.contrib import admin
from .models import (
    SiteSettings,
    ServiceTypeOption,
    ProductOption,
    ProductColorOption,
    StatusOption,
    PriorityOption,
    WhatsAppTemplate,
    SolutionPartner,
    SolutionPartnerType,
    ServiceTeam,
    ServicePersonnel,
    PersonnelDepartment,
    CashAccount,
    SupplierPayable,
    InstallationScheduleEntry,
    OperationalProject,
    TimeEntry,
    FinanceRecord,
    EExportSettings,
)

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

admin.site.register(ServiceTypeOption)
admin.site.register(ProductOption)
admin.site.register(ProductColorOption)
admin.site.register(StatusOption)
admin.site.register(PriorityOption)
admin.site.register(WhatsAppTemplate)
admin.site.register(SolutionPartner)
admin.site.register(SolutionPartnerType)
admin.site.register(ServiceTeam)
admin.site.register(PersonnelDepartment)
admin.site.register(ServicePersonnel)
admin.site.register(CashAccount)
admin.site.register(SupplierPayable)
admin.site.register(InstallationScheduleEntry)
admin.site.register(OperationalProject)
admin.site.register(TimeEntry)
admin.site.register(EExportSettings)


@admin.register(FinanceRecord)
class FinanceRecordAdmin(admin.ModelAdmin):
    list_display = ('record_date', 'record_type', 'title', 'amount', 'cash_account', 'sales_lead')
    list_filter = ('record_type', 'category')
    search_fields = ('title', 'notes')
    raw_id_fields = ('sales_lead', 'operational_project', 'cash_account', 'recorded_by')
