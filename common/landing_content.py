"""Landing sayfası — vitrin metinleri ve özellik kataloğu."""

from __future__ import annotations

LANDING_VERTICAL_COPY: dict[str, dict] = {
    'kobi': {
        'badge': 'Modüler operasyon paneli · self-host',
        'headline': 'Müşteri, servis, satış, kasa ve ekibiniz tek panelde.',
        'lead': (
            'Montaj ve saha servis KOBİ’leri için tasarlanmış; modüller açılıp kapatılarak '
            'bayi ağları, hizmet firmaları ve iletişim odaklı ekipler de aynı altyapıyı kullanabilir. '
            'Rehber, yardım masası, ön muhasebe, WhatsApp ve medya — kendi sunucunuzda.'
        ),
        'highlights': (
            ('headphones', 'Yardım Masası', 'İş emri, saha planı, WhatsApp'),
            ('book-user', 'Rehber', 'Müşteri 360°, firma, ekip'),
            ('calculator', 'Muhasebe', 'Kasa, alacak, maaş, stok'),
            ('messages-square', 'İletişim', 'Kampanya ve mesaj kayıtları'),
            ('search', 'Hızlı arama', '/ ile sayfa ve kayıt bul'),
            ('bell', 'Bildirimler', 'Maaş ve alacak özeti'),
        ),
    },
}

LANDING_PILLARS: tuple[tuple[str, str], ...] = (
    (
        'Modüler yapı',
        'Rehber, servis, muhasebe ve iletişim modülleri; parçacıklarla (maaş, stok, teklif…) ihtiyaca göre açılır.',
    ),
    (
        'Tek müşteri kaydı',
        'Müşteri 360° — satış, servis, alacak ve mesaj geçmişi aynı kartta; veri tekrarı yok.',
    ),
    (
        'Operasyon muhasebesi',
        'Resmi e-defter değil: tahsilat, kasa, malzeme stoku, personel maaşı günlük karar için.',
    ),
    (
        'Rol bazlı erişim',
        'Muhasebe, saha, satış ve yönetici rolleri yalnızca yetkili ekranları görür.',
    ),
    (
        'Self-host',
        'Docker; Dokploy, Coolify, VPS. SQLite + medya volume — veriler sizde kalır.',
    ),
    (
        'WhatsApp entegrasyonu',
        'QR köprü veya Business API; servis durumu, kampanya ve alacak hatırlatma.',
    ),
)

LANDING_SERVICES_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('layout-dashboard', 'Durum özeti', 'Açık servisler, öncelik ve ekip dağılımı'),
    ('clipboard-list', 'Servis kayıtları', 'Müşteri, ürün, durum, personel ve notlar'),
    ('calendar-days', 'Saha planı', 'Günlük randevu takvimi; planlanan ziyaretler'),
    ('plus', 'Hızlı işlemler', 'Yeni kayıt, toplu durum/öncelik, personel atama'),
    ('printer', 'Yazdırma', 'Tekil ve toplu servis formu çıktısı'),
    ('message-circle', 'WhatsApp dağıtım', 'Durum değişiminde senaryo ve otomatik mesaj'),
    ('history', 'Geçmiş & geri al', 'Servis değişiklik geçmişi'),
    ('zap', 'Hızlı güncelleme', 'Listede durum, öncelik ve personel değiştirme'),
)

LANDING_REHBER_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('users', 'Müşteri kartları', 'İletişim, ürünler, sözleşme ve medya ekleri'),
    ('scan', 'Müşteri 360°', 'Satış, servis, alacak ve mesaj özeti tek ekran'),
    ('building-2', 'Firma rehberi', 'Etiket, bölge, çözüm ortağı türleri'),
    ('map-pin', 'Firma bul (Maps)', 'Google Maps arama, CSV dışa aktarım'),
    ('users-round', 'Saha ekipleri', 'Ekip tanımı, ürün yetkinliği, şirket hattı'),
    ('id-card', 'Personel yönetimi', 'Departman, ünvan, ekip; ofis ve saha kadrosu'),
    ('handshake', 'Çözüm ortağı ağı', 'Taşeron / freelancer kayıtları (opsiyonel parçacık)'),
)

LANDING_MUHASEBE_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('layout-grid', 'Finans özeti', 'Hub ekranı — dönem KPI ve kısayollar'),
    ('file-text', 'Teklifler', 'Ürün satırları; tek tıkla satışa dönüştürme'),
    ('badge-dollar-sign', 'Satış kayıtları', 'Peşinat, vade, proje referansı, pipeline'),
    ('hand-coins', 'Alacaklar', 'Bekleyen tahsilat, gecikme filtresi, WhatsApp hatırlatma'),
    ('landmark', 'Kasa', 'Açılış + gelir/gider + tahsilatlarla güncel nakit'),
    ('receipt', 'Gelir & gider', 'Kategori bazlı hareketler; yazdırma ve CSV'),
    ('wallet', 'Maaş & avans', 'Aylık döngü; brüt − avans = net; toplu ödeme'),
    ('package', 'Stok & reçete (BOM)', 'Malzeme stoku; satış/serviste otomatik düşüm'),
    ('truck', 'Tedarikçi borçları', 'Vade takibi; ödeme otomatik gider kaydı'),
    ('landmark', 'Çoklu kasa & banka', 'Nakit, banka, POS hesap bakiyeleri'),
    ('pie-chart', 'Proje kârlılığı', 'Satış geliri − proje gideri = marj'),
    ('calendar-days', 'Montaj programı', 'Günlük kurulum takvimi, ekip, hava durumu'),
    ('clock', 'Zaman kaydı', 'Personel saatleri ve faturalama durumu'),
    ('file-badge', 'Dış aktarım', 'Mali müşavir CSV paketi (Logo / Paraşüt)'),
    ('bar-chart-3', 'Raporlar', 'Maaş, satış, gelir-gider; yazdırma ve dönem filtresi'),
    ('arrow-up-down', 'Veri alışverişi', 'Maaş ve gelir-gider CSV içe/dışa aktarım'),
)

LANDING_OUTREACH_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('megaphone', 'Kampanyalar', 'Toplu WhatsApp gönderimi ve hedef listeler'),
    ('list', 'Kampanya mesajları', 'Gönderim geçmişi ve durum'),
    ('building-2', 'Firma mesajları', 'Rehber firmalarına giden iletişim kaydı'),
    ('users', 'Müşteri mesajları', 'Müşteri kartına bağlı mesaj arşivi'),
    ('id-card', 'Personel mesajları', 'Saha ekibi iletişim geçmişi'),
)

LANDING_INTEGRATION_DETAILS: tuple[tuple[str, str, str], ...] = (
    ('message-circle', 'WhatsApp Köprüsü (QR)', 'Hat bağlama, senaryo şablonları, servis bildirimleri'),
    ('cloud', 'WhatsApp Business API', 'Meta Cloud API — kampanya ve otomasyon'),
    ('map-pin', 'Firma & lead kazıma', 'Maps araması, etiketleme, hafıza listesi'),
    ('images', 'Medya kütüphanesi', 'Müşteri ve kampanya dosyaları; önizleme'),
    ('sparkles', 'Yapay zeka (opsiyonel)', 'Sohbet asistanı, servis raporlama paneli'),
)

LANDING_PLATFORM_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('search', 'Hızlı arama', '/ tuşu ile sayfa, işlem ve müşteri/servis kaydı arama'),
    ('bell', 'Bildirimler', 'Bekleyen maaş, gecikmiş alacak; okundu işaretleme'),
    ('messages-square', 'Ekip sohbeti', 'Genel ve özel kanallar; anlık mesajlaşma'),
    ('puzzle', 'Modül merkezi', 'Kurulu uygulamaları görüntüleme ve yönetim'),
    ('shield', 'Roller & izinler', 'Modül erişimi ve fonksiyon bazlı yetkilendirme'),
    ('sliders-horizontal', 'Site ayarları', 'Ürün, durum, öncelik katalogları; firma bilgisi'),
    ('database', 'Yedekleme', 'Süper admin SQLite yedeği (self-host)'),
)

LANDING_SETTINGS_FEATURES: tuple[tuple[str, str, str], ...] = (
    ('building-2', 'Firma bilgileri', 'Logo, site adı, iletişim'),
    ('package', 'Ürün kataloğu', 'Ortak ürün grupları — satış ve serviste paylaşılır'),
    ('wrench', 'Arıza / servis tipleri', 'Servis kayıtlarında kullanılan tipler'),
    ('list-checks', 'Durum & öncelik', 'İş akışı katalogları, renk kodları'),
    ('tags', 'Firma etiketleri', 'Rehber filtreleme ve sınıflandırma'),
    ('handshake', 'Çözüm ortağı türleri', 'Taşeron / partner sınıflandırması'),
)

from common.sector_catalog import landing_sectors_tuple

LANDING_SECTORS: tuple[tuple[str, str, str, str], ...] = landing_sectors_tuple()

LANDING_FLOW_SAHA: tuple[tuple[str, str, str, str, str], ...] = (
    ('border-violet-500/20 bg-violet-500/5', 'text-violet-400', '1', 'Rehber', 'Müşteri kartı, ürün ve sözleşme'),
    ('border-amber-500/20 bg-amber-500/5', 'text-amber-400', '2', 'Teklif', 'Ürün satırlarıyla teklif'),
    ('border-emerald-500/20 bg-emerald-500/5', 'text-emerald-400', '3', 'Satış & kasa', 'Tahsilat, alacak, kasa'),
    ('border-brand-500/20 bg-brand-500/5', 'text-brand-400', '4', 'Saha', 'Servis aç, planla, WhatsApp'),
)

LANDING_FLOW_HIZMET: tuple[tuple[str, str, str, str, str], ...] = (
    ('border-violet-500/20 bg-violet-500/5', 'text-violet-400', '1', 'Rehber', 'Müşteri ve firma kaydı'),
    ('border-amber-500/20 bg-amber-500/5', 'text-amber-400', '2', 'Teklif', 'Hizmet / proje teklifi'),
    ('border-emerald-500/20 bg-emerald-500/5', 'text-emerald-400', '3', 'Satış', 'Peşinat ve vade takibi'),
    ('border-blue-500/20 bg-blue-500/5', 'text-blue-400', '4', 'İletişim', 'Kampanya ve mesaj kaydı'),
)

LANDING_DEPLOY_PLATFORMS: tuple[str, ...] = (
    'Dokploy',
    'Coolify',
    '1Panel',
    'Portainer',
    'Docker Compose',
)

LANDING_AUDIENCE: tuple[str, ...] = (
    'Montaj, teknik servis ve saha ekipleri',
    'Bayi ve çözüm ortağı ağları',
    'B2B teklif, satış ve tahsilat takibi yapan KOBİ’ler',
    'Malzeme stokunu reçeteyle yöneten üretici / montaj işletmeleri',
    'Personel maaşı, avans ve departman kadrosunu Excel dışında yönetenler',
    'WhatsApp ile müşteri ve saha iletişimi kuran işletmeler',
    'Self-host ve veri egemenliği isteyen kurumsal ekipler',
)

# Geriye dönük — eski şablon anahtarları
LANDING_FLOW = LANDING_FLOW_SAHA

DEFAULT_LANDING_VERTICAL = 'kobi'


def build_landing_particle_groups() -> list[dict]:
    from common.module_particles import PARTICLES, category_by_slug

    groups: dict[str, dict] = {}
    for p in PARTICLES:
        cat = category_by_slug(p['category']) or {'name': p['category'], 'icon': 'layers'}
        slug = p['category']
        if slug not in groups:
            groups[slug] = {
                'slug': slug,
                'name': cat['name'],
                'icon': cat['icon'],
                'items': [],
            }
        groups[slug]['items'].append({
            'name': p['name'],
            'summary': p['summary'],
            'default_enabled': p.get('default_enabled', True),
        })
    order = ('rehber', 'operasyon', 'finans', 'ajans', 'iletisim')
    return [groups[s] for s in order if s in groups]
