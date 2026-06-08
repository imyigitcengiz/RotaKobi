"""Tanıtım yapan kullanıcılar için yol haritası ve bilgi bankası — landing içeriğinden türetilir."""

from __future__ import annotations

from common.landing_content import (
    LANDING_AUDIENCE,
    LANDING_DEPLOY_PLATFORMS,
    LANDING_FLOW_HIZMET,
    LANDING_FLOW_SAHA,
    LANDING_INTEGRATION_DETAILS,
    LANDING_MUHASEBE_FEATURES,
    LANDING_OUTREACH_FEATURES,
    LANDING_PILLARS,
    LANDING_PLATFORM_FEATURES,
    LANDING_REHBER_FEATURES,
    LANDING_SECTORS,
    LANDING_SERVICES_FEATURES,
    LANDING_SETTINGS_FEATURES,
    LANDING_VERTICAL_COPY,
    DEFAULT_LANDING_VERTICAL,
)


def _step(
    order: int,
    title: str,
    duration: str,
    goal: str,
    talking_points: tuple[str, ...],
    demo_screens: tuple[dict, ...] = (),
    checklist: tuple[str, ...] = (),
    tips: tuple[str, ...] = (),
) -> dict:
    return {
        'order': order,
        'title': title,
        'duration': duration,
        'goal': goal,
        'talking_points': talking_points,
        'demo_screens': demo_screens,
        'checklist': checklist,
        'tips': tips,
    }


def _screen(label: str, url_name: str = '', note: str = '') -> dict:
    return {'label': label, 'url_name': url_name, 'note': note}


INTRODUCER_JOURNEYS: tuple[dict, ...] = (
    {
        'slug': 'saha-servis-tam',
        'icon': 'wrench',
        'title': 'Tam demo — saha servis KOBİ',
        'duration': '45–60 dk',
        'audience': 'Montaj, teknik servis, üretici-montaj işletmeleri',
        'summary': (
            'Tek müşteri kaydından teklife, satışa, saha planına ve tahsilata uzanan uçtan uca hikâye. '
            'Ana hedef kitle için en güçlü anlatım.'
        ),
        'steps': (
            _step(
                1, 'Açılış ve değer önerisi', '5 dk',
                'Dinleyicinin Excel / dağınık araçlar yerine neden tek panel istediğini netleştirin.',
                (
                    'Kobi Hub resmi muhasebe değil — günlük operasyon kararları için ön muhasebe.',
                    'Modüller ve parçacıklar ihtiyaca göre açılır; aynı altyapı bayi ve hizmet profiline de uyar.',
                    'Veriler self-host: Docker, kendi sunucunuz, SQLite + medya volume.',
                ),
                checklist=(
                    'Dinleyici profilini sorun: saha ekip var mı, stok/reçete takibi gerekli mi?',
                    'Rakip veya mevcut araç (Excel, Logo, saha uygulaması) not alın.',
                ),
                tips=('Landing #moduller bölümünü kısa gösterin; giriş yapmadan vitrin mümkün.',),
            ),
            _step(
                2, 'Rehber ve Müşteri 360°', '8 dk',
                'Tek müşteri kartında satış, servis, alacak ve mesajın birleştiğini gösterin.',
                (
                    'Müşteri kartı: iletişim, ürünler, sözleşme, medya ekleri tek yerde.',
                    '360° özet: satış geçmişi, açık servisler, bekleyen alacak, mesajlar — veri tekrarı yok.',
                    'Personel: departman, ünvan, ekip; ofis ve saha kadrosu ayrı yönetilir.',
                ),
                demo_screens=(
                    _screen('Rehber özeti', 'contact_hub', 'Hub istatistikleri'),
                    _screen('Müşteri listesi', 'customers', '360° linki örnek müşteriden'),
                    _screen('Personel', 'contact_personnel', 'Departman / ünvan sütunları'),
                ),
                checklist=('En az bir dolu müşteri kartı hazır olsun.', '360° ekranında en az bir satış ve bir servis kaydı görünsün.'),
            ),
            _step(
                3, 'Teklif → satış → alacak', '10 dk',
                'Pipeline ve tahsilat takibini operasyon diliyle anlatın.',
                (
                    'Teklif: ürün satırları; onay sonrası tek tıkla satışa dönüşür.',
                    'Satış: peşinat, vade, proje referansı; alacak otomatik oluşur.',
                    'Alacaklar: gecikme filtresi, WhatsApp hatırlatma; kasa ile nakit görünürlüğü.',
                ),
                demo_screens=(
                    _screen('Teklif listesi', 'sales_quote_list'),
                    _screen('Yeni teklif', 'sales_quote_create', 'Satışa çevir butonunu vurgulayın'),
                    _screen('Alacaklar', 'accounting_receivables', 'Gecikmiş satır varsa gösterin'),
                    _screen('Kasa', 'accounting_cash', 'Açılış + hareketler'),
                ),
            ),
            _step(
                4, 'Stok ve reçete (BOM)', '7 dk',
                'Ürün stoklanmaz; malzeme reçeteyle servis/satişte düşer — KOBİ montajcıları için kritik.',
                (
                    'Malzeme stoku ayrı; satış veya servis kapanınca reçeteye göre otomatik düşüm.',
                    'Operasyon muhasebesi: maliyet tahmini için, e-defter yerine günlük stok görünürlüğü.',
                ),
                demo_screens=(
                    _screen('Stok & reçete', 'accounting_stock', 'BOM satırları ve hareket geçmişi'),
                    _screen('Tedarikçi borçları', 'accounting_payables'),
                    _screen('Proje kârlılığı', 'accounting_project_costing'),
                    _screen('Çoklu hesap', 'accounting_cash_accounts'),
                ),
                tips=('Stok parçacığı kapalıysa Modül merkezinden açmayı gösterin.',),
            ),
            _step(
                5, 'Yardım masası ve saha planı', '12 dk',
                'Saha ekibinin günlük iş akışını canlı gösterin.',
                (
                    'Servis kaydı: müşteri, ürün, durum, öncelik, atanan personel.',
                    'Saha planı: günlük randevu takvimi; planlanan ziyaretler.',
                    'Listede hızlı güncelleme: durum, öncelik, personel değiştirme.',
                    'Durum değişiminde WhatsApp senaryosu (köprü veya API).',
                ),
                demo_screens=(
                    _screen('Durum özeti', 'dashboard'),
                    _screen('Servis kayıtları', 'services', 'Inline düzenleme'),
                    _screen('Saha planı', 'service_schedule', 'Takvim görünümü'),
                    _screen('Yeni servis', 'service_create'),
                ),
                checklist=('WhatsApp köprüsü bağlı veya demo senaryosu hazır olsun.',),
            ),
            _step(
                6, 'Platform: arama, bildirim, roller', '5 dk',
                'Günlük kullanım kolaylığı ve güvenlik mesajı.',
                (
                    '/ tuşu ile hızlı arama: sayfa, müşteri, servis kaydı.',
                    'Bildirimler: bekleyen maaş, gecikmiş alacak özeti.',
                    'Rol bazlı erişim: muhasebe, saha, satış yalnızca yetkili ekranları görür.',
                ),
                demo_screens=(
                    _screen('Abonelik modülleri', 'subscription_dashboard'),
                    _screen('Ana panel', 'home'),
                ),
                tips=('Klavyede / tuşuna basarak hızlı aramayı canlı gösterin.',),
            ),
            _step(
                7, 'Kapanış ve sonraki adımlar', '5 dk',
                'Kurulum, pilot ve modül profili kararını netleştirin.',
                (
                    'Self-host: Dokploy / Coolify overlay hazır; domain → app:80.',
                    'Pilot: tek ekip, sınırlı modül seti; 2–4 hafta geri bildirim.',
                    'Sektöre göre servis veya muhasebe modülü kapatılabilir.',
                ),
                checklist=(
                    'Demo ortamı mı canlı kurulum mu netleştirin.',
                    'İletişim kişisi ve karar tarihi alın.',
                ),
            ),
        ),
    },
    {
        'slug': 'hizmet-hizli',
        'icon': 'briefcase',
        'title': 'Hızlı demo — hizmet & danışmanlık',
        'duration': '20–30 dk',
        'audience': 'Danışmanlık, ajans benzeri, saha ekibi olmayan ekipler',
        'summary': 'Saha modülü kapalı veya ikincil; teklif, satış, kasa ve iletişim odaklı kısa tur.',
        'steps': (
            _step(
                1, 'Profil ve modül seçimi', '3 dk',
                'Aynı yazılımın farklı modül profiliyle hizmet firmasına uyduğunu gösterin.',
                (
                    'Yardım masası modülü kapalı veya sınırlı; teklif ve satış ön planda.',
                    'Rehber: müşteri ve firma kaydı ortak veri tabanı.',
                ),
                demo_screens=(_screen('Abonelik modülleri', 'subscription_dashboard', 'Servis modülünün kapalı olduğunu gösterin'),),
            ),
            _step(
                2, 'Teklif ve satış', '8 dk',
                'Proje / hizmet teklifinden tahsilata.',
                (
                    'Teklif satırları; onay sonrası satış kaydı.',
                    'Peşinat ve vade; alacak takibi ve kasa özeti.',
                ),
                demo_screens=(
                    _screen('Teklifler', 'sales_quote_list'),
                    _screen('Satış kayıtları', 'sales_lead_list'),
                    _screen('Muhasebe özeti', 'accounting_hub'),
                ),
            ),
            _step(
                3, 'İletişim ve kampanya', '7 dk',
                'Müşteri ilişkisi ve toplu mesaj (opsiyonel parçacık).',
                (
                    'Kampanya: hedef liste, WhatsApp Business API ile toplu gönderim.',
                    'Mesaj geçmişi müşteri kartına bağlı arşivlenir.',
                ),
                demo_screens=(
                    _screen('İletişim merkezi', 'outreach_hub'),
                    _screen('Kampanyalar', 'outreach_campaigns'),
                ),
                tips=('İletişim modülü kapalıysa bu adımı atlayın; rehber + muhasebe ile devam edin.',),
            ),
            _step(
                4, 'Kapanış', '3 dk',
                'Hizmet profili kurulum notları.',
                (
                    'Parçacıklar: maaş, stok kapalı; teklif ve alacak açık.',
                    'Self-host veya yönetilen demo ortamı seçenekleri.',
                ),
            ),
        ),
    },
    {
        'slug': 'demo-hazirlik',
        'icon': 'clipboard-check',
        'title': 'Demo öncesi hazırlık',
        'duration': '30–45 dk (sunumdan önce)',
        'audience': 'Tanıtım yapan ekip, satış, danışman',
        'summary': 'Canlı demo öncesi ortam, veri ve anlatım kontrol listesi.',
        'steps': (
            _step(
                1, 'Ortam ve erişim', '10 dk',
                'Giriş, roller ve modül durumunu doğrulayın.',
                (
                    'Demo kullanıcısı: mümkünse yönetici değil, tipik saha/satış rolü ile gösterin.',
                    'Modül merkezi: hedef sektöre uygun açık/kapalı modüller.',
                    'Site ayarları: firma adı, logo — dinleyicinin markası veya nötr demo markası.',
                ),
                demo_screens=(
                    _screen('Site ayarları', 'settings_genel'),
                    _screen('Abonelik modülleri', 'subscription_dashboard'),
                ),
                checklist=(
                    'Giriş URL ve demo hesap şifresi hazır.',
                    'HTTPS ve mobil görünüm test edildi.',
                    'WhatsApp köprüsü veya API token (mesaj demosu için).',
                ),
            ),
            _step(
                2, 'Örnek veri', '15 dk',
                'Boş ekran yerine gerçekçi senaryo.',
                (
                    'En az 3 müşteri; biri dolu 360° kart.',
                    'Açık servis, gecikmiş alacak, bugünkü saha planı kaydı.',
                    'Bir teklif taslak, bir onaylı satış.',
                ),
                checklist=(
                    'Stok/reçete demosu için malzeme hareketi görünür.',
                    'Personel kayıtlarında departman ve ünvan dolu.',
                ),
            ),
            _step(
                3, 'Anlatım materyali', '10 dk',
                'Yol haritası ve itiraz cevapları.',
                (
                    'Bu bilgi bankasındaki sektör kartına göre vurgu değiştirin.',
                    'Landing sayfasını paylaşılabilir link olarak gönderin (/).',
                    'Logo / e-fatura beklentisi varsa operasyon muhasebesi sınırını önceden netleştirin.',
                ),
                demo_screens=(_screen('Tanıtım sayfası', 'landing', 'Herkese açık'),),
            ),
        ),
    },
    {
        'slug': 'sektor-secimi',
        'icon': 'map',
        'title': 'Sektöre göre anlatım',
        'duration': 'Referans — sunum sırasında',
        'audience': 'Karışık sektörlü toplantılar, ön görüşmeler',
        'summary': 'Dinleyici sektörüne göre hangi modül ve akışın öne çıkarılacağı.',
        'steps': (
            _step(
                1, 'Montaj & saha servis', '—',
                'Tam uyum — ana hikâye.',
                (
                    'Akış: Rehber → Teklif → Satış & kasa → Saha.',
                    'Stok/reçete, saha planı, WhatsApp durum bildirimi vurgula.',
                    '"Tam demo — saha servis KOBİ" yolunu izleyin.',
                ),
            ),
            _step(
                2, 'Bayi servis ağı', '—',
                'Çok nokta, garanti, alacak.',
                (
                    'Alacak takibi ve firma rehberi öne çıkar.',
                    'Ekip ve personel atama; bölgesel servis dağılımı.',
                ),
            ),
            _step(
                3, 'İnşaat & taahhüt', '—',
                'Proje satışı ve malzeme.',
                (
                    'Proje referanslı satış; malzeme reçetesi.',
                    'Saha ekip planı ve saha planı takvimi.',
                ),
            ),
            _step(
                4, 'Hizmet & danışmanlık', '—',
                'Saha modülü ikincil veya kapalı.',
                (
                    'Akış: Rehber → Teklif → Satış → İletişim.',
                    '"Hızlı demo — hizmet" yolunu kullanın.',
                ),
            ),
            _step(
                5, 'STK & dernek', '—',
                'Kısmi uyum — modül profili kritik.',
                (
                    'Kampanya ve rehber; servis/muhasebe genelde kapalı.',
                    'Beklenti yönetimi: tam ERP değil, ilişki ve iletişim merkezi.',
                ),
            ),
        ),
    },
)

INTRODUCER_FAQ: tuple[tuple[str, str], ...] = (
    (
        'Logo, Mikro veya resmi muhasebe yerine geçer mi?',
        'Hayır. Kobi Hub operasyon ve ön muhasebe içindir: tahsilat, kasa, stok, maaş, servis. '
        'E-defter ve resmi muhasebe entegrasyonu yol haritasındadır; günlük saha kararları için tasarlanmıştır.',
    ),
    (
        'Bulut mu, self-host mu?',
        'Self-host odaklı: Docker Compose, Dokploy, Coolify, VPS. Veriler sizde kalır; SQLite + medya volume.',
    ),
    (
        'Modülleri kapatabilir miyiz?',
        'Evet. Modül merkezi ve parçacıklar (teklif, stok, maaş vb.) ihtiyaca göre açılır/kapanır.',
    ),
    (
        'WhatsApp nasıl çalışır?',
        'İki yol: QR köprü (saha hatları, servis bildirimi) ve Meta Business API (kampanya, toplu mesaj).',
    ),
    (
        'Kaç kullanıcı desteklenir?',
        'KOBİ ölçeği: onlarca eşzamanlı kullanıcı self-host SQLite ile tipik senaryo. '
        'Büyük ekipler için PostgreSQL yol haritasında.',
    ),
    (
        'Demo hesabı nasıl verilir?',
        'Hesaplar yönetici tarafından oluşturulur. Tanıtım öncesi rol ve modül profili tanımlayın.',
    ),
)

INTRODUCER_OBJECTIONS: tuple[tuple[str, str], ...] = (
    (
        'Zaten Excel ile idare ediyoruz.',
        'Excel tek müşteri görünümü, saha planı ve otomatik stok düşümü vermez. '
        '360° kart ve WhatsApp senaryolarını 10 dakikada gösterin; Excel\'in kırıldığı noktayı somutlaştırın.',
    ),
    (
        'Logo kullanıyoruz, buna gerek yok.',
        'Kobi Hub Logo\'nun yerine değil; saha ekibi, servis, teklif ve operasyon kasasının yanında. '
        'Resmi muhasebe ayrı kalır, operasyon hızlanır.',
    ),
    (
        'Çok karmaşık görünüyor.',
        'Modüler yapı: sadece rehber + servis ile başlayın; muhasebe parçacıklarını sonra açın. '
        'Hızlı arama (/) ile eğitim süresini kısaltın.',
    ),
    (
        'Verilerimiz güvende mi?',
        'Self-host: veritabanı ve medya sizin sunucunuzda. Rol bazlı erişim; yedekleme süper admin araçlarında.',
    ),
)

MODULE_REFERENCE_SECTIONS: tuple[dict, ...] = (
    {
        'slug': 'rehber',
        'icon': 'book-user',
        'title': 'Rehber',
        'features': LANDING_REHBER_FEATURES,
    },
    {
        'slug': 'yardim-masasi',
        'icon': 'headphones',
        'title': 'Yardım Masası',
        'features': LANDING_SERVICES_FEATURES,
    },
    {
        'slug': 'muhasebe',
        'icon': 'calculator',
        'title': 'Muhasebe',
        'features': LANDING_MUHASEBE_FEATURES,
    },
    {
        'slug': 'iletisim',
        'icon': 'messages-square',
        'title': 'İletişim',
        'features': LANDING_OUTREACH_FEATURES,
    },
    {
        'slug': 'entegrasyon',
        'icon': 'plug',
        'title': 'Entegrasyonlar',
        'features': LANDING_INTEGRATION_DETAILS,
    },
    {
        'slug': 'platform',
        'icon': 'layers',
        'title': 'Platform',
        'features': LANDING_PLATFORM_FEATURES,
    },
    {
        'slug': 'ayarlar',
        'icon': 'sliders-horizontal',
        'title': 'Site ayarları',
        'features': LANDING_SETTINGS_FEATURES,
    },
)


def get_journey(slug: str | None) -> dict | None:
    if not slug:
        return INTRODUCER_JOURNEYS[0] if INTRODUCER_JOURNEYS else None
    for journey in INTRODUCER_JOURNEYS:
        if journey['slug'] == slug:
            return journey
    return None


def build_introducer_context() -> dict:
    vertical = LANDING_VERTICAL_COPY.get(DEFAULT_LANDING_VERTICAL, {})
    return {
        'introducer_journeys': INTRODUCER_JOURNEYS,
        'introducer_faq': INTRODUCER_FAQ,
        'introducer_objections': INTRODUCER_OBJECTIONS,
        'introducer_module_sections': MODULE_REFERENCE_SECTIONS,
        'introducer_pillars': LANDING_PILLARS,
        'introducer_sectors': LANDING_SECTORS,
        'introducer_flow_saha': LANDING_FLOW_SAHA,
        'introducer_flow_hizmet': LANDING_FLOW_HIZMET,
        'introducer_deploy_platforms': LANDING_DEPLOY_PLATFORMS,
        'introducer_audience': LANDING_AUDIENCE,
        'introducer_vertical_copy': vertical,
    }
