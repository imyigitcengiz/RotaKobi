from django.conf import settings
from django.db import models

from common.currency import CURRENCY_CODE_CHOICES, DEFAULT_CURRENCY_CODE, currency_from_settings
from common.storage_paths import site_logo_upload_to

from .color_utils import DEFAULT_HEX, normalize_hex


class SiteSettings(models.Model):
    BULK_PRINT_SORT_CHOICES = [
        ('created_desc', 'Tarih (Yeni -> Eski)'),
        ('created_asc', 'Tarih (Eski -> Yeni)'),
        ('customer', 'Müşteri Adına Göre'),
        ('product', 'Ürüne Göre'),
        ('team', 'Ekibe Göre'),
        ('personnel', 'Personele Göre'),
        ('status', 'Duruma Göre'),
        ('priority', 'Önceliğe Göre'),
    ]

    site_name = models.CharField(max_length=255, default="Kobi Hub")
    logo = models.ImageField(upload_to=site_logo_upload_to, null=True, blank=True)
    company_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Firma Telefonu")
    company_address = models.TextField(blank=True, null=True, verbose_name="Firma Adresi")
    
    warranty_years = models.PositiveIntegerField(default=1, verbose_name="Garanti Süresi (Yıl)")
    warranty_months = models.PositiveIntegerField(default=0, verbose_name="Garanti Süresi (Ay)")
    warranty_days = models.PositiveIntegerField(default=0, verbose_name="Garanti Süresi (Gün)")
    currency_code = models.CharField(
        max_length=3,
        choices=CURRENCY_CODE_CHOICES,
        default=DEFAULT_CURRENCY_CODE,
        verbose_name='Para birimi',
        help_text='Tüm tutar alanları ve raporlarda kullanılır.',
    )
    bulk_print_default_sort = models.CharField(
        max_length=20,
        choices=BULK_PRINT_SORT_CHOICES,
        default='created_desc',
        verbose_name='Toplu Yazdır Varsayılan Sıralama',
    )
    sidebar_profile_name = models.CharField(max_length=100, default="Yönetici", verbose_name="Sol Alt Profil Adı")
    sidebar_profile_role = models.CharField(max_length=100, default="Admin", verbose_name="Sol Alt Profil Ünvanı")

    openai_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="OpenAI API Key")
    google_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Google AI (Gemini) API Key")
    ai_chat_enabled = models.BooleanField(default=False, verbose_name="Yapay Zeka Sohbet Aktif")
    ai_system_prompt = models.TextField(
        blank=True,
        null=True,
        default="Sen bir asistanasın. Kullanıcının sorularını yanıtla ve ona yardımcı ol.",
        verbose_name="Yapay Zeka Sistem Talimatı",
    )
    whatsapp_default_delay = models.PositiveSmallIntegerField(
        default=4,
        verbose_name='WhatsApp varsayılan bekleme (sn)',
    )
    whatsapp_skip_globally_default = models.BooleanField(
        default=False,
        verbose_name='WhatsApp: daha önce mesaj atılanları varsayılan atla',
    )
    whatsapp_location_request_template = models.TextField(
        blank=True,
        default='',
        verbose_name='Yazdırma: WhatsApp konum isteme mesajı',
        help_text='Toplu yazdırmada konum yoksa QR bu metinle oluşturulur. Değişkenler: {site_name}, {ariza}',
    )
    whatsapp_cloud_token = models.CharField(
        max_length=512,
        blank=True,
        default='',
        verbose_name='WhatsApp Business API token',
    )
    whatsapp_cloud_phone_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='WhatsApp Business telefon numarası ID',
    )

    primary_vertical_slug = models.CharField(
        max_length=32,
        default='montaj_saha',
        verbose_name='Birincil sektör profili',
        help_text='Kurumsal sektör tipi — modül paketi bu profile göre önerilir.',
    )
    weather_city = models.CharField(
        max_length=120,
        blank=True,
        default='İstanbul',
        verbose_name='Hava durumu şehri',
        help_text='Open-Meteo ile otomatik koordinat çözülür; API anahtarı gerekmez.',
    )
    weather_latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Hava enlem',
    )
    weather_longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Hava boylam',
    )
    schedule_saturday_working = models.BooleanField(
        default=True,
        verbose_name='Cumartesi çalışma günü',
        help_text='Kapalıysa cumartesi montaj programında tatil olarak işaretlenir.',
    )
    schedule_sunday_working = models.BooleanField(
        default=False,
        verbose_name='Pazar çalışma günü',
        help_text='Kapalıysa pazar montaj programında tatil olarak işaretlenir.',
    )
    schedule_saturday_default_work = models.CharField(
        max_length=20,
        choices=(
            ('installation', 'Montaj'),
            ('service', 'Servis'),
        ),
        default='installation',
        verbose_name='Cumartesi varsayılan iş tipi',
        help_text='Cumartesi gününe yeni kayıt eklerken önerilen montaj veya servis.',
    )
    enabled_module_slugs = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Açık modüller',
        help_text='Boş bırakılırsa varsayılan aktif modüller kullanılır.',
    )
    profile_setup_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Profil kurulumu tamamlandı',
        help_text='İlk kurulum sihirbazı tamamlandığında doldurulur.',
    )

    class Meta:
        verbose_name = "Site Ayarları"
        verbose_name_plural = "Site Ayarları"

    def __str__(self):
        return self.site_name

    @property
    def currency_symbol(self) -> str:
        return currency_from_settings(self).symbol

    @property
    def currency_label(self) -> str:
        return currency_from_settings(self).label


def business_brand_logo_upload_to(instance, filename):
    from pathlib import Path

    slug = (instance.slug or 'marka').replace('/', '-')
    ext = Path(filename).suffix.lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        ext = '.jpg'
    return f'brands/{slug}/logo{ext}'


class Plan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Plan adı")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Fiyat")
    max_brands = models.PositiveIntegerField(default=1, verbose_name="Maksimum marka sayısı")
    max_hq_brands = models.PositiveIntegerField(
        default=1,
        verbose_name='Maksimum merkez panel',
    )
    max_dealer_panels = models.PositiveIntegerField(
        default=0,
        verbose_name='Maksimum bayi alt panel',
    )
    max_users_per_brand = models.PositiveIntegerField(default=3, verbose_name="Marka başına maksimum kullanıcı")
    max_customers_per_brand = models.PositiveIntegerField(default=100, verbose_name="Marka başına maksimum müşteri")
    included_module_slugs = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Plana dahil modüller',
    )
    included_particle_slugs = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Plana dahil parçacıklar',
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planlar'

    @staticmethod
    def format_limit(value: int) -> str:
        if value >= 1000:
            return f'{value:,}'.replace(',', '.')
        return str(value)

    @property
    def brands_limit_display(self) -> str:
        return self.format_limit(self.max_brands)

    @property
    def users_limit_display(self) -> str:
        return self.format_limit(self.max_users_per_brand)

    @property
    def customers_limit_display(self) -> str:
        return self.format_limit(self.max_customers_per_brand)

    @property
    def module_count(self) -> int:
        from common.module_plan import plan_included_modules
        return len(plan_included_modules(self))

    def save(self, *args, **kwargs):
        if self.max_hq_brands or self.max_dealer_panels:
            self.max_brands = (self.max_hq_brands or 0) + (self.max_dealer_panels or 0) or self.max_brands
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BusinessBrand(models.Model):
    """Çalışma markası / firma — veriler marka bazında ayrılır."""

    PANEL_HQ = 'hq'
    PANEL_DEALER = 'dealer'
    PANEL_KIND_CHOICES = (
        (PANEL_HQ, 'Merkez panel'),
        (PANEL_DEALER, 'Bayi / franchise paneli'),
    )
    TENANT_SUBDOMAIN = 'subdomain'
    TENANT_PATH = 'path'
    TENANT_ROUTING_CHOICES = (
        (TENANT_SUBDOMAIN, 'Alt alan adı (bayi.marka.coolops.com)'),
        (TENANT_PATH, 'Yol öneki (marka.coolops.com/bayi)'),
    )

    name = models.CharField(max_length=255, verbose_name='Marka / firma adı')
    slug = models.SlugField(max_length=80, unique=True)
    host_slug = models.SlugField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='Alan adı kısa adı',
        help_text='Boşsa slug kullanılır. Örn. marka.coolops.com için "marka".',
    )
    panel_kind = models.CharField(
        max_length=10,
        choices=PANEL_KIND_CHOICES,
        default=PANEL_HQ,
        verbose_name='Panel türü',
    )
    parent_brand = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='dealer_panels',
        verbose_name='Bağlı merkez marka',
    )
    tenant_routing = models.CharField(
        max_length=12,
        choices=TENANT_ROUTING_CHOICES,
        default=TENANT_SUBDOMAIN,
        verbose_name='Erişim yapısı',
    )
    legal_name = models.CharField(max_length=255, blank=True, default='', verbose_name='Ticari ünvan')
    logo = models.ImageField(
        upload_to=business_brand_logo_upload_to,
        null=True,
        blank=True,
        verbose_name='Logo',
    )
    phone = models.CharField(max_length=50, blank=True, default='', verbose_name='Telefon')
    address = models.TextField(blank=True, default='', verbose_name='Adres')
    currency_code = models.CharField(
        max_length=3,
        choices=CURRENCY_CODE_CHOICES,
        default=DEFAULT_CURRENCY_CODE,
        verbose_name='Para birimi',
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name='Sistem varsayılanı',
        help_text='Eski kayıtlar ve üyeliksiz kullanıcılar için.',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_brands',
        verbose_name='Oluşturan',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marka / firma'
        verbose_name_plural = 'Markalar / firmalar'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def tenant_key(self) -> str:
        return (self.host_slug or self.slug).strip()

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name) or 'marka'
            slug = base
            n = 1
            while BusinessBrand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f'{base}-{n}'
            self.slug = slug
        if self.panel_kind == self.PANEL_DEALER and not self.parent_brand_id:
            raise ValueError('Bayi paneli bir merkez markaya bağlı olmalıdır.')
        if self.panel_kind == self.PANEL_HQ:
            self.parent_brand = None
        super().save(*args, **kwargs)


class BrandMembership(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_MEMBER = 'member'
    ROLE_DEALER = 'dealer'
    ROLE_CHOICES = (
        (ROLE_OWNER, 'Sahip'),
        (ROLE_MEMBER, 'Üye'),
        (ROLE_DEALER, 'Bayi kullanıcısı'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='brand_memberships',
    )
    brand = models.ForeignKey(
        BusinessBrand,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER)
    is_default = models.BooleanField(default=False, verbose_name='Varsayılan marka')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Marka üyeliği'
        verbose_name_plural = 'Marka üyelikleri'
        constraints = [
            models.UniqueConstraint(fields=['user', 'brand'], name='uniq_brand_membership_user_brand'),
        ]

    def __str__(self):
        return f'{self.user_id} → {self.brand.name}'


class WorkSchedulePlan(models.Model):
    """Haftalık mesai planı — site ayarlarından yönetilir."""

    name = models.CharField(max_length=120, verbose_name='Plan adı')
    notes = models.TextField(blank=True, default='', verbose_name='Açıklama')
    is_default = models.BooleanField(
        default=False,
        verbose_name='Varsayılan plan',
        help_text='Montaj programı ve mesai kontrollerinde öncelikli plan.',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    weekly_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Haftalık mesai',
        help_text='Gün başına: çalışma günü mü, başlangıç ve bitiş saati.',
    )
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Sıra')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'sort_order', 'name']
        verbose_name = 'Mesai planı'
        verbose_name_plural = 'Mesai planları'

    def __str__(self):
        return self.name

    def summary(self) -> str:
        from core_settings.work_schedule import format_plan_summary

        return format_plan_summary(self)


class ColorOptionMixin(models.Model):
    color = models.CharField(max_length=7, default='#3b82f6', verbose_name="Renk")

    class Meta:
        abstract = True

    _COLOR_KIND = {
        'ServiceTypeOption': 'service_type',
        'ProductOption': 'product',
        'StatusOption': 'status',
        'PriorityOption': 'priority',
    }

    @property
    def color_hex(self):
        kind = self._COLOR_KIND.get(self.__class__.__name__, 'status')
        return normalize_hex(self.color, fallback=DEFAULT_HEX.get(kind, '#3b82f6'))

    def save(self, *args, **kwargs):
        kind = self._COLOR_KIND.get(self.__class__.__name__, 'status')
        self.color = normalize_hex(self.color, fallback=DEFAULT_HEX.get(kind, '#3b82f6'))
        super().save(*args, **kwargs)


class ServiceTypeOption(ColorOptionMixin, models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Servis tipi"
        verbose_name_plural = "Servis tipleri"

    def __str__(self):
        return self.name


class ProductOption(ColorOptionMixin, models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='box')
    service_types = models.ManyToManyField(
        ServiceTypeOption,
        blank=True,
        related_name='products',
        verbose_name='İzin verilen arıza / servis tipleri',
    )

    class Meta:
        verbose_name = "Ürün seçeneği"
        verbose_name_plural = "Ürün seçenekleri"

    def __str__(self):
        return self.name


class ProductColorOption(ColorOptionMixin, models.Model):
    product = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name='color_options',
        verbose_name='Ürün',
    )
    name = models.CharField(max_length=100, verbose_name='Renk adı')

    class Meta:
        verbose_name = 'Ürün rengi'
        verbose_name_plural = 'Ürün renkleri'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['product', 'name'], name='uniq_product_color_name'),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.name}'


class StatusOption(ColorOptionMixin, models.Model):
    LIST_ACTIVE = 'active'
    LIST_PENDING = 'pending'
    LIST_HIDDEN = 'hidden'
    LIST_GROUP_CHOICES = [
        (LIST_ACTIVE, 'Liste: varsayılan göster'),
        (LIST_PENDING, 'Liste: isteğe bağlı (beklemede)'),
        (LIST_HIDDEN, 'Liste: varsayılan gizle'),
    ]

    name = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Sıra')
    list_group = models.CharField(
        max_length=20,
        choices=LIST_GROUP_CHOICES,
        default=LIST_ACTIVE,
        verbose_name='Liste görünürlüğü',
    )

    class Meta:
        verbose_name = "Servis durumu"
        verbose_name_plural = "Servis durumları"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class WhatsAppTemplate(models.Model):
    SCENARIO_SERVICE_CREATED = 'service_created'
    SCENARIO_SERVICE_STATUS = 'service_status'
    SCENARIO_SALES_LEAD_CREATED = 'sales_lead_created'
    SCENARIO_SALES_LEAD_STATUS = 'sales_lead_status'
    SCENARIO_CUSTOMER_CREATED = 'customer_created'
    SCENARIO_CHOICES = (
        (SCENARIO_SERVICE_CREATED, 'Servis — ilk kayıt açılışı'),
        (SCENARIO_SERVICE_STATUS, 'Servis — durum değişimi'),
        (SCENARIO_SALES_LEAD_CREATED, 'Satış — ilk kayıt'),
        (SCENARIO_SALES_LEAD_STATUS, 'Satış — durum değişimi'),
        (SCENARIO_CUSTOMER_CREATED, 'Müşteri — ilk kayıt'),
    )

    title = models.CharField(max_length=100, verbose_name="Kural adı")
    message = models.TextField(verbose_name="Mesaj içeriği")
    scenario = models.CharField(
        max_length=40,
        choices=SCENARIO_CHOICES,
        default=SCENARIO_SERVICE_STATUS,
        verbose_name='Senaryo',
    )
    trigger_from = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='Eski durum (önce)',
        help_text='Durum değişiminde önceki değer. Boş = herhangi.',
    )
    trigger_to = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='Yeni durum (sonra)',
        help_text='Oluşturma anındaki durum veya değişim sonrası durum. Boş = herhangi.',
    )
    trigger_value = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='Durum / koşul (eski)',
        help_text='Kullanımdan kalktı — trigger_to kullanın.',
    )
    auto_send = models.BooleanField(default=True, verbose_name='Otomatik gönder')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    connection = models.ForeignKey(
        'tools.WhatsappConnection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scenario_templates',
        verbose_name='Gönderen hat',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "WhatsApp Şablonu"
        verbose_name_plural = "WhatsApp Şablonları"
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class PriorityOption(ColorOptionMixin, models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Öncelik"
        verbose_name_plural = "Öncelikler"

    def __str__(self):
        return self.name


class SolutionPartnerType(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name='Tür adı')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Çözüm ortağı türü'
        verbose_name_plural = 'Çözüm ortağı türleri'
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceTeam(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name='Ekip adı')
    product_groups = models.ManyToManyField(
        ProductOption,
        blank=True,
        related_name='skilled_teams',
        verbose_name='Yetenekli ürün grupları',
    )
    company_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Şirket hattı')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Servis ekibi'
        verbose_name_plural = 'Servis ekipleri'
        ordering = ['name']

    def __str__(self):
        return self.name


class PersonnelDepartment(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name='Departman adı')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Personel departmanı'
        verbose_name_plural = 'Personel departmanları'
        ordering = ['name']

    def __str__(self):
        return self.name


class ServicePersonnel(models.Model):
    brand = models.ForeignKey(
        BusinessBrand,
        on_delete=models.PROTECT,
        related_name='personnel',
        verbose_name='Marka / firma',
    )
    name = models.CharField(max_length=120, verbose_name='Ad Soyad')
    department = models.ForeignKey(
        PersonnelDepartment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel',
        verbose_name='Departman',
        help_text='Organizasyon birimi — ofis, tasarım, saha vb.',
    )
    job_title = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Ünvan',
        help_text='Örn: Grafik Tasarımcı, Montaj Ustası',
    )
    team = models.ForeignKey(
        ServiceTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel',
        verbose_name='Ekip',
        help_text='Saha servis ekibi — ofis personeli için boş bırakılabilir.',
    )
    product_groups = models.ManyToManyField(
        ProductOption,
        blank=True,
        related_name='skilled_personnel',
        verbose_name='Yetenekli ürün grupları',
    )
    company_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Şirket numarası')
    monthly_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Aylık maaş',
        help_text='Muhasebe modülünde aylık döngü hesabı için.',
    )
    salary_pay_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Maaş günü',
        help_text='Her ay maaşın ödeneceği gün (1–31).',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name='Not')

    class Meta:
        verbose_name = 'Personel'
        verbose_name_plural = 'Personeller'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def org_summary(self) -> str:
        parts: list[str] = []
        if self.department_id:
            parts.append(self.department.name)
        if self.job_title:
            parts.append(self.job_title)
        if self.team_id:
            parts.append(f'Ekip: {self.team.name}')
        return ' · '.join(parts)


class PersonnelPayment(models.Model):
    TYPE_SALARY = 'salary'
    TYPE_ADVANCE = 'advance'
    TYPE_CHOICES = (
        (TYPE_SALARY, 'Maaş'),
        (TYPE_ADVANCE, 'Avans'),
    )

    personnel = models.ForeignKey(
        ServicePersonnel,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Personel',
    )
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Tür')
    period = models.DateField(
        verbose_name='Maaş dönemi',
        help_text='Ayın ilk günü — avans ve maaş hangi aya ait.',
    )
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Brüt maaş',
        help_text='Maaş ödemesinde brüt tutar; net amount alanına yazılır.',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Tutar')
    payment_date = models.DateField(verbose_name='Ödeme tarihi')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Not')
    settled_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settled_advances',
        verbose_name='Mahsup eden maaş',
    )
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel_payments',
        verbose_name='Kaydeden',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Personel ödemesi'
        verbose_name_plural = 'Personel ödemeleri'
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f'{self.personnel.name} — {self.get_payment_type_display()} ({self.amount})'


class FinanceRecord(models.Model):
    brand = models.ForeignKey(
        BusinessBrand,
        on_delete=models.PROTECT,
        related_name='finance_records',
        verbose_name='Marka / firma',
    )
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'
    TYPE_CHOICES = (
        (TYPE_INCOME, 'Gelir'),
        (TYPE_EXPENSE, 'Gider'),
    )
    EXPENSE_CATEGORY_CHOICES = (
        ('', 'Genel'),
        ('rent', 'Kira'),
        ('fuel', 'Yakıt'),
        ('material', 'Malzeme'),
        ('office', 'Ofis'),
        ('marketing', 'Pazarlama'),
        ('payroll_other', 'Personel (diğer)'),
        ('supplier', 'Tedarikçi'),
        ('other', 'Diğer'),
    )

    record_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Tür')
    category = models.CharField(
        max_length=20,
        blank=True,
        default='',
        choices=EXPENSE_CATEGORY_CHOICES,
        verbose_name='Gider kategorisi',
        help_text='Yalnızca gider kayıtlarında anlamlıdır.',
    )
    title = models.CharField(max_length=120, verbose_name='Açıklama')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Tutar')
    record_date = models.DateField(verbose_name='Tarih')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Not')
    cash_account = models.ForeignKey(
        'core_settings.CashAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_records',
        verbose_name='Hesap',
    )
    sales_lead = models.ForeignKey(
        'sales_leads.SalesLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_records',
        verbose_name='Satış / proje',
    )
    operational_project = models.ForeignKey(
        'core_settings.OperationalProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_records',
        verbose_name='Operasyon projesi',
    )
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_records',
        verbose_name='Kaydeden',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gelir/gider kaydı'
        verbose_name_plural = 'Gelir/gider kayıtları'
        ordering = ['-record_date', '-created_at']

    def __str__(self):
        return f'{self.get_record_type_display()} — {self.title} ({self.amount})'


class CashSettings(models.Model):
    """Tekil kasa ayarları — açılış bakiyesi ve otomatik dahil etme kuralları."""

    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Açılış bakiyesi (₺)',
    )
    opening_date = models.DateField(null=True, blank=True, verbose_name='Açılış tarihi')
    include_payroll_in_balance = models.BooleanField(
        default=True,
        verbose_name='Maaş/avans ödemelerini kasadan düş',
    )
    include_sales_collections_in_balance = models.BooleanField(
        default=True,
        verbose_name='Satış tahsilatlarını (peşinat + ara ödeme) kasaya ekle',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kasa ayarları'
        verbose_name_plural = 'Kasa ayarları'

    def __str__(self):
        return f'Kasa (açılış {self.opening_balance} ₺)'


class StockSettings(models.Model):
    """Tekil stok ayarları — otomatik düşüm kuralları."""

    auto_deduct_on_sale = models.BooleanField(
        default=True,
        verbose_name='Tamamlanan satışta stok düş',
    )
    auto_deduct_on_service = models.BooleanField(
        default=False,
        verbose_name='Servis kaydında stok düş (ürün başına 1 adet)',
    )
    block_negative_stock = models.BooleanField(
        default=True,
        verbose_name='Stok eksiye düşmesin',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stok ayarları'
        verbose_name_plural = 'Stok ayarları'

    def __str__(self):
        return 'Stok ayarları'


class Material(models.Model):
    """Stokta tutulan ham malzeme / parça — satış ürününden ayrı."""

    UNIT_PIECE = 'piece'
    UNIT_METER = 'm'
    UNIT_KG = 'kg'
    UNIT_LITER = 'l'
    UNIT_CHOICES = (
        (UNIT_PIECE, 'Adet'),
        (UNIT_METER, 'Metre'),
        (UNIT_KG, 'Kg'),
        (UNIT_LITER, 'Litre'),
    )

    name = models.CharField(max_length=120, verbose_name='Malzeme adı')
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_PIECE,
        verbose_name='Birim',
    )
    stock_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Mevcut stok',
    )
    min_stock_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Kritik seviye',
    )
    sku = models.CharField(max_length=64, blank=True, verbose_name='Stok kodu')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Not')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Malzeme'
        verbose_name_plural = 'Malzemeler'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductRecipeLine(models.Model):
    """Ürün reçetesi — 1 satış ürünü için gerekli malzemeler."""

    product = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name='recipe_lines',
        verbose_name='Satış ürünü',
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='recipe_lines',
        verbose_name='Malzeme',
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name='Miktar (1 ürün başına)',
    )

    class Meta:
        verbose_name = 'Reçete satırı'
        verbose_name_plural = 'Reçete satırları'
        ordering = ['material__name']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'material'],
                name='uniq_product_recipe_material',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} → {self.material.name} × {self.quantity}'


class StockMovement(models.Model):
    REASON_PURCHASE = 'purchase'
    REASON_SALE = 'sale'
    REASON_SALE_CANCEL = 'sale_cancel'
    REASON_SERVICE = 'service'
    REASON_COUNT = 'count'
    REASON_MANUAL = 'manual'
    REASON_CHOICES = (
        (REASON_PURCHASE, 'Alış / giriş'),
        (REASON_SALE, 'Satış'),
        (REASON_SALE_CANCEL, 'Satış iptali'),
        (REASON_SERVICE, 'Servis'),
        (REASON_COUNT, 'Sayım'),
        (REASON_MANUAL, 'Manuel'),
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name='Malzeme',
    )
    delta = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Değişim (+/−)')
    quantity_after = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Sonraki stok')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, verbose_name='Neden')
    note = models.CharField(max_length=255, blank=True, verbose_name='Not')
    sales_lead = models.ForeignKey(
        'sales_leads.SalesLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Satış kaydı',
    )
    service_record = models.ForeignKey(
        'services.ServiceRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Servis kaydı',
    )
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Kaydeden',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stok hareketi'
        verbose_name_plural = 'Stok hareketleri'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.delta >= 0 else ''
        return f'{self.material.name} {sign}{self.delta} ({self.get_reason_display()})'


class SolutionPartner(models.Model):
    brand = models.ForeignKey(
        BusinessBrand,
        on_delete=models.PROTECT,
        related_name='solution_partners',
        verbose_name='Marka / firma',
    )
    name = models.CharField(max_length=120, verbose_name='Ad')
    partner_type = models.ForeignKey(
        SolutionPartnerType,
        on_delete=models.PROTECT,
        related_name='partners',
        null=True,
        blank=True,
        verbose_name='Tür',
    )
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Telefon')
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name='Not')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Çözüm ortağı'
        verbose_name_plural = 'Çözüm ortakları'
        ordering = ['name']

    def __str__(self):
        type_name = self.partner_type.name if self.partner_type else 'Türsüz'
        return f'{self.name} ({type_name})'


class CashAccount(models.Model):
    TYPE_CASH = 'cash'
    TYPE_BANK = 'bank'
    TYPE_POS = 'pos'
    TYPE_CHOICES = (
        (TYPE_CASH, 'Nakit kasa'),
        (TYPE_BANK, 'Banka'),
        (TYPE_POS, 'POS'),
    )

    name = models.CharField(max_length=80, verbose_name='Hesap adı')
    account_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_CASH,
        verbose_name='Tür',
    )
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Açılış bakiyesi (₺)',
    )
    is_default = models.BooleanField(default=False, verbose_name='Varsayılan')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kasa / banka hesabı'
        verbose_name_plural = 'Kasa / banka hesapları'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return self.name


class SupplierPayable(models.Model):
    brand = models.ForeignKey(
        'BusinessBrand',
        on_delete=models.CASCADE,
        related_name='supplier_payables',
        verbose_name='Marka',
    )
    supplier_name = models.CharField(max_length=120, verbose_name='Tedarikçi')
    invoice_ref = models.CharField(max_length=80, blank=True, verbose_name='Fatura / referans')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Tutar (₺)')
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Ödenen (₺)',
    )
    due_date = models.DateField(null=True, blank=True, verbose_name='Vade')
    notes = models.TextField(blank=True, verbose_name='Not')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tedarikçi borcu'
        verbose_name_plural = 'Tedarikçi borçları'
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return f'{self.supplier_name} — {self.amount} ₺'

    @property
    def remaining(self):
        from decimal import Decimal
        return (self.amount or Decimal('0')) - (self.paid_amount or Decimal('0'))


class OperationalProject(models.Model):
    STATUS_PLANNING = 'planning'
    STATUS_ACTIVE = 'active'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (STATUS_PLANNING, 'Planlama'),
        (STATUS_ACTIVE, 'Aktif'),
        (STATUS_DONE, 'Tamamlandı'),
        (STATUS_CANCELLED, 'İptal'),
    )

    name = models.CharField(max_length=160, verbose_name='Proje adı')
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operational_projects',
        verbose_name='Müşteri',
    )
    sales_lead = models.ForeignKey(
        'sales_leads.SalesLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operational_projects',
        verbose_name='Satış kaydı',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name='Durum',
    )
    start_date = models.DateField(null=True, blank=True, verbose_name='Başlangıç')
    end_date = models.DateField(null=True, blank=True, verbose_name='Bitiş')
    notes = models.TextField(blank=True, verbose_name='Not')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Operasyon projesi'
        verbose_name_plural = 'Operasyon projeleri'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class InstallationScheduleEntry(models.Model):
    TYPE_INSTALLATION = 'installation'
    TYPE_SERVICE = 'service'
    TYPE_CHOICES = (
        (TYPE_INSTALLATION, 'Montaj'),
        (TYPE_SERVICE, 'Servis'),
    )

    scheduled_date = models.DateField(verbose_name='Gün', db_index=True)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='installation_schedule_entries',
        verbose_name='Müşteri',
    )
    sales_lead = models.ForeignKey(
        'sales_leads.SalesLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installation_schedule_entries',
        verbose_name='Satış kaydı',
    )
    operational_project = models.ForeignKey(
        'core_settings.OperationalProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_entries',
        verbose_name='Proje kartı',
    )
    team = models.ForeignKey(
        'core_settings.ServiceTeam',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installation_schedule_entries',
        verbose_name='Ekip',
    )
    work_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_INSTALLATION,
        verbose_name='İş tipi',
    )
    notes = models.TextField(blank=True, verbose_name='Montaj notları')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Sıra')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Montaj programı kaydı'
        verbose_name_plural = 'Montaj programı kayıtları'
        ordering = ['scheduled_date', 'sort_order', 'pk']

    def __str__(self):
        return f'{self.scheduled_date:%d.%m.%Y} — {self.customer.name}'


class TimeEntry(models.Model):
    entry_date = models.DateField(verbose_name='Tarih')
    hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Saat')
    description = models.CharField(max_length=200, verbose_name='Açıklama')
    billable = models.BooleanField(default=True, verbose_name='Faturalanabilir')
    personnel = models.ForeignKey(
        'core_settings.ServicePersonnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_entries',
        verbose_name='Personel',
    )
    sales_lead = models.ForeignKey(
        'sales_leads.SalesLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_entries',
        verbose_name='Satış / proje',
    )
    operational_project = models.ForeignKey(
        OperationalProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_entries',
        verbose_name='Proje',
    )
    invoiced = models.BooleanField(default=False, verbose_name='Faturalandı')
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_entries',
        verbose_name='Kaydeden',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Zaman kaydı'
        verbose_name_plural = 'Zaman kayıtları'
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f'{self.entry_date} — {self.hours} saat'


class EExportSettings(models.Model):
    """Mali müşavir / dış aktarım notları — tekil."""

    advisor_note = models.TextField(blank=True, verbose_name='Mali müşavir notu')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dış aktarım ayarları'
        verbose_name_plural = 'Dış aktarım ayarları'

    def __str__(self):
        return 'Dış aktarım ayarları'


class Subscription(models.Model):
    STATUS_TRIALING = 'trialing'
    STATUS_ACTIVE = 'active'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = (
        (STATUS_TRIALING, 'Deneme'),
        (STATUS_ACTIVE, 'Aktif'),
        (STATUS_PAST_DUE, 'Ödeme gecikmiş'),
        (STATUS_CANCELED, 'İptal'),
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Abonelik sahibi',
    )
    plan = models.ForeignKey(
        'Plan',
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Plan',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_TRIALING,
        verbose_name='Durum',
    )
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Dönem bitişi',
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Ödeme sağlayıcı kimliği',
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Deneme bitişi',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Abonelik'
        verbose_name_plural = 'Abonelikler'
        ordering = ['-updated_at', '-pk']
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.user_id} — {self.plan.name} ({self.get_status_display()})'


class BillingInvoice(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name='Kullanıcı',
    )
    plan = models.ForeignKey(
        'core_settings.Plan',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='Plan',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Tutar')
    status = models.CharField(
        max_length=20,
        choices=(('paid', 'Ödendi'), ('pending', 'Bekliyor')),
        default='paid',
        verbose_name='Durum',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma tarihi')

    class Meta:
        verbose_name = 'Fatura'
        verbose_name_plural = 'Faturalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.plan.name} ({self.amount} ₺)'

