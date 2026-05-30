"""Kurulum modül + parçacık çözümlemesi."""

from __future__ import annotations

from django.urls import NoReverseMatch, reverse

from common.module_catalog import (
    DEFAULT_PRIMARY_VERTICAL,
    MODULE_GATE_EXEMPT_PREFIXES,
    MODULE_KIND_APP,
    MODULE_KIND_INTEGRATION,
    MODULE_KIND_ROADMAP,
    MODULE_STATUS_ACTIVE,
    MODULE_STATUS_BETA,
    MODULE_STATUS_ROADMAP,
    MODULES,
    VERTICALS,
    default_enabled_module_slugs,
    module_by_slug,
    route_prefix_to_module_slug,
    vertical_by_slug,
)
from common.module_particles import (
    LEGACY_MODULE_ALIASES,
    PARTICLE_CATEGORIES,
    PARTICLES,
    category_by_slug,
    default_enabled_particle_slugs,
    particle_by_slug,
    particle_route_prefixes,
    vertical_preset_all_slugs,
)


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix)


def _site_settings():
    from core_settings.models import SiteSettings
    return SiteSettings.objects.first()


def _normalize_catalog_slugs(raw: list | tuple | None) -> list[str]:
    if not raw:
        return default_enabled_module_slugs() + default_enabled_particle_slugs()

    known_modules = {m['slug'] for m in MODULES}
    known_particles = {p['slug'] for p in PARTICLES}
    known = known_modules | known_particles
    out: list[str] = []

    for slug in raw:
        if slug in LEGACY_MODULE_ALIASES:
            for alias in LEGACY_MODULE_ALIASES[slug]:
                if alias not in out:
                    out.append(alias)
            continue
        if slug in known and slug not in out:
            out.append(slug)

    if not out:
        return default_enabled_module_slugs() + default_enabled_particle_slugs()

    # Eski kurulumlar: modül listesi var, parçacık yok → profile göre tamamla
    if not any(s.startswith('p.') for s in out):
        settings = _site_settings()
        vertical = DEFAULT_PRIMARY_VERTICAL
        if settings and settings.primary_vertical_slug:
            v = settings.primary_vertical_slug.strip()
            if vertical_by_slug(v):
                vertical = v
        for slug in vertical_preset_all_slugs(vertical):
            if slug not in out:
                out.append(slug)

    return out


def get_primary_vertical_slug() -> str:
    settings = _site_settings()
    if settings and settings.primary_vertical_slug:
        slug = settings.primary_vertical_slug.strip()
        if vertical_by_slug(slug):
            return slug
    return DEFAULT_PRIMARY_VERTICAL


def get_enabled_catalog_slugs() -> list[str]:
    settings = _site_settings()
    if settings and settings.enabled_module_slugs:
        return _normalize_catalog_slugs(settings.enabled_module_slugs)
    return _normalize_catalog_slugs(None)


def get_enabled_module_slugs() -> list[str]:
    known = {m['slug'] for m in MODULES}
    return [s for s in get_enabled_catalog_slugs() if s in known]


def get_enabled_particle_slugs() -> list[str]:
    known = {p['slug'] for p in PARTICLES}
    return [s for s in get_enabled_catalog_slugs() if s in known]


def is_module_enabled(slug: str) -> bool:
    if slug in LEGACY_MODULE_ALIASES:
        return all(is_module_enabled(s) for s in LEGACY_MODULE_ALIASES[slug])
    return slug in get_enabled_module_slugs()


def is_particle_enabled(slug: str) -> bool:
    return slug in get_enabled_particle_slugs()


def is_particle_enabled_for_nav(slug: str) -> bool:
    """Parçacık açık ve üst modül kurulu."""
    p = particle_by_slug(slug)
    if not p or not is_particle_enabled(slug):
        return False
    parent = p.get('parent_module')
    if parent == 'agency_suite':
        return is_module_enabled('agency_suite') or is_particle_enabled('p.agency.retainer')
    if parent and not is_module_enabled(parent):
        return False
    return True


def resolve_path_module_slug(path: str) -> str | None:
    if any(_path_matches(path, p) for p in MODULE_GATE_EXEMPT_PREFIXES):
        return None
    for prefix, slug in route_prefix_to_module_slug():
        if _path_matches(path, prefix):
            return slug
    return None


def resolve_path_particle_slug(path: str) -> str | None:
    for prefix, slug in particle_route_prefixes():
        if _path_matches(path, prefix):
            return slug
    return None


def user_can_access_module(user, module: dict) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    required_any = module.get('requires_any_perm')
    if required_any:
        return user.has_any_perm_codename(*required_any)
    perm = module.get('access_perm')
    if not perm:
        return False
    return user.has_perm_codename(perm)


def module_available_for_nav(user, slug: str) -> bool:
    if not is_module_enabled(slug):
        return False
    mod = module_by_slug(slug)
    if not mod or mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
        return False
    return user_can_access_module(user, mod)


def integration_available_for_nav(user, slug: str) -> bool:
    return module_available_for_nav(user, slug)


def build_modules_nav_flags(user) -> dict[str, bool]:
    slugs = {m['slug'] for m in MODULES}
    return {slug: module_available_for_nav(user, slug) for slug in slugs}


def build_particles_nav_flags(user) -> dict[str, bool]:
    return {p['slug']: is_particle_enabled_for_nav(p['slug']) for p in PARTICLES}


def build_particles_nav_short(user) -> dict[str, bool]:
    """Şablonlar için kısa anahtarlar: contact_teams, accounting_payroll…"""
    mapping = {
        'p.contact.customers': 'contact_customers',
        'p.contact.firms': 'contact_firms',
        'p.contact.teams': 'contact_teams',
        'p.contact.freelancers': 'contact_freelancers',
        'p.accounting.personnel': 'accounting_personnel',
        'p.accounting.payroll': 'accounting_payroll',
        'p.accounting.finance': 'accounting_finance',
        'p.accounting.sales': 'accounting_sales',
        'p.agency.retainer': 'agency_retainer',
        'p.outreach.campaigns': 'outreach_campaigns',
    }
    flags = build_particles_nav_flags(user)
    return {short: flags.get(full, False) for full, short in mapping.items()}


def _module_hub_url(module: dict) -> str | None:
    url_name = module.get('hub_url_name')
    if not url_name:
        return None
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def _status_label(status: str) -> str:
    return {
        MODULE_STATUS_ACTIVE: 'Aktif',
        MODULE_STATUS_BETA: 'Beta',
        MODULE_STATUS_ROADMAP: 'Yakında',
    }.get(status, status)


def _kind_label(kind: str) -> str:
    return {
        MODULE_KIND_APP: 'Uygulama',
        MODULE_KIND_INTEGRATION: 'Entegrasyon',
        MODULE_KIND_ROADMAP: 'Yol haritası',
    }.get(kind, kind)


def build_module_record(user, module: dict, *, installed: bool) -> dict:
    record = dict(module)
    record['installed'] = installed
    record['status_label'] = _status_label(module['status'])
    record['kind_label'] = _kind_label(module.get('kind', MODULE_KIND_APP))
    record['hub_url'] = (
        _module_hub_url(module)
        if installed and module['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA)
        else None
    )
    record['user_has_access'] = user_can_access_module(user, module) if installed else False
    record['can_open'] = bool(record['hub_url'] and record['user_has_access'])
    record['can_toggle'] = (
        module['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA)
        and module.get('can_disable', True)
    )
    return record


def build_particle_record(particle: dict, *, enabled: bool) -> dict:
    record = dict(particle)
    record['enabled'] = enabled
    cat = category_by_slug(particle['category'])
    record['category_name'] = cat['name'] if cat else particle['category']
    record['category_icon'] = cat['icon'] if cat else 'puzzle'
    parent = module_by_slug(particle.get('parent_module', ''))
    record['parent_module_name'] = parent['name'] if parent else '—'
    record['can_toggle'] = True
    return record


def build_module_hub_context(user, *, vertical_filter: str | None = None, query: str = '') -> dict:
    enabled = set(get_enabled_catalog_slugs())
    primary = get_primary_vertical_slug()
    vf = None
    if vertical_filter and vertical_filter != 'all':
        vf = vertical_filter if vertical_by_slug(vertical_filter) else None

    q = (query or '').strip().lower()
    modules = []
    for mod in MODULES:
        if vf and vf not in mod.get('verticals', ()):
            continue
        if q:
            hay = f"{mod['name']} {mod['summary']}".lower()
            if q not in hay:
                continue
        installed = mod['slug'] in enabled and mod['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA)
        modules.append(build_module_record(user, mod, installed=installed))

    modules.sort(key=lambda m: (
        m['kind'] == MODULE_KIND_INTEGRATION,
        m['status'] != MODULE_STATUS_ACTIVE,
        m['sort'],
        m['name'],
    ))

    particles = []
    for p in PARTICLES:
        if vf and vf not in p.get('vertical_tags', ()):
            continue
        if q:
            hay = f"{p['name']} {p['summary']}".lower()
            if q not in hay:
                continue
        particles.append(build_particle_record(p, enabled=p['slug'] in enabled))

    particles.sort(key=lambda p: (p['category'], p['sort'], p['name']))

    particle_groups = []
    for cat_row in PARTICLE_CATEGORIES:
        cat_slug, cat_name, cat_icon = cat_row
        items = [p for p in particles if p['category'] == cat_slug]
        if items:
            particle_groups.append({'slug': cat_slug, 'name': cat_name, 'icon': cat_icon, 'items': items})

    verticals = [{'slug': 'all', 'name': 'Tüm sektörler', 'tagline': '', 'icon': 'layout-grid', 'color': 'slate'}]
    verticals.extend(v for v in (vertical_by_slug(row[0]) for row in VERTICALS) if v)

    apps = [m for m in modules if m.get('kind') == MODULE_KIND_APP and m['status'] != MODULE_STATUS_ROADMAP]
    integrations = [m for m in modules if m.get('kind') == MODULE_KIND_INTEGRATION]
    roadmap = [m for m in modules if m['status'] == MODULE_STATUS_ROADMAP]

    preset_slugs = vertical_preset_all_slugs(primary)

    return {
        'module_verticals': verticals,
        'module_vertical_filter': vertical_filter or 'all',
        'module_primary_vertical': primary,
        'module_catalog_items': modules,
        'module_catalog_apps': apps,
        'module_catalog_integrations': integrations,
        'module_catalog_roadmap': roadmap,
        'module_particle_groups': particle_groups,
        'module_particles': particles,
        'module_installed_count': sum(1 for m in apps if m['installed']) + sum(1 for p in particles if p['enabled']),
        'module_roadmap_count': len(roadmap),
        'module_search_query': query,
        'vertical_preset_slugs': preset_slugs,
    }


def panel_section_visible(section_key: str) -> bool:
    mapping = {
        'contact': 'contact',
        'services': 'services',
        'accounting': 'accounting',
        'outreach': 'outreach',
        'agency': 'agency_suite',
    }
    slug = mapping.get(section_key)
    if not slug:
        return True
    return is_module_enabled(slug)


def recommended_modules_for_vertical(vertical_slug: str) -> list[dict]:
    preset = set(vertical_preset_all_slugs(vertical_slug))
    return [
        dict(m) for m in MODULES
        if m['slug'] in preset and m['status'] in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA)
    ]


def recommended_particles_for_vertical(vertical_slug: str) -> list[dict]:
    preset = set(vertical_preset_all_slugs(vertical_slug))
    return [dict(p) for p in PARTICLES if p['slug'] in preset]


def apply_vertical_preset(vertical_slug: str) -> list[str]:
    slugs = list(vertical_preset_all_slugs(vertical_slug))
    settings = _site_settings()
    if not settings:
        from core_settings.models import SiteSettings
        settings = SiteSettings.objects.create()
    settings.primary_vertical_slug = vertical_slug
    settings.enabled_module_slugs = slugs
    settings.save(update_fields=['primary_vertical_slug', 'enabled_module_slugs'])
    return slugs


def vertical_preset_modules(vertical_slug: str) -> tuple[str, ...]:
    """Geriye dönük uyumluluk."""
    return vertical_preset_all_slugs(vertical_slug)
