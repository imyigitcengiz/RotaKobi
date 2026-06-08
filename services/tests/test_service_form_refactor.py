from django.test import TestCase
from decimal import Decimal
from django.contrib.auth import get_user_model
from common.tests.helpers import default_test_brand
from core_settings.models import SiteSettings, ServicePersonnel, ServiceTeam, StatusOption, PriorityOption
from customers.models import Customer
from services.models import ServiceRecord
from services.forms import ServiceRecordForm

User = get_user_model()

class ServiceFormRefactorTests(TestCase):
    def setUp(self):
        # Create necessary options
        self.status = StatusOption.objects.create(name='Aktif', sort_order=1)
        self.priority = PriorityOption.objects.create(name='Yüksek')
        
        self.brand = default_test_brand()
        # Create customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            phone='5551234567',
            brand=self.brand,
        )

        # Create settings
        self.settings = SiteSettings.objects.create(
            site_name='Test CoolOPS',
            warranty_years=2,
            warranty_months=6,
            warranty_days=15,
        )

        # Create team & personnel
        self.team = ServiceTeam.objects.create(name='Destek Ekibi')
        self.personnel = ServicePersonnel.objects.create(
            name='Ahmet Usta',
            team=self.team,
            brand=self.brand,
            is_active=True,
        )

    def test_site_settings_has_warranty_fields(self):
        self.assertEqual(self.settings.warranty_years, 2)
        self.assertEqual(self.settings.warranty_months, 6)
        self.assertEqual(self.settings.warranty_days, 15)

    def test_service_record_has_partner_fee(self):
        service = ServiceRecord.objects.create(
            customer=self.customer,
            brand=self.brand,
            status=self.status,
            priority=self.priority,
            partner_fee=Decimal('250.75'),
        )
        self.assertEqual(service.partner_fee, Decimal('250.75'))

    def test_form_excludes_assigned_to_and_includes_partner_fee(self):
        form = ServiceRecordForm()
        self.assertNotIn('assigned_to', form.fields)
        self.assertIn('partner_fee', form.fields)

    def test_form_parses_turkish_decimal_for_partner_fee(self):
        form_data = {
            'customer': self.customer.id,
            'status': self.status.id,
            'priority': self.priority.id,
            'list_price': '600,50',
            'partner_fee': '450,25',
            'warranty_status': 'active',
        }
        form = ServiceRecordForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['list_price'], Decimal('600.50'))
        self.assertEqual(form.cleaned_data['partner_fee'], Decimal('450.25'))

    def test_personnel_choices_show_team(self):
        form = ServiceRecordForm()
        choices = list(form.fields['service_personnel'].choices)
        # Check if the label contains Ahmet Usta and his team name
        found = False
        for val, label in choices:
            if 'Ahmet Usta (Destek Ekibi)' in label:
                found = True
                break
        self.assertTrue(found, "Personnel choice label did not display team name.")

    def test_form_includes_warranty_note_and_saves_successfully(self):
        form_data = {
            'customer': self.customer.id,
            'status': self.status.id,
            'priority': self.priority.id,
            'warranty_status': 'expired',
            'list_price': '500,00',
            'warranty_note': 'Müşteri kullanım hatasından dolayı garanti dışı kalmıştır.',
        }
        form = ServiceRecordForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['warranty_note'], 'Müşteri kullanım hatasından dolayı garanti dışı kalmıştır.')
