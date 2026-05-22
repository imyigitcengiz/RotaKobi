from django import forms
from core_settings.catalog import filter_service_type_ids
from .models import ServiceRecord, ServiceImage
from core_settings.models import ServiceTypeOption, ProductOption, SolutionPartner, ServicePersonnel

class ServiceRecordForm(forms.ModelForm):
    class Meta:
        model = ServiceRecord
        fields = [
            'customer', 'solution_partner', 'status', 'priority', 'products',
            'service_types', 'notes', 'assigned_to', 'service_personnel',
            'warranty_status', 'list_price', 'discounted_price',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'solution_partner': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'status': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'priority': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'products': forms.CheckboxSelectMultiple(attrs={'class': 'grid grid-cols-2 gap-4'}),
            'service_types': forms.CheckboxSelectMultiple(attrs={'class': 'grid grid-cols-2 gap-4'}),
            'notes': forms.Textarea(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'service_personnel': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'warranty_status': forms.Select(attrs={'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500'}),
            'list_price': forms.NumberInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
            'discounted_price': forms.NumberInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-brand-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['solution_partner'].queryset = SolutionPartner.objects.filter(is_active=True).order_by('name')
        self.fields['solution_partner'].empty_label = 'Çözüm ortağı seçin (opsiyonel)'
        self.fields['service_personnel'].queryset = ServicePersonnel.objects.filter(is_active=True).select_related('team').order_by('name')
        self.fields['service_personnel'].empty_label = 'Servis personeli seçin (opsiyonel)'
        self.fields['list_price'].label = 'Normal fiyat (₺)'
        self.fields['discounted_price'].label = 'İndirimli fiyat (₺)'

    def clean(self):
        cleaned = super().clean()
        products = cleaned.get('products')
        service_types = cleaned.get('service_types')
        if products is not None and service_types is not None:
            product_ids = [p.pk for p in products]
            st_ids = [st.pk for st in service_types]
            allowed = filter_service_type_ids(product_ids, st_ids)
            allowed_set = set(allowed)
            cleaned['service_types'] = [st for st in service_types if st.pk in allowed_set]
        return cleaned
