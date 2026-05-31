"""Modül parçacıkları — uygulama içi özellikler, sektöre göre ayrı aç/kapa.

Örnek: KOBİ → personel & saha ekipleri; Ajans → freelancer ağı, retainer (personel kapalı).
"""

from __future__ import annotations

PARTICLE_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ('rehber', 'Rehber & ilişkiler', 'users'),
    ('operasyon', 'Operasyon & saha', 'wrench'),
    ('finans', 'Finans & ödeme', 'wallet'),
    ('ajans', 'Ajans & proje', 'palette'),
    ('iletisim', 'İletişim', 'messages-square'),
)

PARTICLES: tuple[dict, ...] = (
    {
        'slug': 'p.contact.customers',
        'name': 'Müşteri kartları',
        'summary': 'Müşteri kayıtları, ürünler ve sözleşme bilgileri.',
        'category': 'rehber',
        'parent_module': 'contact',
        'route_prefixes': (),
        'vertical_tags': ('kobi', 'agency', 'retail', 'nonprofit', 'healthcare'),
        'default_enabled': True,
        'sort': 10,
    },
    {
        'slug': 'p.contact.firms',
        'name': 'Firma rehberi & Maps',
        'summary': 'Firma kaydı, etiketler ve Google Maps araması.',
        'category': 'rehber',
        'parent_module': 'contact',
        'route_prefixes': ('/contact/firmalar/', '/contact/firma-kazi/'),
        'vertical_tags': ('kobi', 'agency', 'retail', 'nonprofit'),
        'default_enabled': True,
        'sort': 20,
    },
    {
        'slug': 'p.contact.teams',
        'name': 'Saha servis ekipleri',
        'summary': 'Montaj/servis ekipleri ve ürün yetkinlikleri — kurumsal saha ops.',
        'category': 'operasyon',
        'parent_module': 'contact',
        'route_prefixes': ('/contact/ekip/',),
        'vertical_tags': ('kobi', 'retail', 'healthcare'),
        'default_enabled': True,
        'sort': 30,
    },
    {
        'slug': 'p.contact.freelancers',
        'name': 'Freelancer & taşeron ağı',
        'summary': 'Çözüm ortağı / freelancer ağı — ajans proje kadrosu.',
        'category': 'ajans',
        'parent_module': 'contact',
        'route_prefixes': ('/contact/cozum-agi/',),
        'vertical_tags': ('agency',),
        'default_enabled': False,
        'sort': 35,
    },
    {
        'slug': 'p.accounting.personnel',
        'name': 'Personel & kadro',
        'summary': 'Sigortalı personel, ekip ataması — kurumsal İK.',
        'category': 'operasyon',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/personel/', '/contact/personel/'),
        'vertical_tags': ('kobi', 'retail', 'healthcare'),
        'default_enabled': True,
        'sort': 40,
    },
    {
        'slug': 'p.accounting.payroll',
        'name': 'Maaş & avans',
        'summary': 'Aylık maaş döngüsü, avans mahsubu, brüt − avans = net.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/maas-avans/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 50,
    },
    {
        'slug': 'p.accounting.finance',
        'name': 'Gelir & gider',
        'summary': 'Kasa hareketleri ve dönem özeti.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/gelir-gider/',),
        'vertical_tags': ('kobi', 'agency', 'retail', 'nonprofit'),
        'default_enabled': True,
        'sort': 60,
    },
    {
        'slug': 'p.accounting.sales',
        'name': 'Satış kayıtları',
        'summary': 'Proje satışları, peşinat ve pipeline.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/satis/', '/sales-lead/'),
        'vertical_tags': ('kobi', 'agency', 'retail'),
        'default_enabled': True,
        'sort': 70,
    },
    {
        'slug': 'p.accounting.cash',
        'name': 'Kasa özeti',
        'summary': 'Açılış bakiyesi, gelir-gider ve tahsilatlarla güncel kasa.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/kasa/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 72,
    },
    {
        'slug': 'p.accounting.receivables',
        'name': 'Alacak takibi',
        'summary': 'Bekleyen tahsilatlar, gecikme filtresi ve WhatsApp hatırlatma.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/alacaklar/',),
        'vertical_tags': ('kobi', 'agency', 'retail'),
        'default_enabled': True,
        'sort': 74,
    },
    {
        'slug': 'p.accounting.stock',
        'name': 'Stok & reçete',
        'summary': 'Malzeme stoku, ürün reçeteleri (BOM), satış/serviste malzeme düşümü.',
        'category': 'operasyon',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/stok/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 76,
    },
    {
        'slug': 'p.accounting.payables',
        'name': 'Tedarikçi borçları',
        'summary': 'Alış faturaları, vade takibi ve ödeme planı.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/borclar/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 78,
    },
    {
        'slug': 'p.accounting.multi_cash',
        'name': 'Çoklu kasa & banka',
        'summary': 'Nakit, banka ve POS hesapları; bakiye özeti.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/hesaplar/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 79,
    },
    {
        'slug': 'p.accounting.project_costing',
        'name': 'Proje maliyet & kârlılık',
        'summary': 'Satış geliri − gider = proje marjı.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/proje-karlilik/',),
        'vertical_tags': ('kobi',),
        'default_enabled': True,
        'sort': 80,
    },
    {
        'slug': 'p.accounting.e_export',
        'name': 'e-Fatura / dış aktarım',
        'summary': 'Mali müşavir CSV paketi — Logo, Paraşüt içe aktarım.',
        'category': 'finans',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/dis-aktarim/',),
        'vertical_tags': ('kobi', 'retail'),
        'default_enabled': True,
        'sort': 81,
    },
    {
        'slug': 'p.accounting.timesheet',
        'name': 'Zaman & faturalama',
        'summary': 'Saat kaydı, personel ve proje bazlı takip.',
        'category': 'operasyon',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/zaman/',),
        'vertical_tags': ('kobi', 'agency'),
        'default_enabled': True,
        'sort': 82,
    },
    {
        'slug': 'p.accounting.projects',
        'name': 'Montaj programı',
        'summary': 'Proje kartları, günlük montaj takvimi, ekip ataması.',
        'category': 'operasyon',
        'parent_module': 'accounting',
        'route_prefixes': ('/muhasebe/projeler/',),
        'vertical_tags': ('kobi',),
        'default_enabled': True,
        'sort': 83,
    },
    {
        'slug': 'p.outreach.campaigns',
        'name': 'Kampanya & toplu mesaj',
        'summary': 'WhatsApp kampanyaları ve mesaj geçmişi.',
        'category': 'iletisim',
        'parent_module': 'outreach',
        'route_prefixes': (),
        'vertical_tags': ('kobi', 'agency', 'nonprofit'),
        'default_enabled': True,
        'sort': 80,
    },
)

# Sektör paketi: modül slug'ları + parçacık slug'ları
VERTICAL_CATALOG_PRESETS: dict[str, dict[str, tuple[str, ...]]] = {
    'kobi': {
        'modules': (
            'contact', 'services', 'accounting', 'outreach',
            'supplier_payables', 'e_invoice_bridge', 'project_costing', 'multi_cash', 'projects', 'timesheet',
            'integration_data_harvest',
            'integration_whatsapp_bridge', 'integration_whatsapp_api', 'integration_media', 'integration_weather',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.contact.teams',
            'p.accounting.personnel', 'p.accounting.payroll',
            'p.accounting.finance', 'p.accounting.sales',
            'p.accounting.cash', 'p.accounting.receivables', 'p.accounting.stock',
            'p.accounting.payables', 'p.accounting.multi_cash', 'p.accounting.project_costing',
            'p.accounting.e_export', 'p.accounting.timesheet', 'p.accounting.projects',
            'p.outreach.campaigns',
        ),
    },
    'retail': {
        'modules': (
            'contact', 'services', 'accounting',
            'integration_whatsapp_bridge', 'integration_media',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.contact.teams',
            'p.accounting.personnel', 'p.accounting.payroll',
            'p.accounting.finance', 'p.accounting.sales',
        ),
    },
    'healthcare': {
        'modules': (
            'contact', 'services', 'outreach',
            'integration_whatsapp_bridge', 'integration_media',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.teams', 'p.outreach.campaigns',
        ),
    },
    'nonprofit': {
        'modules': (
            'contact', 'outreach',
            'integration_whatsapp_api', 'integration_media',
        ),
        'particles': (
            'p.contact.customers', 'p.contact.firms', 'p.outreach.campaigns',
        ),
    },
    'universal': {
        'modules': ('contact', 'accounting', 'settings', 'integration_media'),
        'particles': (
            'p.contact.customers', 'p.accounting.finance', 'p.accounting.sales',
        ),
    },
}

LEGACY_MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    'tools': (
        'integration_whatsapp_bridge',
        'integration_whatsapp_api',
        'integration_media',
    ),
}


def particle_by_slug(slug: str) -> dict | None:
    for p in PARTICLES:
        if p['slug'] == slug:
            return dict(p)
    return None


def category_by_slug(slug: str) -> dict | None:
    for row in PARTICLE_CATEGORIES:
        if row[0] == slug:
            return {'slug': row[0], 'name': row[1], 'icon': row[2]}
    return None


def default_enabled_particle_slugs() -> list[str]:
    return [p['slug'] for p in PARTICLES if p.get('default_enabled')]


def vertical_preset_all_slugs(vertical_slug: str) -> tuple[str, ...]:
    from common.sector_catalog import normalize_sector_slug, sector_preset_all_slugs

    slug = normalize_sector_slug(vertical_slug)
    if slug in ('montaj_saha', 'bayi_servis', 'insaat_taahhut', 'hizmet_danismanlik', 'evde_bakim', 'stk_dernek'):
        return sector_preset_all_slugs(slug)
    preset = VERTICAL_CATALOG_PRESETS.get(vertical_slug, VERTICAL_CATALOG_PRESETS['kobi'])
    return preset['modules'] + preset['particles']


def particle_route_prefixes() -> list[tuple[str, str]]:
    pairs = []
    for p in PARTICLES:
        for prefix in p.get('route_prefixes', ()):
            pairs.append((prefix, p['slug']))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs
