"""Paylaşılan test yardımcıları — marka oturumu ve modül listesi."""

from __future__ import annotations

from common.brand_scope import SESSION_ACTIVE_BRAND, create_brand_for_user
from common.kobi_lean_preset import lean_kobi_slugs
from core_settings.models import SiteSettings


def ensure_site_settings(site_name: str = 'Test Site') -> SiteSettings:
    settings, _ = SiteSettings.objects.get_or_create(defaults={'site_name': site_name})
    if settings.site_name != site_name:
        settings.site_name = site_name
        settings.save(update_fields=['site_name'])
    return settings


def _split_modules_particles(slugs: list[str]) -> tuple[list[str], list[str]]:
    modules: list[str] = []
    particles: list[str] = []
    for slug in slugs:
        if slug.startswith('p.'):
            particles.append(slug)
        else:
            modules.append(slug)
    return modules, particles


def ensure_test_plan(slugs: list[str]):
    from core_settings.models import Plan

    modules, particles = _split_modules_particles(slugs)
    plan, created = Plan.objects.get_or_create(
        name='Test Full Plan',
        defaults={
            'price': 0,
            'max_hq_brands': 50,
            'max_dealer_panels': 50,
            'max_users_per_brand': 200,
            'max_customers_per_brand': 10000,
            'included_module_slugs': modules,
            'included_particle_slugs': particles,
        },
    )
    if not created:
        plan.included_module_slugs = modules
        plan.included_particle_slugs = particles
        plan.save(update_fields=['included_module_slugs', 'included_particle_slugs'])
    return plan


def ensure_brand_for_user(user, brand_name: str = 'Test Marka'):
    ensure_site_settings()
    return create_brand_for_user(user, brand_name)


def default_test_brand():
    """Test verisi için varsayılan marka (NOT NULL brand FK)."""
    from django.contrib.auth import get_user_model
    from core_settings.models import BusinessBrand

    brand = BusinessBrand.objects.filter(is_default=True, is_active=True).first()
    if brand:
        return brand
    User = get_user_model()
    owner = User.objects.filter(is_superuser=False).order_by('pk').first()
    if owner is None:
        owner = User.objects.create_user(username='_test_brand_owner', password='test1234')
    return ensure_brand_for_user(owner, 'Test Varsayılan Marka')


def set_user_modules(user, slugs) -> None:
    slug_list = list(slugs)
    plan = ensure_test_plan(slug_list)
    user.plan = plan
    user.enabled_module_slugs = slug_list
    user.save(update_fields=['plan', 'enabled_module_slugs'])


def login_with_brand(client, user, brand=None):
    """Giriş + aktif marka oturumu."""
    if brand is None:
        brand = ensure_brand_for_user(user)
    client.force_login(user)
    session = client.session
    session[SESSION_ACTIVE_BRAND] = brand.pk
    session.save()
    return brand


def lean_modules_without(*omit: str) -> list[str]:
    return [s for s in lean_kobi_slugs() if s not in omit]
