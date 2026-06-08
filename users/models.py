from django.contrib.auth.models import AbstractUser
from django.db import models

from .display import humanize_username, is_rbac_test_username


class Permission(models.Model):
    KIND_ACCESS = 'access'
    KIND_ACTION = 'action'
    KIND_CHOICES = [
        (KIND_ACCESS, 'Modül erişimi'),
        (KIND_ACTION, 'Fonksiyon izni'),
    ]

    codename = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    module = models.CharField(max_length=40, default='Genel')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_ACTION)
    description = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['kind', 'module', 'sort_order', 'name']
        verbose_name = 'İzin'
        verbose_name_plural = 'İzinler'

    def __str__(self):
        return self.name

    @property
    def is_access(self):
        return self.kind == self.KIND_ACCESS


class Role(models.Model):
    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False, verbose_name='Sistem rolü')
    owner = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='owned_roles',
        verbose_name='Oluşturan abonelik sahibi',
    )
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    class Meta:
        ordering = ['name']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roller'

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        verbose_name='Rol',
    )
    plan = models.ForeignKey(
        'core_settings.Plan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Abonelik planı',
    )
    enabled_module_slugs = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Aktif modüller',
        help_text='Abonelik planı tavanı içinde açık modüller.',
    )

    @property
    def active_plan(self):
        from core_settings.billing.subscription import get_active_subscription, refresh_subscription_status

        refresh_subscription_status(self)
        sub = get_active_subscription(self)
        if sub and sub.plan_id:
            return sub.plan
        if self.plan:
            return self.plan
        from core_settings.models import Plan
        free_plan = Plan.objects.filter(price=0).first()
        if free_plan:
            return free_plan
        class FallbackPlan:
            name = "Ücretsiz Plan"
            max_brands = 1
            max_hq_brands = 1
            max_dealer_panels = 0
            max_users_per_brand = 3
            max_customers_per_brand = 100
            included_module_slugs = []
            included_particle_slugs = []
            brands_limit_display = "1"
            users_limit_display = "3"
            customers_limit_display = "100"

            def module_count(self):
                return 4
        return FallbackPlan()

    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'

    def __str__(self):
        role_name = self.role.name if self.role_id else 'Rol yok'
        return f"{self.username} ({role_name})"

    @property
    def display_name(self):
        full = self.get_full_name().strip()
        if full:
            return full
        role_name = self.role.name if self.role_id else ''
        label = humanize_username(self.username, role_name=role_name)
        if label != self.username:
            return label
        return self.username

    @property
    def is_rbac_test_account(self):
        return is_rbac_test_username(self.username)

    @property
    def list_subtitle(self):
        """Admin listeleri — teknik kullanıcı adı yerine rol/e-posta."""
        parts = [self.role_label]
        if self.email:
            parts.append(self.email)
        return ' · '.join(parts)

    @property
    def initials(self):
        parts = self.display_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.display_name[:2].upper()

    @property
    def role_label(self):
        if self.is_superuser:
            return 'Süper Admin'
        if self.role_id:
            return self.role.name
        return 'Rol atanmadı'

    def get_permission_codenames(self):
        if self.is_superuser:
            return set(Permission.objects.values_list('codename', flat=True))
        if not self.role_id:
            return set()
        return set(self.role.permissions.values_list('codename', flat=True))

    def has_perm_codename(self, codename):
        if self.is_superuser:
            return True
        if not codename:
            return True
        if not self.role_id:
            return False
        return self.role.permissions.filter(codename=codename).exists()

    def has_any_perm_codename(self, *codenames):
        if self.is_superuser:
            return True
        codes = {c for c in codenames if c}
        if not codes:
            return True
        if not self.role_id:
            return False
        return self.role.permissions.filter(codename__in=codes).exists()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='profiles/', null=True, blank=True, verbose_name='Profil fotoğrafı')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Telefon')
    job_title = models.CharField(max_length=120, blank=True, verbose_name='Ünvan')
    bio = models.TextField(blank=True, verbose_name='Hakkında')

    class Meta:
        verbose_name = 'Kullanıcı profili'
        verbose_name_plural = 'Kullanıcı profilleri'

    def __str__(self):
        return self.user.display_name

    def subtitle(self):
        if self.job_title:
            return self.job_title
        return self.user.role_label


class UserNotification(models.Model):
    LEVEL_INFO = 'info'
    LEVEL_SUCCESS = 'success'
    LEVEL_WARNING = 'warning'
    LEVEL_CHOICES = (
        (LEVEL_INFO, 'Bilgi'),
        (LEVEL_SUCCESS, 'Başarılı'),
        (LEVEL_WARNING, 'Uyarı'),
    )

    SOURCE_SYSTEM = 'system'
    SOURCE_PAYROLL = 'payroll'
    SOURCE_RECEIVABLES = 'receivables'
    SOURCE_SERVICE = 'service'
    SOURCE_CHOICES = (
        (SOURCE_SYSTEM, 'Sistem'),
        (SOURCE_PAYROLL, 'Maaş'),
        (SOURCE_RECEIVABLES, 'Alacak'),
        (SOURCE_SERVICE, 'Servis'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_SYSTEM)
    dedupe_key = models.CharField(max_length=120, blank=True, db_index=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bildirim'
        verbose_name_plural = 'Bildirimler'
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.title}'


class ImpersonationAudit(models.Model):
    ACTION_START = 'start'
    ACTION_STOP = 'stop'
    ACTION_CHOICES = (
        (ACTION_START, 'Başlangıç'),
        (ACTION_STOP, 'Bitiş'),
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='impersonation_audits_as_actor',
    )
    target = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='impersonation_audits_as_target',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Impersonate kaydı'
        verbose_name_plural = 'Impersonate kayıtları'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['actor', '-created_at']),
        ]

    def __str__(self):
        return f'{self.action} {self.actor_id}→{self.target_id}'


class PlatformAuditLog(models.Model):
    ACTION_BRAND_INSPECT = 'brand_inspect'
    ACTION_BACKUP_EXPORT = 'backup_export'
    ACTION_BRAND_BACKUP_EXPORT = 'brand_backup_export'
    ACTION_FACTORY_RESET = 'factory_reset'
    ACTION_BRAND_DELETE = 'brand_delete'
    ACTION_CHOICES = (
        (ACTION_BRAND_INSPECT, 'Marka inceleme'),
        (ACTION_BACKUP_EXPORT, 'Tam yedek indirme'),
        (ACTION_BRAND_BACKUP_EXPORT, 'Marka yedeği indirme'),
        (ACTION_FACTORY_RESET, 'Fabrika sıfırlama'),
        (ACTION_BRAND_DELETE, 'Marka silme'),
    )

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_audits',
    )
    brand = models.ForeignKey(
        'core_settings.BusinessBrand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_audits',
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_audits_as_target',
    )
    detail = models.CharField(max_length=500, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Platform denetim kaydı'
        verbose_name_plural = 'Platform denetim kayıtları'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f'{self.get_action_display()} — {self.actor_id}'
