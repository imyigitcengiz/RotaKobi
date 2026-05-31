"""Hızlı arama — sayfa ve işlem indeksi."""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse

from common.module_runtime import is_module_installed, module_available_for_nav, module_route_allowed


@dataclass(frozen=True)
class QuickSearchItem:
    title: str
    subtitle: str
    icon: str
    group: str
    url_name: str | None = None
    url: str | None = None
    keywords: tuple[str, ...] = ()
    perms_any: tuple[str, ...] = ('access.home',)
    module_slug: str | None = None
    kind: str = 'page'


def _item(
    title: str,
    subtitle: str,
    icon: str,
    group: str,
    url_name: str,
    *,
    keywords: tuple[str, ...] = (),
    perms_any: tuple[str, ...] = ('access.home',),
    module_slug: str | None = None,
    kind: str = 'page',
) -> QuickSearchItem:
    return QuickSearchItem(
        title=title,
        subtitle=subtitle,
        icon=icon,
        group=group,
        url_name=url_name,
        keywords=keywords,
        perms_any=perms_any,
        module_slug=module_slug,
        kind=kind,
    )


QUICK_SEARCH_ITEMS: tuple[QuickSearchItem, ...] = (
    _item('Ana Panel', 'Modül kısayolları', 'layout-grid', 'Genel', 'home'),
    _item('Modül Merkezi', 'Kurulu uygulamalar', 'puzzle', 'Genel', 'module_hub'),
    _item('Entegrasyon Merkezi', 'WhatsApp, medya, kazıma', 'zap', 'Genel', 'capabilities_hub'),
    _item('Bilgi bankası', 'Tanıtım yol haritası ve demo rehberi', 'book-open', 'Genel', 'introducer_knowledge_base', keywords=('tanıtım', 'demo', 'bilgi', 'rehber'), perms_any=('access.home',)),
    _item('Profil ayarları', 'Hesap ve avatar', 'user', 'Genel', 'profile_settings'),
    _item('Rehber özeti', 'Müşteri ve firma hub', 'book-user', 'Rehber', 'contact_hub', module_slug='contact', perms_any=('access.contact',)),
    _item('Müşteriler', 'Müşteri listesi', 'users', 'Rehber', 'customers', keywords=('müşteri', 'rehber'), perms_any=('access.contact', 'contact.customers_view', 'contact.customers'), module_slug='contact'),
    _item('Yeni müşteri', 'Müşteri kaydı oluştur', 'user-plus', 'Rehber', 'customer_create', keywords=('ekle', 'yeni'), perms_any=('contact.customers',), module_slug='contact', kind='action'),
    _item('Firma rehberi', 'Firma kayıtları', 'building-2', 'Rehber', 'contact_firmalar', keywords=('firma',), perms_any=('contact.firms',), module_slug='contact'),
    _item('Firma bul', 'Google Maps araması', 'map-pin', 'Rehber', 'contact_firma_bul', keywords=('maps', 'kazı'), perms_any=('contact.firms',), module_slug='integration_data_harvest'),
    _item('Ekipler', 'Saha servis ekipleri', 'users-round', 'Rehber', 'team_network', keywords=('ekip',), perms_any=('contact.teams',), module_slug='contact'),
    _item('Yardım Masası özeti', 'Durum paneli', 'layout-dashboard', 'Yardım Masası', 'dashboard', module_slug='services', perms_any=('access.services',)),
    _item('Servis kayıtları', 'Tüm servis iş emirleri', 'clipboard-list', 'Yardım Masası', 'services', keywords=('servis', 'kayıt'), perms_any=('access.services',), module_slug='services'),
    _item('Yeni servis kaydı', 'Servis aç', 'plus', 'Yardım Masası', 'service_create', keywords=('yeni', 'aç'), perms_any=('services.manage',), module_slug='services', kind='action'),
    _item('Saha planı', 'Günlük randevu takvimi', 'calendar-days', 'Yardım Masası', 'service_schedule', keywords=('takvim', 'plan'), perms_any=('access.services',), module_slug='services'),
    _item('Muhasebe özeti', 'Finans hub', 'calculator', 'Muhasebe', 'accounting_hub', module_slug='accounting', perms_any=('access.accounting',)),
    _item('Personel yönetimi', 'Departman, ekip, maaş', 'id-card', 'Muhasebe', 'accounting_personnel', keywords=('personel', 'kadro'), perms_any=('contact.personnel', 'access.accounting'), module_slug='accounting'),
    _item('Maaş & avans', 'Ödeme döngüsü', 'wallet', 'Muhasebe', 'accounting_payroll', keywords=('maaş', 'avans'), perms_any=('contact.payroll',), module_slug='accounting'),
    _item('Gelir & gider', 'Ofis giderleri', 'receipt', 'Muhasebe', 'accounting_finance', keywords=('gider', 'gelir'), perms_any=('accounting.finance',), module_slug='accounting'),
    _item('Kasa', 'Nakit özeti', 'landmark', 'Muhasebe', 'accounting_cash', keywords=('kasa', 'nakit'), perms_any=('accounting.finance',), module_slug='accounting'),
    _item('Stok & reçete', 'Malzeme stoku', 'package', 'Muhasebe', 'accounting_stock', keywords=('stok', 'malzeme'), perms_any=('accounting.finance',), module_slug='accounting'),
    _item('Tedarikçi borçları', 'Vade ve ödeme', 'truck', 'Muhasebe', 'accounting_payables', keywords=('tedarik', 'borç'), perms_any=('accounting.finance',), module_slug='supplier_payables'),
    _item('Kasa & banka', 'Çoklu hesap', 'landmark', 'Muhasebe', 'accounting_cash_accounts', keywords=('banka', 'hesap'), perms_any=('accounting.finance',), module_slug='multi_cash'),
    _item('Proje kârlılığı', 'Marj raporu', 'pie-chart', 'Muhasebe', 'accounting_project_costing', keywords=('kâr', 'maliyet'), perms_any=('accounting.finance',), module_slug='project_costing'),
    _item('Dış aktarım', 'Mali müşavir CSV', 'file-badge', 'Muhasebe', 'accounting_e_export', keywords=('e-fatura', 'export'), perms_any=('accounting.finance',), module_slug='e_invoice_bridge'),
    _item('Zaman kaydı', 'Saat & faturalama', 'clock', 'Muhasebe', 'accounting_timesheet', keywords=('zaman', 'saat'), perms_any=('accounting.finance',), module_slug='timesheet'),
    _item('Montaj programı', 'Günlük kurulum planı', 'calendar-days', 'Muhasebe', 'accounting_projects', keywords=('montaj', 'proje', 'takvim', 'program'), perms_any=('accounting.finance', 'access.accounting', 'services.manage', 'contact.teams'), module_slug='projects'),
    _item('Alacaklar', 'Bekleyen tahsilat', 'hand-coins', 'Muhasebe', 'accounting_receivables', keywords=('alacak', 'tahsilat'), perms_any=('sales.reports', 'sales.manage'), module_slug='accounting'),
    _item('Satış kayıtları', 'Pipeline listesi', 'list', 'Muhasebe', 'sales_lead_list', keywords=('satış',), perms_any=('access.accounting', 'sales.manage'), module_slug='accounting'),
    _item('Yeni satış', 'Satış kaydı oluştur', 'circle-plus', 'Muhasebe', 'sales_lead_create', keywords=('yeni satış',), perms_any=('sales.manage',), module_slug='accounting', kind='action'),
    _item('Teklifler', 'Teklif listesi', 'file-text', 'Muhasebe', 'sales_quote_list', keywords=('teklif',), perms_any=('sales.manage',), module_slug='accounting'),
    _item('Yeni teklif', 'Teklif hazırla', 'file-plus', 'Muhasebe', 'sales_quote_create', keywords=('teklif',), perms_any=('sales.manage',), module_slug='accounting', kind='action'),
    _item('Raporlar', 'Maaş ve satış raporları', 'bar-chart-3', 'Muhasebe', 'accounting_reports', keywords=('rapor',), perms_any=('contact.payroll', 'sales.reports', 'accounting.finance'), module_slug='accounting'),
    _item('Veri alışverişi', 'CSV içe/dışa aktarım', 'arrow-up-down', 'Muhasebe', 'accounting_data_exchange', keywords=('csv', 'import'), perms_any=('contact.payroll', 'accounting.finance', 'sales.export'), module_slug='accounting'),
    _item('İletişim Merkezi', 'Kampanya hub', 'messages-square', 'İletişim', 'outreach_hub', module_slug='outreach', perms_any=('access.outreach',)),
    _item('Kampanyalar', 'Toplu mesaj gönderimi', 'megaphone', 'İletişim', 'outreach_campaigns', keywords=('kampanya',), perms_any=('access.outreach',), module_slug='outreach'),
    _item('WhatsApp bağlan', 'Köprü ve senaryolar', 'message-circle', 'Araçlar', 'tools_whatsapp_baglan', keywords=('whatsapp',), perms_any=('tools.whatsapp',), module_slug='integration_whatsapp_bridge'),
    _item('Medya kütüphanesi', 'Yüklenen dosyalar', 'images', 'Araçlar', 'tools_media_library', keywords=('medya', 'dosya'), perms_any=('tools.media',), module_slug='integration_media'),
    _item('Araçlar', 'Entegrasyon kısayolları', 'hammer', 'Araçlar', 'tools_hub', keywords=('araç',), perms_any=('access.tools',)),
    _item('Site ayarları', 'Firma bilgileri', 'building-2', 'Ayarlar', 'settings_genel', keywords=('ayar', 'firma'), perms_any=('access.settings',), module_slug='settings'),
    _item('Ürün kataloğu', 'Ortak ürünler', 'package', 'Ayarlar', 'settings_products', keywords=('ürün',), perms_any=('access.settings',), module_slug='settings'),
    _item('Durumlar', 'Servis durum seçenekleri', 'list-checks', 'Ayarlar', 'settings_statuses', keywords=('durum',), perms_any=('access.settings',), module_slug='settings'),
    _item('Öncelikler', 'Servis öncelik seçenekleri', 'flag', 'Ayarlar', 'settings_priorities', keywords=('öncelik',), perms_any=('access.settings',), module_slug='settings'),
    _item('Arıza tipleri', 'Servis tip kataloğu', 'wrench', 'Ayarlar', 'settings_service_types', keywords=('arıza', 'tip'), perms_any=('access.settings',), module_slug='settings'),
    _item('Firma etiketleri', 'Rehber etiketleri', 'tags', 'Ayarlar', 'settings_tags', keywords=('etiket',), perms_any=('access.settings',), module_slug='settings'),
)


def _user_can_see_item(user, item: QuickSearchItem) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if item.module_slug:
        if item.module_slug == 'settings':
            if not user.has_perm_codename('access.settings'):
                return False
        elif not module_route_allowed(item.module_slug):
            return False
        elif not module_available_for_nav(user, item.module_slug):
            return False
    if item.perms_any:
        return user.has_any_perm_codename(*item.perms_any)
    return True


def _resolve_url(item: QuickSearchItem) -> str | None:
    if item.url and isinstance(item.url, str):
        return item.url
    if not item.url_name:
        return None
    try:
        return reverse(item.url_name)
    except NoReverseMatch:
        return None


def _match_query(item: QuickSearchItem, q: str) -> bool:
    if not q:
        return True
    blob = ' '.join((item.title, item.subtitle, item.group, *item.keywords)).lower()
    return q in blob or any(part in blob for part in q.split() if len(part) >= 2)


def build_quick_search_results(user, query: str = '', *, limit: int = 20) -> list[dict]:
    q = (query or '').strip().lower()
    out: list[dict] = []
    for item in QUICK_SEARCH_ITEMS:
        if not _user_can_see_item(user, item):
            continue
        if q and not _match_query(item, q):
            continue
        url = _resolve_url(item)
        if not url:
            continue
        out.append({
            'title': item.title,
            'subtitle': item.subtitle,
            'url': url,
            'icon': item.icon,
            'group': item.group,
            'kind': item.kind,
        })
        if len(out) >= limit:
            break
    return out


def search_entities(user, query: str, *, limit: int = 5) -> list[dict]:
    q = (query or '').strip()
    if len(q) < 2:
        return []

    results: list[dict] = []

    if user.has_any_perm_codename('contact.customers_view', 'contact.customers'):
        from customers.models import Customer

        for customer in Customer.objects.filter(name__icontains=q).order_by('name')[:limit]:
            try:
                url = reverse('customer_update', kwargs={'pk': customer.pk})
            except NoReverseMatch:
                url = reverse('customers')
            results.append({
                'title': customer.name,
                'subtitle': 'Müşteri kaydı',
                'url': url,
                'icon': 'user',
                'group': 'Kayıtlar',
                'kind': 'record',
            })

    if user.has_perm_codename('access.services'):
        from services.models import ServiceRecord

        for service in (
            ServiceRecord.objects.select_related('customer')
            .filter(customer__name__icontains=q)
            .order_by('-updated_at')[:limit]
        ):
            try:
                url = reverse('service_update', kwargs={'pk': service.pk})
            except NoReverseMatch:
                url = reverse('services')
            results.append({
                'title': f'#{service.pk} · {service.customer.name}',
                'subtitle': 'Servis kaydı',
                'url': url,
                'icon': 'headphones',
                'group': 'Kayıtlar',
                'kind': 'record',
            })

    return results[:limit]
