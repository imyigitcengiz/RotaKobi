"""Kurumsal sektör tipleri — modül uyumluluğu ve kurulum paketleri.

Landing, modül merkezi ve bilgi bankası bu katalogdan beslenir.
"""

from __future__ import annotations

FIT_TAM = 'tam'
FIT_YUKSEK = 'yuksek'
FIT_ORTA = 'orta'
FIT_KISMI = 'kismi'

FIT_LABELS: dict[str, str] = {
    FIT_TAM: 'Tam uyum',
    FIT_YUKSEK: 'Yüksek',
    FIT_ORTA: 'Orta',
    FIT_KISMI: 'Kısmi',
}

# slug, icon, ad, uyum etiketi, açıklama
CORPORATE_SECTORS: tuple[tuple[str, str, str, str, str], ...] = (
    ('montaj_saha', 'wrench', 'Montaj & saha servis', FIT_TAM, 'Teklif → satış → saha → stok → tahsilat akışı'),
    ('bayi_servis', 'store', 'Bayi servis ağı', FIT_YUKSEK, 'Garanti servisi, çok nokta, alacak takibi'),
    ('insaat_taahhut', 'hard-hat', 'İnşaat & taahhüt', FIT_YUKSEK, 'Saha ekip, malzeme reçetesi, proje satışı'),
    ('hizmet_danismanlik', 'briefcase', 'Hizmet & danışmanlık', FIT_ORTA, 'Saha modülü kapalı; teklif, satış, kasa'),
    ('evde_bakim', 'heart-pulse', 'Evde bakım / sağlık', FIT_ORTA, 'Randevu planı; muhasebe modülü opsiyonel'),
    ('stk_dernek', 'heart-handshake', 'STK & dernek', FIT_KISMI, 'Kampanya, rehber; servis/muhasebe kapalı profil'),
)

# Ortak modül setleri
_KOBI_CORE_MODULES = (
    'contact', 'services', 'accounting', 'outreach', 'settings',
    'supplier_payables', 'e_invoice_bridge', 'project_costing', 'multi_cash',
    'projects', 'timesheet',
    'integration_data_harvest', 'integration_whatsapp_bridge',
    'integration_whatsapp_api', 'integration_media', 'integration_weather',
)
_KOBI_CORE_PARTICLES = (
    'p.contact.customers', 'p.contact.firms', 'p.contact.teams',
    'p.accounting.personnel', 'p.accounting.payroll',
    'p.accounting.finance', 'p.accounting.sales',
    'p.accounting.cash', 'p.accounting.receivables', 'p.accounting.stock',
    'p.accounting.payables', 'p.accounting.multi_cash', 'p.accounting.project_costing',
    'p.accounting.e_export', 'p.accounting.timesheet', 'p.accounting.projects',
    'p.outreach.campaigns',
)

SECTOR_PRESETS: dict[str, dict[str, tuple[str, ...] | str]] = {
    'montaj_saha': {
        'fit': FIT_TAM,
        'modules': _KOBI_CORE_MODULES,
        'particles': _KOBI_CORE_PARTICLES,
    },
    'bayi_servis': {
        'fit': FIT_YUKSEK,
        'modules': (
            'contact', 'services', 'accounting', 'outreach', 'settings',
            'supplier_payables', 'multi_cash', 'e_invoice_bridge',
            'integration_data_harvest', 'integration_whatsapp_bridge',
            'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.contact.teams',
            'p.accounting.personnel', 'p.accounting.payroll',
            'p.accounting.finance', 'p.accounting.sales',
            'p.accounting.cash', 'p.accounting.receivables', 'p.accounting.stock',
            'p.accounting.payables', 'p.accounting.multi_cash', 'p.accounting.e_export',
            'p.outreach.campaigns',
        ),
    },
    'insaat_taahhut': {
        'fit': FIT_YUKSEK,
        'modules': (
            'contact', 'services', 'accounting', 'outreach', 'settings',
            'supplier_payables', 'project_costing', 'multi_cash', 'projects',
            'timesheet', 'e_invoice_bridge',
            'integration_whatsapp_bridge', 'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.contact.teams',
            'p.accounting.personnel', 'p.accounting.payroll',
            'p.accounting.finance', 'p.accounting.sales',
            'p.accounting.cash', 'p.accounting.receivables', 'p.accounting.stock',
            'p.accounting.payables', 'p.accounting.multi_cash',
            'p.accounting.project_costing', 'p.accounting.e_export',
            'p.accounting.timesheet', 'p.accounting.projects',
            'p.outreach.campaigns',
        ),
    },
    'hizmet_danismanlik': {
        'fit': FIT_ORTA,
        'modules': (
            'contact', 'accounting', 'outreach', 'settings',
            'multi_cash', 'timesheet', 'e_invoice_bridge',
            'integration_whatsapp_bridge', 'integration_whatsapp_api',
            'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms',
            'p.accounting.personnel', 'p.accounting.finance', 'p.accounting.sales',
            'p.accounting.cash', 'p.accounting.receivables',
            'p.accounting.multi_cash', 'p.accounting.e_export', 'p.accounting.timesheet',
            'p.outreach.campaigns',
        ),
    },
    'evde_bakim': {
        'fit': FIT_ORTA,
        'modules': (
            'contact', 'services', 'outreach', 'settings',
            'integration_whatsapp_bridge', 'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.teams',
            'p.outreach.campaigns',
        ),
    },
    'stk_dernek': {
        'fit': FIT_KISMI,
        'modules': (
            'contact', 'outreach', 'settings',
            'integration_whatsapp_api', 'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.outreach.campaigns',
        ),
    },
}

# Modül → sektör uyumu (preset türetmesi + manuel tam/yüksek işaretleri)
def _build_module_sector_map() -> dict[str, list[tuple[str, str]]]:
    out: dict[str, set[tuple[str, str]]] = {}
    for sector_slug, preset in SECTOR_PRESETS.items():
        fit = preset['fit']
        for mod in preset['modules']:
            out.setdefault(mod, set()).add((sector_slug, fit))
        for part in preset['particles']:
            out.setdefault(part, set()).add((sector_slug, fit))
    return {k: sorted(v, key=lambda x: x[0]) for k, v in out.items()}


MODULE_SECTOR_MAP: dict[str, list[tuple[str, str]]] = _build_module_sector_map()

# Geriye dönük vertical slug eşlemesi
LEGACY_VERTICAL_TO_SECTOR: dict[str, str] = {
    'kobi': 'montaj_saha',
    'retail': 'bayi_servis',
    'healthcare': 'evde_bakim',
    'nonprofit': 'stk_dernek',
    'agency': 'hizmet_danismanlik',
    'universal': 'montaj_saha',
}


def sector_by_slug(slug: str) -> dict | None:
    for row in CORPORATE_SECTORS:
        if row[0] == slug:
            return {
                'slug': row[0],
                'icon': row[1],
                'name': row[2],
                'fit': row[3],
                'fit_label': FIT_LABELS.get(row[3], row[3]),
                'description': row[4],
            }
    return None


def all_sectors() -> list[dict]:
    return [sector_by_slug(row[0]) for row in CORPORATE_SECTORS]


def landing_sectors_tuple() -> tuple[tuple[str, str, str, str], ...]:
    """Landing şablonu: icon, ad, uyum etiketi, açıklama."""
    return tuple(
        (row[1], row[2], FIT_LABELS.get(row[3], row[3]), row[4])
        for row in CORPORATE_SECTORS
    )


def sector_preset_all_slugs(sector_slug: str) -> tuple[str, ...]:
    preset = SECTOR_PRESETS.get(sector_slug, SECTOR_PRESETS['montaj_saha'])
    return preset['modules'] + preset['particles']


def normalize_sector_slug(slug: str) -> str:
    if slug in SECTOR_PRESETS:
        return slug
    return LEGACY_VERTICAL_TO_SECTOR.get(slug, 'montaj_saha')


def module_sector_labels(module_slug: str) -> list[dict]:
    """Modül kartında gösterilecek sektör etiketleri."""
    rows = MODULE_SECTOR_MAP.get(module_slug, ())
    labels = []
    for sector_slug, fit in rows:
        sec = sector_by_slug(sector_slug)
        if sec:
            labels.append({
                'slug': sector_slug,
                'name': sec['name'],
                'fit': fit,
                'fit_label': FIT_LABELS.get(fit, fit),
            })
    return labels


def sector_hub_cards(*, current_sector: str | None = None) -> list[dict]:
    cards = []
    for sec in all_sectors():
        if not sec:
            continue
        preset = SECTOR_PRESETS[sec['slug']]
        mod_count = len(preset['modules'])
        part_count = len(preset['particles'])
        cards.append({
            **sec,
            'module_count': mod_count,
            'particle_count': part_count,
            'is_active': sec['slug'] == normalize_sector_slug(current_sector or ''),
        })
    return cards


def apply_sector_preset(settings, sector_slug: str) -> tuple[str, ...]:
    """SiteSettings'e sektör paketini uygular; etkin slug listesini döner."""
    slug = normalize_sector_slug(sector_slug)
    slugs = list(sector_preset_all_slugs(slug))
    settings.primary_vertical_slug = slug
    settings.enabled_module_slugs = slugs
    settings.save(update_fields=['primary_vertical_slug', 'enabled_module_slugs'])
    return tuple(slugs)
