"""Kurulum modül listesi — module_catalog tabanlı."""

from __future__ import annotations

from django.urls import NoReverseMatch, reverse

from common.module_catalog import (
    MODULE_KIND_APP,
    MODULE_KIND_INTEGRATION,
    MODULE_GATE_EXEMPT_PREFIXES,
    MODULE_STATUS_ACTIVE,
    MODULE_STATUS_BETA,
    MODULE_STATUS_ROADMAP,
    MODULES,
    default_enabled_module_slugs,
    module_by_slug,
    route_prefix_to_module_slug,
)
from common.module_particles import LEGACY_MODULE_ALIASES, particle_by_slug

# Eski profil / yetenek slug → modül slug
LEGACY_PROFILE_TO_MODULE: dict[str, str | None] = {
    'app.kobi.customers': 'contact',
    'app.kobi.service_desk': 'services',
    'app.kobi.finance': 'accounting',
    'app.kobi.campaigns': 'outreach',
    'cap.whatsapp.send': 'integration_whatsapp_bridge',
    'cap.whatsapp.api': 'integration_whatsapp_api',
    'cap.data.harvest': 'integration_data_harvest',
    'cap.media.library': 'integration_media',
    'int.whatsapp.send': 'integration_whatsapp_bridge',
    'int.whatsapp.api': 'integration_whatsapp_api',
    'int.data.harvest': 'integration_data_harvest',
    'int.media.library': 'integration_media',
    'contact': 'contact',
    'services': 'services',
    'accounting': 'accounting',
    'outreach': 'outreach',
    'tools': None,
    'agency_suite': None,
    'agency_retainer': None,
    'agency_clients': None,
    'agency_freelancers': None,
    'agency_firms': None,
    'agency_pipeline': None,
    'agency_finance': None,
    'agency_campaigns': None,
}

APP_SECTION_LABELS: dict[str, tuple[str, str]] = {
    'contact': ('Rehber & İlişkiler', 'book-user'),
    'services': ('Operasyon', 'headphones'),
    'accounting': ('Finans', 'calculator'),
    'outreach': ('İletişim', 'messages-square'),
    'other': ('Uygulamalar', 'layout-grid'),
}


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix)


def _site_settings():
    from core_settings.models import SiteSettings
    return SiteSettings.objects.first()


def _known_module_slugs() -> set[str]:
    return {
        m['slug'] for m in MODULES
        if not m['slug'].startswith('agency_')
    }


def _default_enabled_slugs() -> list[str]:
    return [s for s in default_enabled_module_slugs() if not s.startswith('agency_')]


def _normalize_stored_slugs(raw: list | tuple | None) -> list[str]:
    known = _known_module_slugs()
    default = _default_enabled_slugs()
    if not raw:
        return default

    out: list[str] = []
    for slug in raw:
        if slug.startswith('agency_') or slug.startswith('p.agency') or slug.startswith('app.agency'):
            continue
        if slug.startswith('p.'):
            continue
        if slug in LEGACY_PROFILE_TO_MODULE:
            mapped = LEGACY_PROFILE_TO_MODULE[slug]
            if mapped and mapped in known and mapped not in out:
                out.append(mapped)
            continue
        if slug.startswith('app.') or slug.startswith('cap.') or slug.startswith('int.'):
            mapped = LEGACY_PROFILE_TO_MODULE.get(slug)
            if mapped and mapped not in out:
                out.append(mapped)
            continue
        if slug in LEGACY_MODULE_ALIASES:
            for alias in LEGACY_MODULE_ALIASES[slug]:
                if alias in known and alias not in out:
                    out.append(alias)
            continue
        if slug in known and slug not in out:
            out.append(slug)

    return out or default


def get_enabled_module_slugs() -> list[str]:
    settings = _site_settings()
    if settings and settings.enabled_module_slugs:
        return _normalize_stored_slugs(settings.enabled_module_slugs)
    return _normalize_stored_slugs(None)


def get_enabled_particle_slugs() -> list[str]:
    slugs: set[str] = set()
    settings = _site_settings()
    if settings and settings.enabled_module_slugs:
        for slug in settings.enabled_module_slugs:
            if slug.startswith('p.') and not slug.startswith('p.agency'):
                slugs.add(slug)
    for mod_slug in get_enabled_module_slugs():
        mod = module_by_slug(mod_slug)
        if mod:
            for p in mod.get('particle_slugs', ()):
                if not p.startswith('p.agency'):
                    slugs.add(p)
    return list(slugs)


def is_module_enabled(slug: str) -> bool:
    if slug in LEGACY_MODULE_ALIASES:
        return all(is_module_enabled(s) for s in LEGACY_MODULE_ALIASES[slug])
    return slug in get_enabled_module_slugs()


def is_particle_enabled(slug: str) -> bool:
    return slug in get_enabled_particle_slugs()


def is_particle_enabled_for_nav(slug: str) -> bool:
    p = particle_by_slug(slug)
    if not p or not is_particle_enabled(slug):
        return False
    parent = p.get('parent_module')
    if parent and not is_module_enabled(parent):
        return False
    return True


def resolve_path_module_slug(path: str) -> str | None:
    if any(_path_matches(path, p) for p in MODULE_GATE_EXEMPT_PREFIXES):
        return None
    for prefix, slug in route_prefix_to_module_slug():
        if slug.startswith('agency_'):
            continue
        if _path_matches(path, prefix):
            return slug
    return None


def resolve_path_particle_slug(path: str) -> str | None:
    from common.module_particles import particle_route_prefixes
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


def build_modules_nav_flags(user) -> dict[str, bool]:
    return {m['slug']: module_available_for_nav(user, m['slug']) for m in MODULES}


def build_particles_nav_short(user) -> dict[str, bool]:
    mapping = {
        'p.contact.customers': 'contact_customers',
        'p.contact.firms': 'contact_firms',
        'p.contact.teams': 'contact_teams',
        'p.contact.freelancers': 'contact_freelancers',
        'p.accounting.personnel': 'accounting_personnel',
        'p.accounting.payroll': 'accounting_payroll',
        'p.accounting.finance': 'accounting_finance',
        'p.accounting.sales': 'accounting_sales',
        'p.accounting.cash': 'accounting_cash',
        'p.accounting.receivables': 'accounting_receivables',
        'p.accounting.stock': 'accounting_stock',
        'p.outreach.campaigns': 'outreach_campaigns',
    }
    return {
        short: is_particle_enabled_for_nav(full)
        for full, short in mapping.items()
    }


def _hub_url(url_name: str | None) -> str | None:
    if not url_name:
        return None
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def _module_is_active(mod: dict, path: str, url_name: str | None) -> bool:
    if url_name and url_name == mod.get('hub_url_name'):
        return True
    for prefix in mod.get('route_prefixes', ()):
        if path.startswith(prefix):
            return True
    return False


def build_module_sidebar(user, request) -> dict:
    """Sol menü — kurulu modüller."""
    path = getattr(request, 'path', '') or ''
    match = getattr(request, 'resolver_match', None)
    url_name = match.url_name if match else None

    groups: dict[str, dict] = {}
    integrations: list[dict] = []

    for mod in MODULES:
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        if mod['slug'] == 'settings':
            continue
        if not module_available_for_nav(user, mod['slug']):
            continue

        entry = {
            'slug': mod['slug'],
            'name': mod['name'],
            'icon': mod.get('icon', 'puzzle'),
            'url': _hub_url(mod.get('hub_url_name')),
            'platform_modules': (mod['slug'],),
            'active': _module_is_active(mod, path, url_name),
        }
        if not entry['url']:
            continue

        if mod['kind'] == MODULE_KIND_INTEGRATION:
            integrations.append(entry)
            continue

        section = mod.get('panel_section') or 'other'
        label = APP_SECTION_LABELS.get(section, APP_SECTION_LABELS['other'])
        groups.setdefault(section, {
            'slug': section,
            'name': label[0],
            'icon': label[1],
            'items': [],
        })
        groups[section]['items'].append(entry)

    ordered_groups = []
    for section in ('contact', 'services', 'accounting', 'outreach', 'other'):
        g = groups.get(section)
        if g and g['items']:
            g['items'].sort(key=lambda i: i['name'])
            ordered_groups.append(g)

    integrations.sort(key=lambda i: i['name'])
    return {
        'groups': ordered_groups,
        'integrations': integrations,
        'capabilities': integrations,
    }


def build_module_record(user, mod: dict) -> dict:
    slug = mod['slug']
    installed = is_module_enabled(slug)
    hub = _hub_url(mod.get('hub_url_name'))
    record = dict(mod)
    record['installed'] = installed
    record['hub_url'] = hub if installed else None
    record['open_url'] = hub
    record['user_has_access'] = user_can_access_module(user, mod) if installed else False
    record['can_open'] = bool(hub and installed and user_can_access_module(user, mod))
    record['can_toggle'] = mod.get('can_disable', True)
    return record


def build_module_hub_context(user, *, query: str = '') -> dict:
    q = (query or '').strip().lower()
    apps: list[dict] = []
    integrations: list[dict] = []

    for mod in MODULES:
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        if mod['slug'] == 'settings':
            continue
        if mod['slug'].startswith('agency_'):
            continue
        if q and q not in f"{mod['name']} {mod['summary']}".lower():
            continue
        rec = build_module_record(user, mod)
        if mod['kind'] == MODULE_KIND_INTEGRATION:
            integrations.append(rec)
        elif mod['kind'] == MODULE_KIND_APP:
            apps.append(rec)

    apps.sort(key=lambda a: (a.get('sort', 99), a['name']))
    integrations.sort(key=lambda a: (a.get('sort', 99), a['name']))

    groups: dict[str, list] = {}
    for app in apps:
        section = app.get('panel_section') or 'other'
        groups.setdefault(section, []).append(app)

    module_app_groups = []
    for section in ('contact', 'services', 'accounting', 'outreach', 'other'):
        items = groups.get(section, [])
        if items:
            label = APP_SECTION_LABELS.get(section, APP_SECTION_LABELS['other'])
            module_app_groups.append({
                'slug': section,
                'name': label[0],
                'icon': label[1],
                'items': items,
            })

    roadmap = [
        dict(m) for m in MODULES
        if m['status'] == MODULE_STATUS_ROADMAP and not m['slug'].startswith('agency_')
    ]

    return {
        'module_app_groups': module_app_groups,
        'module_integrations': integrations,
        'module_catalog_roadmap': roadmap,
        'module_installed_count': sum(1 for a in apps + integrations if a['installed']),
        'module_roadmap_count': len(roadmap),
        'module_search_query': query,
        'enabled_module_slugs': get_enabled_module_slugs(),
    }


def build_panel_modules(user) -> list[dict]:
    records = []
    for mod in MODULES:
        if mod['kind'] != MODULE_KIND_APP or mod['slug'] == 'settings':
            continue
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        if mod['slug'].startswith('agency_'):
            continue
        rec = build_module_record(user, mod)
        if rec['installed'] and rec['can_open']:
            records.append(rec)
    records.sort(key=lambda a: (a.get('sort', 99), a['name']))
    return records


def build_panel_integrations(user) -> list[dict]:
    records = []
    for mod in MODULES:
        if mod['kind'] != MODULE_KIND_INTEGRATION:
            continue
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        rec = build_module_record(user, mod)
        if rec['installed'] and rec['can_open']:
            records.append(rec)
    records.sort(key=lambda a: (a.get('sort', 99), a['name']))
    return records


def panel_section_visible(section_key: str) -> bool:
    mapping = {
        'contact': 'contact',
        'services': 'services',
        'accounting': 'accounting',
        'outreach': 'outreach',
    }
    slug = mapping.get(section_key)
    return is_module_enabled(slug) if slug else False


def reset_enabled_modules_to_defaults() -> list[str]:
    slugs = _default_enabled_slugs()
    settings = _site_settings()
    if not settings:
        from core_settings.models import SiteSettings
        settings = SiteSettings.objects.create()
    settings.primary_vertical_slug = 'kobi'
    settings.enabled_module_slugs = slugs
    settings.save(update_fields=['primary_vertical_slug', 'enabled_module_slugs'])
    return slugs


# Geriye dönük isimler
build_profile_sidebar = build_module_sidebar


def get_primary_vertical_slug() -> str:
    return 'kobi'
