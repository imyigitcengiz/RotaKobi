"""Marka / abonelik sahibi ekip yönetimi."""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from core_settings.models import BrandMembership, BusinessBrand


def production_users_queryset():
    from django.contrib.auth import get_user_model

    return get_user_model().objects.select_related('role', 'plan').exclude(
        username__startswith='_rbac_',
    )


def owned_brand_ids(user) -> list[int]:
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return list(
            BusinessBrand.objects.filter(is_active=True).values_list('pk', flat=True)
        )
    return list(
        BrandMembership.objects.filter(
            user=user,
            role=BrandMembership.ROLE_OWNER,
            brand__is_active=True,
        ).values_list('brand_id', flat=True)
    )


def can_manage_brand_team(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return BrandMembership.objects.filter(
        user=user,
        role=BrandMembership.ROLE_OWNER,
        brand__is_active=True,
    ).exists()


def is_subscription_owner(user) -> bool:
    if not user or not user.is_authenticated or user.is_superuser:
        return False
    return BrandMembership.objects.filter(
        user=user,
        role=BrandMembership.ROLE_OWNER,
        brand__panel_kind=BusinessBrand.PANEL_HQ,
        brand__is_active=True,
    ).exists()


def subscription_owners_queryset() -> QuerySet:
    owner_ids = BrandMembership.objects.filter(
        role=BrandMembership.ROLE_OWNER,
        brand__is_active=True,
    ).values_list('user_id', flat=True)
    return (
        production_users_queryset()
        .filter(is_superuser=False)
        .filter(Q(pk__in=owner_ids) | Q(plan__isnull=False))
        .distinct()
        .annotate(
            team_brand_count=Count(
                'brand_memberships',
                filter=Q(brand_memberships__role=BrandMembership.ROLE_OWNER),
                distinct=True,
            ),
        )
        .order_by('-date_joined')
    )


def team_users_queryset(manager, *, brand_id: int | None = None) -> QuerySet:
    brand_ids = owned_brand_ids(manager)
    if brand_id:
        if brand_id not in brand_ids:
            return production_users_queryset().none()
        brand_ids = [brand_id]

    if not brand_ids:
        return production_users_queryset().none()

    user_ids = (
        BrandMembership.objects.filter(brand_id__in=brand_ids)
        .values_list('user_id', flat=True)
        .distinct()
    )
    return (
        production_users_queryset()
        .filter(pk__in=user_ids)
        .exclude(is_superuser=True)
        .order_by('-date_joined')
    )


def manager_can_edit_user(manager, target) -> bool:
    if not manager or not target or not manager.is_authenticated:
        return False
    if manager.is_superuser:
        return True
    if target.is_superuser:
        return False
    if not can_manage_brand_team(manager):
        return False
    managed_ids = set(team_users_queryset(manager).values_list('pk', flat=True))
    return target.pk in managed_ids


BRAND_FORBIDDEN_ROLE_SLUGS = frozenset({'admin'})
BRAND_FORBIDDEN_PERMISSION_CODENAMES = frozenset({'tools.backup'})


def brand_assignable_permissions_queryset():
    from users.models import Permission

    return Permission.objects.exclude(codename__in=BRAND_FORBIDDEN_PERMISSION_CODENAMES)


def sanitize_brand_permission_ids(permission_ids: list[int]) -> list[int]:
    allowed = set(
        brand_assignable_permissions_queryset()
        .filter(pk__in=permission_ids)
        .values_list('pk', flat=True)
    )
    return [pid for pid in permission_ids if pid in allowed]


def assignable_roles_queryset(manager):
    from users.models import Role

    if manager.is_superuser:
        return Role.objects.order_by('name')
    return (
        Role.objects.filter(Q(is_system=True) | Q(owner=manager))
        .exclude(slug__in=BRAND_FORBIDDEN_ROLE_SLUGS)
        .order_by('name')
    )


def role_assignable_by_brand_manager(manager, role) -> bool:
    if not role:
        return False
    if manager.is_superuser:
        return True
    if role.slug in BRAND_FORBIDDEN_ROLE_SLUGS:
        return False
    return role.is_system or role.owner_id == manager.pk


def owned_brands_queryset(manager):
    ids = owned_brand_ids(manager)
    return BusinessBrand.objects.filter(pk__in=ids, is_active=True).order_by('name')


def attach_user_to_brand(
    user,
    brand: BusinessBrand,
    *,
    membership_role: str = BrandMembership.ROLE_MEMBER,
    is_default: bool = False,
):
    mem, created = BrandMembership.objects.get_or_create(
        user=user,
        brand=brand,
        defaults={
            'role': membership_role,
            'is_default': is_default,
        },
    )
    if not created:
        mem.role = membership_role
        if is_default:
            mem.is_default = True
        mem.save(update_fields=['role', 'is_default'])
    if is_default:
        BrandMembership.objects.filter(user=user).exclude(pk=mem.pk).update(is_default=False)
    return mem


class PlanLimitExceeded(Exception):
    def __init__(self, message: str, *, status_code: int = 402):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def check_team_user_limit(owner, brand: BusinessBrand) -> None:
    plan = owner.active_plan
    count = BrandMembership.objects.filter(brand=brand).count()
    if not owner.is_superuser and count >= plan.max_users_per_brand:
        raise PlanLimitExceeded(
            f'"{brand.name}" panelinde kullanıcı limitine ulaşıldı '
            f'({count}/{plan.max_users_per_brand}). Planınızı yükseltin.',
            status_code=403,
        )


def subscription_owner_for_brand(brand: BusinessBrand):
    """Marka / bayi paneli için abonelik sahibi (HQ owner)."""
    target_brand = brand
    if brand.panel_kind == BusinessBrand.PANEL_DEALER and brand.parent_brand_id:
        target_brand = brand.parent_brand
    mem = (
        BrandMembership.objects.filter(
            user__is_superuser=False,
            brand=target_brand,
            role=BrandMembership.ROLE_OWNER,
            brand__is_active=True,
        )
        .select_related('user')
        .order_by('joined_at')
        .first()
    )
    return mem.user if mem else None


def check_customer_limit(owner, brand: BusinessBrand) -> None:
    from customers.models import Customer

    if not owner or owner.is_superuser:
        return
    plan = owner.active_plan
    count = Customer.objects.filter(brand_id=brand.pk).count()
    if count >= plan.max_customers_per_brand:
        raise PlanLimitExceeded(
            f'"{brand.name}" panelinde müşteri limitine ulaşıldı '
            f'({count}/{plan.max_customers_per_brand}). '
            f'Planınızı yükseltmek için Abonelik sayfasını ziyaret edin.',
            status_code=402,
        )


def check_customer_limit_for_request(request, *, brand: BusinessBrand | None = None):
    from common.brand_scope import get_active_brand
    from common.middleware import _is_api_request
    from django.http import JsonResponse

    brand = brand or get_active_brand(request)
    if not brand:
        return None
    owner = subscription_owner_for_brand(brand)
    if not owner:
        return None
    try:
        check_customer_limit(owner, brand)
    except PlanLimitExceeded as exc:
        if _is_api_request(request):
            return JsonResponse(
                {'ok': False, 'error': 'plan_limit', 'detail': exc.message},
                status=exc.status_code,
            )
        raise ValueError(exc.message) from exc
    return None
