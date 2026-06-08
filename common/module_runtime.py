"""Kurulum modül listesi — module_catalog tabanlı."""

from __future__ import annotations

from django.urls import NoReverseMatch, reverse

from common.module_context import current_module_user
from common.module_plan import (
    owner_selected_modules,
    owner_selected_particles,
    subscription_owner_for_user,
)
from common.module_catalog import (
    MODULE_KIND_APP,
    MODULE_KIND_INTEGRATION,
    MODULE_GATE_EXEMPT_EXACT,
    MODULE_GATE_EXEMPT_PREFIXES,
    MODULE_STATUS_ACTIVE,
    MODULE_STATUS_BETA,
    MODULE_STATUS_ROADMAP,
    MODULES,
    default_enabled_module_slugs,
    module_by_slug,
    route_prefix_to_module_slug,
)
from common.module_particles import LEGACY_MODULE_ALIASES, particle_by_slug, resolve_particle_slug

# Eski ayrı uygulama slug → muhasebe parçacığı (Modül Merkezi migrasyonu)
LEGACY_APP_MODULE_TO_PARTICLE: dict[str, str] = {
    'supplier_payables': 'p.accounting.payables',
    'project_costing': 'p.accounting.project_costing',
    'multi_cash': 'p.accounting.multi_cash',
    'projects': 'p.accounting.projects',
    'timesheet': 'p.accounting.timesheet',
}

MODULE_PARTICLE_FALLBACK: dict[str, str] = {
    **LEGACY_APP_MODULE_TO_PARTICLE,
    'e_invoice_bridge': 'p.accounting.e_export',
}

_EXTENSION_MODULE_SLUGS = frozenset({'e_invoice_bridge'})

LEGACY_PROFILE_TO_MODULE: dict[str, str | None] = {
    'app.kobi.customers': 'contact',
    'app.kobi.service_desk': 'services',
    'app.kobi.finance': 'accounting',
    'app.kobi.campaigns': 'outreach',
    'cap.whatsapp.send': 'integration_whatsapp_bridge',
    'cap.whatsapp.api': 'integration_whatsapp_api',
    'cap.campaigns.bulk': 'integration_bulk_messaging',
    'cap.data.harvest': 'integration_data_harvest',
    'cap.media.library': 'integration_media',
    'int.whatsapp.send': 'integration_whatsapp_bridge',
    'int.whatsapp.api': 'integration_whatsapp_api',
    'int.campaigns.bulk': 'integration_bulk_messaging',
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

PANEL_HOME_APP_SLUGS: frozenset[str] = frozenset({
    'contact', 'services', 'accounting', 'outreach',
})

PANEL_SECTION_ORDER: tuple[str, ...] = (
    'contact', 'services', 'accounting', 'outreach', 'other',
)


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix)


def _site_settings():
    from core_settings.models import SiteSettings
    return SiteSettings.objects.first()


def _migrate_legacy_app_modules_in_storage() -> None:
    """Eski eklenti modül slug'larını parçacık slug'ına çevir."""
    settings = _site_settings()
    if not settings or not settings.enabled_module_slugs:
        return
    raw = list(settings.enabled_module_slugs)
    changed = False
    out: list[str] = []
    for slug in raw:
        particle = LEGACY_APP_MODULE_TO_PARTICLE.get(slug)
        if particle:
            if particle not in out:
                out.append(particle)
            changed = True
            continue
        out.append(slug)
    if changed:
        settings.enabled_module_slugs = out
        settings.save(update_fields=['enabled_module_slugs'])


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
    user = current_module_user()
    if user and getattr(user, 'is_authenticated', False):
        if user.is_superuser:
            return _normalize_stored_slugs(None)
        from common.module_context import current_module_request

        owner = subscription_owner_for_user(user, request=current_module_request()) or user
        return owner_selected_modules(owner)

    _migrate_legacy_app_modules_in_storage()
    settings = _site_settings()
    if settings and settings.enabled_module_slugs:
        return _normalize_stored_slugs(settings.enabled_module_slugs)
    return _normalize_stored_slugs(None)


def is_module_installed(slug: str) -> bool:
    """Modül merkezi aç/kapa listesinde mi — parçacık yedeği hariç."""
    if slug in LEGACY_MODULE_ALIASES:
        return all(is_module_installed(s) for s in LEGACY_MODULE_ALIASES[slug])
    return slug in get_enabled_module_slugs()


def _particle_allowed_when_parent_installed(slug: str) -> bool:
    """Parçacık — üst modül kapalıysa sayılmaz."""
    p = particle_by_slug(slug)
    if not p:
        return False
    parent = p.get('parent_module')
    if parent and not is_module_installed(parent):
        return False
    return True


def get_enabled_particle_slugs() -> list[str]:
    user = current_module_user()
    if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
        owner = subscription_owner_for_user(user) or user
        return owner_selected_particles(owner)

    _migrate_legacy_app_modules_in_storage()
    settings = _site_settings()
    raw = list(settings.enabled_module_slugs) if settings and settings.enabled_module_slugs else []

    explicit_particles = {
        resolve_particle_slug(slug)
        for slug in raw
        if slug.startswith('p.') and not slug.startswith('p.agency')
    }

    if explicit_particles:
        slugs = set(explicit_particles)
    else:
        slugs = set()
        for mod_slug in get_enabled_module_slugs():
            mod = module_by_slug(mod_slug)
            if not mod or mod_slug not in _EXTENSION_MODULE_SLUGS:
                continue
            for p in mod.get('particle_slugs', ()):
                if not p.startswith('p.agency'):
                    slugs.add(p)
        if not slugs:
            from common.module_particles import default_enabled_particle_slugs
            for pslug in default_enabled_particle_slugs():
                if _particle_allowed_when_parent_installed(pslug):
                    slugs.add(pslug)

    return [s for s in slugs if _particle_allowed_when_parent_installed(s)]


def is_module_enabled(slug: str) -> bool:
    if slug in LEGACY_MODULE_ALIASES:
        return all(is_module_enabled(s) for s in LEGACY_MODULE_ALIASES[slug])
    if slug in get_enabled_module_slugs():
        return True
    particle_slug = MODULE_PARTICLE_FALLBACK.get(slug)
    if particle_slug and is_particle_enabled(particle_slug):
        return True
    return False


def is_particle_enabled(slug: str) -> bool:
    return resolve_particle_slug(slug) in get_enabled_particle_slugs()


def is_particle_enabled_for_nav(slug: str) -> bool:
    slug = resolve_particle_slug(slug)
    p = particle_by_slug(slug)
    if not p or not is_particle_enabled(slug):
        return False
    parent = p.get('parent_module')
    if parent and not is_module_installed(parent):
        return False
    return True


def integration_nav_visible(user, slug: str) -> bool:
    """Entegrasyon menü/kart — kurulu, üst modül açık ve kullanıcı yetkisi."""
    mod = module_by_slug(slug)
    if not mod or mod['kind'] != MODULE_KIND_INTEGRATION:
        return False
    return integration_visible_on_panel(user, mod)


def module_route_allowed(slug: str) -> bool:
    """URL erişimi — Modül Merkezi aç/kapa (parçacık yedeği hariç)."""
    if not is_module_installed(slug):
        return False
    mod = module_by_slug(slug)
    if not mod:
        return False
    return _panel_parent_installed(mod)


def resolve_path_module_slug(path: str) -> str | None:
    if path in MODULE_GATE_EXEMPT_EXACT:
        return None
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
    if not is_module_installed(slug):
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
        'p.contact.personnel': 'contact_personnel',
        'p.accounting.payroll': 'accounting_payroll',
        'p.accounting.finance': 'accounting_finance',
        'p.accounting.sales': 'accounting_sales',
        'p.accounting.cash': 'accounting_cash',
        'p.accounting.receivables': 'accounting_receivables',
        'p.accounting.stock': 'accounting_stock',
        'p.accounting.payables': 'accounting_payables',
        'p.accounting.multi_cash': 'accounting_cash_accounts',
        'p.accounting.project_costing': 'accounting_project_costing',
        'p.accounting.e_export': 'accounting_e_export',
        'p.accounting.timesheet': 'accounting_timesheet',
        'p.accounting.projects': 'accounting_projects',
        'p.outreach.campaigns': 'outreach_campaigns',
    }
    flags = {
        short: is_particle_enabled_for_nav(full)
        for full, short in mapping.items()
    }
    flags['accounting_personnel'] = flags.get('contact_personnel', False)
    return flags


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
    integrations_by_section: dict[str, list] = {}

    for mod in MODULES:
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        if mod['slug'] == 'settings':
            continue
        if mod['kind'] == MODULE_KIND_INTEGRATION:
            if not integration_visible_on_panel(user, mod):
                continue
        elif not module_available_for_nav(user, mod['slug']):
            continue

        entry = {
            'slug': mod['slug'],
            'name': mod['name'],
            'icon': mod.get('icon', 'puzzle'),
            'url': _hub_url(mod.get('hub_url_name')),
            'platform_modules': (mod['slug'],),
            'panel_section': mod.get('panel_section'),
            'active': _module_is_active(mod, path, url_name),
        }
        if not entry['url']:
            continue

        if mod['kind'] == MODULE_KIND_INTEGRATION:
            section = mod.get('panel_section') or 'other'
            integrations_by_section.setdefault(section, []).append(entry)
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
    for section in integrations_by_section:
        integrations_by_section[section].sort(key=lambda i: i['name'])
    return {
        'groups': ordered_groups,
        'integrations': integrations,
        'integrations_by_section': integrations_by_section,
        'capabilities': [],
    }


def build_module_record(user, mod: dict) -> dict:
    from common.sector_catalog import module_sector_labels

    slug = mod['slug']
    installed = is_module_installed(slug)
    hub = _hub_url(mod.get('hub_url_name'))
    record = dict(mod)
    record['installed'] = installed
    record['hub_url'] = hub if installed else None
    record['open_url'] = hub
    record['user_has_access'] = user_can_access_module(user, mod) if installed else False
    record['can_open'] = bool(hub and installed and user_can_access_module(user, mod))
    record['can_toggle'] = mod.get('can_disable', True)
    record['sector_labels'] = module_sector_labels(slug)
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

    module_app_groups = enrich_module_hub_groups(module_app_groups)

    catalog_count = len(apps) + len(integrations)
    installed_count = sum(1 for a in apps + integrations if a['installed'])

    return {
        'module_app_groups': module_app_groups,
        'module_integrations': integrations,
        'module_catalog_roadmap': roadmap,
        'module_installed_count': installed_count,
        'module_catalog_count': catalog_count,
        'module_roadmap_count': len(roadmap),
        'module_search_query': query,
        'enabled_module_slugs': get_enabled_module_slugs(),
    }


def build_subscription_modules_context(user, *, query: str = '') -> dict:
    """Abonelik sayfası modül bölümü — plan tavanı ve sahip seçimi."""
    from common.brand_team import is_subscription_owner
    from common.module_plan import plan_included_modules, plan_included_particles, subscription_owner_for_user
    from common.module_toggle import user_can_manage_modules

    owner = subscription_owner_for_user(user) or (user if is_subscription_owner(user) else None)
    hub = build_module_hub_context(user, query=query)
    if not owner:
        hub['can_manage_modules'] = False
        hub['subscription_owner'] = None
        return hub

    plan_mods = set(plan_included_modules(owner.active_plan))
    plan_parts = set(plan_included_particles(owner.active_plan))

    def _annotate(items):
        for item in items:
            slug = item['slug']
            item['in_plan'] = slug in plan_mods or slug in plan_parts
            item['needs_upgrade'] = not item['in_plan']

    for group in hub['module_app_groups']:
        _annotate(group['items'])
    _annotate(hub['module_integrations'])

    hub['can_manage_modules'] = user_can_manage_modules(user)
    hub['subscription_owner'] = owner
    hub['plan_module_count'] = len(plan_mods)
    return hub


def _is_panel_home_app(mod: dict) -> bool:
    return mod['slug'] in PANEL_HOME_APP_SLUGS


def _panel_parent_installed(mod: dict) -> bool:
    parent = mod.get('panel_section')
    if mod.get('kind') == MODULE_KIND_INTEGRATION:
        if parent and parent != mod.get('slug') and module_by_slug(parent):
            return is_module_installed(parent)
        return True
    if not parent or parent == mod.get('slug'):
        return True
    if module_by_slug(parent):
        return is_module_installed(parent)
    return True


def integration_visible_on_panel(user, mod: dict) -> bool:
    if mod['kind'] != MODULE_KIND_INTEGRATION:
        return False
    if not module_available_for_nav(user, mod['slug']):
        return False
    return _panel_parent_installed(mod)


def build_panel_modules(user) -> list[dict]:
    records = []
    for mod in MODULES:
        if mod['kind'] != MODULE_KIND_APP or mod['slug'] == 'settings':
            continue
        if mod['status'] not in (MODULE_STATUS_ACTIVE, MODULE_STATUS_BETA):
            continue
        if mod['slug'].startswith('agency_'):
            continue
        if not _is_panel_home_app(mod):
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
        if not integration_visible_on_panel(user, mod):
            continue
        rec = build_module_record(user, mod)
        records.append(rec)
    records.sort(key=lambda a: (a.get('sort', 99), a['name']))
    return records


def build_panel_integration_groups(user) -> list[dict]:
    by_section: dict[str, list[dict]] = {}
    for rec in build_panel_integrations(user):
        section = rec.get('panel_section') or 'other'
        by_section.setdefault(section, []).append(rec)

    groups: list[dict] = []
    for section in PANEL_SECTION_ORDER:
        items = by_section.get(section)
        if not items:
            continue
        label, icon = APP_SECTION_LABELS.get(section, APP_SECTION_LABELS['other'])
        groups.append({
            'section': section,
            'name': label,
            'icon': icon,
            'items': items,
        })
    return groups


def panel_section_visible(section_key: str) -> bool:
    mapping = {
        'contact': 'contact',
        'services': 'services',
        'accounting': 'accounting',
        'outreach': 'outreach',
    }
    slug = mapping.get(section_key)
    return is_module_installed(slug) if slug else False


def reset_enabled_modules_to_defaults() -> list[str]:
    from common.sector_catalog import apply_sector_preset

    settings = _site_settings()
    if not settings:
        from core_settings.models import SiteSettings
        settings = SiteSettings.objects.create()
    return list(apply_sector_preset(settings, 'montaj_saha'))


MAIN_NAV_MODULE_SLUGS = frozenset({
    'contact', 'services', 'accounting', 'outreach',
})

def _integration_visible_in_tools(user, mod: dict) -> bool:
    """Araçlar menüsü — üst modül kapalı olsa da kurulu entegrasyonları listele."""
    if mod['kind'] != MODULE_KIND_INTEGRATION:
        return False
    return module_available_for_nav(user, mod['slug'])


def _sidebar_module_entry(user, request, mod: dict) -> dict | None:
    path = getattr(request, 'path', '') or ''
    match = getattr(request, 'resolver_match', None)
    url_name = match.url_name if match else None
    url = _hub_url(mod.get('hub_url_name'))
    if not url:
        return None
    return {
        'slug': mod['slug'],
        'name': mod['name'],
        'icon': mod.get('icon', 'puzzle'),
        'url': url,
        'active': _module_is_active(mod, path, url_name),
    }


def _sidebar_feature_items(sidebar: dict, section: str, user, request) -> list[dict]:
    """Eklenti uygulamaları — katalog + sidebar grupları."""
    items: list[dict] = []
    seen: set[str] = set()
    for group in sidebar.get('groups', []):
        if group.get('slug') != section:
            continue
        for entry in group.get('items', []):
            slug = entry.get('slug')
            if slug in MAIN_NAV_MODULE_SLUGS or slug in seen:
                continue
            seen.add(slug)
            items.append(entry)
    for mod in MODULES:
        if mod['kind'] != MODULE_KIND_APP:
            continue
        slug = mod['slug']
        if slug in MAIN_NAV_MODULE_SLUGS or slug in seen:
            continue
        if section == 'accounting' and slug in _EXTENSION_MODULE_SLUGS:
            continue
        mod_section = mod.get('panel_section') or 'other'
        if mod_section != section:
            continue
        if not module_available_for_nav(user, slug):
            continue
        entry = _sidebar_module_entry(user, request, mod)
        if entry:
            seen.add(slug)
            items.append(entry)
    items.sort(key=lambda row: (row.get('name') or '').lower())
    return items


def build_particles_by_parent_module() -> dict[str, list[dict]]:
    """Modül merkezi — ana modül kartlarında parçacık listesi."""
    from common.module_particles import PARTICLES

    buckets: dict[str, list[dict]] = {s: [] for s in MAIN_NAV_MODULE_SLUGS}
    for particle in PARTICLES:
        parent = particle.get('parent_module')
        if parent not in buckets:
            continue
        buckets[parent].append({
            'slug': particle['slug'],
            'name': particle['name'],
            'summary': particle.get('summary', ''),
            'enabled': is_particle_enabled(particle['slug']),
            'sort': particle.get('sort', 99),
        })
    for rows in buckets.values():
        rows.sort(key=lambda r: r.get('sort', 99))
    return buckets


def enrich_module_hub_groups(module_app_groups: list[dict]) -> list[dict]:
    """Ana modül kartlarına parçacık ve eklenti modül listesi ekle."""
    particles = build_particles_by_parent_module()
    for group in module_app_groups:
        mains = [a for a in group['items'] if a['slug'] in MAIN_NAV_MODULE_SLUGS]
        extensions = [a for a in group['items'] if a['slug'] not in MAIN_NAV_MODULE_SLUGS]
        for app in mains:
            app['particles'] = particles.get(app['slug'], [])
            app['extension_modules'] = extensions
    return module_app_groups


def build_erp_sidebar_modules(user, request, *, active_slug: str | None) -> list[dict]:
    """Sol menü — açılır modül blokları ve eklenti özellikleri."""
    from django.urls import NoReverseMatch, reverse

    if not user.is_authenticated:
        return []

    sidebar = build_module_sidebar(user, request)
    nav_flags = build_modules_nav_flags(user)

    defs = (
        ('contact', 'contact_hub', 'book-user', 'common/erp_contact_nav.html', None),
        ('services', 'dashboard', 'headphones', 'common/erp_module_own_nav.html', 'services'),
        ('accounting', 'accounting_hub', 'calculator', 'common/erp_module_own_nav.html', 'accounting'),
        ('outreach', 'outreach_hub', 'messages-square', 'common/erp_outreach_nav.html', None),
    )

    from common.module_plan import plan_included_modules, subscription_owner_for_user

    owner = subscription_owner_for_user(user, request=request) or user
    plan_mods = set(plan_included_modules(owner.active_plan))

    blocks: list[dict] = []
    for slug, hub_name, icon, nav_template, nav_module in defs:
        installed = nav_flags.get(slug, False)
        mod = module_by_slug(slug)
        if not mod:
            continue
        if not installed and slug not in plan_mods:
            continue
        if slug == 'accounting':
            if not (
                user.is_superuser
                or user.has_perm_codename('access.accounting')
                or user.has_perm_codename('contact.personnel')
                or user.has_perm_codename('contact.payroll')
            ):
                continue
        elif not user_can_access_module(user, mod):
            continue
        hub_url_name = hub_name
        if slug == 'contact' and not user.has_perm_codename('access.contact'):
            if user.has_perm_codename('contact.personnel'):
                hub_url_name = 'contact_personnel'
        disabled = not installed
        try:
            hub_url = (
                reverse('subscription_dashboard') + '#moduller'
                if disabled
                else reverse(hub_url_name)
            )
        except NoReverseMatch:
            continue
        blocks.append({
            'slug': slug,
            'name': mod['name'],
            'icon': icon,
            'hub_url': hub_url,
            'nav_template': nav_template,
            'nav_module': nav_module,
            'expanded': active_slug == slug and not disabled,
            'disabled': disabled,
            'disabled_tooltip': 'Kapalı — Modül Merkezi' if disabled else '',
            'features': [] if disabled else _sidebar_feature_items(sidebar, slug, user, request),
        })
    return blocks


def _sidebar_tools_items(user, request) -> list[dict]:
    """Tüm entegrasyon linkleri — Araçlar menüsü (üst modül şartı yok)."""
    items: list[dict] = []
    seen: set[str] = set()
    for mod in MODULES:
        if not _integration_visible_in_tools(user, mod):
            continue
        entry = _sidebar_module_entry(user, request, mod)
        if not entry:
            continue
        url = entry.get('url') or ''
        if url in seen:
            continue
        seen.add(url)
        items.append(entry)
    items.sort(key=lambda row: (row.get('name') or '').lower())
    return items


_NAV_PIN_MODULES = frozenset({'contact', 'services', 'accounting', 'outreach'})
_CUSTOMER_NAV_PREFIX = '/contact/musteriler/'


def _path_is_integration_route(path: str) -> bool:
    for mod in MODULES:
        if mod.get('kind') != MODULE_KIND_INTEGRATION:
            continue
        for prefix in mod.get('route_prefixes', ()):
            if prefix and _path_matches(path, prefix):
                return True
    return False


def _sync_nav_module_pin(request, path: str) -> str | None:
    """Yardım masasından müşteriye gidince Rehber menüsü açılmasın (nav_module=services)."""
    if not getattr(request, 'session', None):
        return None
    raw = (request.GET.get('nav_module') or '').strip()
    if raw in _NAV_PIN_MODULES:
        request.session['erp_nav_expand_module'] = raw
        return raw
    if _path_is_integration_route(path):
        return None
    if path.startswith('/services-dashboard/'):
        request.session['erp_nav_expand_module'] = 'services'
    elif path.startswith('/muhasebe/'):
        request.session['erp_nav_expand_module'] = 'accounting'
    elif path.startswith('/iletisim/'):
        request.session['erp_nav_expand_module'] = 'outreach'
    elif path.startswith('/contact/') and not path.startswith(_CUSTOMER_NAV_PREFIX):
        request.session['erp_nav_expand_module'] = 'contact'
    pinned = request.session.get('erp_nav_expand_module')
    if pinned in _NAV_PIN_MODULES and path.startswith(_CUSTOMER_NAV_PREFIX):
        return pinned
    return None


def resolve_sidebar_expand_slug(path: str, path_slug: str | None, request=None) -> str | None:
    """Sidebar’da hangi blok açık — entegrasyon ve nav_module iğnesi."""
    if request is not None:
        pinned = _sync_nav_module_pin(request, path)
        if pinned:
            return pinned
    if path.startswith('/tools/') or _path_is_integration_route(path):
        return 'tools'
    mod = module_by_slug(path_slug) if path_slug else None
    if mod and mod.get('kind') == MODULE_KIND_INTEGRATION:
        return 'tools'
    return path_slug


def build_erp_sidebar_tools(user, request, *, expand_slug: str | None) -> dict | None:
    from django.urls import NoReverseMatch, reverse

    if not user.is_authenticated:
        return None
    items = _sidebar_tools_items(user, request)
    show_hub = user.is_superuser or user.has_perm_codename('access.tools')
    can_manage_modules = user.is_superuser or user.has_perm_codename('access.settings')
    if not items and not show_hub and not can_manage_modules:
        return None
    hub_url = None
    if show_hub:
        try:
            hub_url = reverse('tools_hub')
        except NoReverseMatch:
            show_hub = False
    if not hub_url and items:
        hub_url = items[0]['url']
    if not hub_url:
        try:
            hub_url = reverse('capabilities_hub')
        except NoReverseMatch:
            hub_url = '#'
    return {
        'slug': 'tools',
        'name': 'Araçlar',
        'icon': 'hammer',
        'hub_url': hub_url,
        'expanded': expand_slug == 'tools',
        'items': items,
        'show_hub': bool(show_hub and hub_url),
    }


# Geriye dönük isimler
build_profile_sidebar = build_module_sidebar


def get_primary_vertical_slug() -> str:
    from common.sector_catalog import normalize_sector_slug

    settings = _site_settings()
    if settings and settings.primary_vertical_slug:
        return normalize_sector_slug(settings.primary_vertical_slug)
    return 'montaj_saha'
