"""Plan ve abonelik sahibi bazlı modül çözümlemesi."""

from __future__ import annotations

from common.module_catalog import MODULES, default_enabled_module_slugs, module_by_slug
from common.module_particles import default_enabled_particle_slugs, resolve_particle_slug


def _known_module_slugs() -> set[str]:
    return {m['slug'] for m in MODULES if not m['slug'].startswith('agency_')}


def normalize_module_slug_list(raw) -> list[str]:
    known = _known_module_slugs()
    default = [s for s in default_enabled_module_slugs() if s in known]
    if not raw:
        return default
    out: list[str] = []
    for slug in raw:
        if not isinstance(slug, str):
            continue
        slug = slug.strip()
        if slug.startswith('p.') or slug.startswith('agency_'):
            continue
        if slug in known and slug not in out:
            out.append(slug)
    return out or default


def normalize_particle_slug_list(raw) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for slug in raw:
        if not isinstance(slug, str):
            continue
        resolved = resolve_particle_slug(slug.strip())
        if resolved and resolved not in out:
            out.append(resolved)
    return out


def plan_included_modules(plan) -> list[str]:
    if plan is None:
        return normalize_module_slug_list(None)
    stored = getattr(plan, 'included_module_slugs', None) or []
    return normalize_module_slug_list(stored)


def plan_included_particles(plan) -> list[str]:
    if plan is None:
        return []
    stored = getattr(plan, 'included_particle_slugs', None) or []
    explicit = normalize_particle_slug_list(stored)
    if explicit:
        return explicit
    particles: list[str] = []
    for mod_slug in plan_included_modules(plan):
        mod = module_by_slug(mod_slug)
        if not mod:
            continue
        for pslug in mod.get('particle_slugs', ()):
            if pslug not in particles:
                particles.append(pslug)
    return particles


def owner_selected_modules(owner) -> list[str]:
    if owner is None:
        return normalize_module_slug_list(None)
    plan_modules = set(plan_included_modules(owner.active_plan))
    selected = getattr(owner, 'enabled_module_slugs', None) or []
    if selected:
        return [s for s in normalize_module_slug_list(selected) if s in plan_modules]
    return [s for s in plan_modules]


def owner_selected_particles(owner) -> list[str]:
    if owner is None:
        return []
    plan_particles = set(plan_included_particles(owner.active_plan))
    raw = getattr(owner, 'enabled_module_slugs', None) or []
    explicit = normalize_particle_slug_list(raw)
    if explicit:
        return [s for s in explicit if s in plan_particles]
    return [s for s in plan_particles]


def clamp_owner_modules_to_plan(owner, *, save: bool = True) -> None:
    """Plan değişince plan dışı modülleri kaldır."""
    if owner is None or owner.is_superuser:
        return
    allowed_modules = set(plan_included_modules(owner.active_plan))
    allowed_particles = set(plan_included_particles(owner.active_plan))
    raw = list(getattr(owner, 'enabled_module_slugs', None) or [])
    if not raw:
        return
    cleaned: list[str] = []
    for slug in raw:
        if slug.startswith('p.'):
            resolved = resolve_particle_slug(slug)
            if resolved in allowed_particles:
                cleaned.append(resolved)
        elif slug in allowed_modules:
            cleaned.append(slug)
    if cleaned != raw:
        owner.enabled_module_slugs = cleaned
        if save:
            owner.save(update_fields=['enabled_module_slugs'])


def subscription_owner_for_user(user, *, request=None):
    from common.brand_team import is_subscription_owner, subscription_owner_for_brand
    from common.brand_scope import get_active_brand_id, user_memberships
    from common.module_context import current_module_request

    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return None

    if request is None:
        request = current_module_request()

    brand_id = get_active_brand_id(request) if request else None
    if not brand_id:
        mem = (
            user_memberships(user).filter(is_default=True).select_related('brand').first()
            or user_memberships(user).select_related('brand').first()
        )
        brand_id = mem.brand_id if mem else None

    if brand_id:
        from core_settings.models import BusinessBrand

        brand = BusinessBrand.objects.filter(pk=brand_id).first()
        if brand:
            return subscription_owner_for_brand(brand) or user

    if is_subscription_owner(user):
        return user
    return None


def default_plan_module_seed() -> list[str]:
    return normalize_module_slug_list(None)
