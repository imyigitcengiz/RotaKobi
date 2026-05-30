"""Landing sayfası — sektör profiline göre vitrin metinleri."""

from __future__ import annotations

LANDING_VERTICAL_COPY: dict[str, dict] = {
    'kobi': {
        'badge': 'KOBİ & saha servis',
        'headline': 'Müşteri, servis, satış ve saha ekibiniz tek panelde birleşsin.',
        'lead': (
            'Montaj ve teknik servis ekipleri ile B2B satış yapan işletmeler için '
            'yardım masası, müşteri rehberi, personel, bordro ve WhatsApp — aynı veri üzerinde.'
        ),
        'highlights': (
            ('headphones', 'Yardım Masası', 'Saha servis iş emirleri'),
            ('users-round', 'Saha Ekipleri', 'Montaj ve teknik kadro'),
            ('wallet', 'Maaş & Avans', 'Brüt − avans = net'),
            ('message-circle', 'WhatsApp', 'Ekip ve müşteri iletişimi'),
        ),
    },
    'agency': {
        'badge': 'Ajans & proje',
        'headline': 'Retainer, freelancer ve müşteri pipeline tek stüdyoda.',
        'lead': (
            'Dijital ajans ve proje ekipleri için retainer takibi, müşteri kartları, '
            'freelancer ağı ve proje satışı — personel ve saha servisi olmadan.'
        ),
        'highlights': (
            ('palette', 'Retainer Stüdyosu', 'Aylık proje ve MRR'),
            ('sparkles', 'Müşteri & Marka', 'Ajans müşteri kartları'),
            ('user-plus', 'Freelancer Ağı', 'Taşeron ve tasarımcı kadrosu'),
            ('trending-up', 'Proje Pipeline', 'Teklif ve satış takibi'),
        ),
    },
    'retail': {
        'badge': 'Perakende & bayi',
        'headline': 'Mağaza, bayi ve tedarikçi ağınızı yönetin.',
        'lead': 'Perakende ve bayi ağları için müşteri, mağaza destek ve satış uygulamaları.',
        'highlights': (
            ('store', 'Mağaza Destek', 'Şube talepleri'),
            ('users', 'Müşteri & Bayi', 'Bayi kartları'),
            ('building-2', 'Tedarikçi', 'Firma rehberi'),
            ('badge-dollar-sign', 'Satış', 'Kayıt ve tahsilat'),
        ),
    },
    'healthcare': {
        'badge': 'Sağlık & randevu',
        'headline': 'Hasta kaydı ve randevu iletişimi tek yerde.',
        'lead': 'Klinik ve sağlık hizmetleri için hasta rehberi, randevu ve kampanya uygulamaları.',
        'highlights': (
            ('calendar', 'Randevular', 'Takvim ve hatırlatma'),
            ('users', 'Hasta Rehberi', 'Müşteri kartları'),
            ('megaphone', 'Kampanyalar', 'WhatsApp bilgilendirme'),
            ('message-circle', 'WhatsApp', 'Hatırlatma mesajları'),
        ),
    },
    'nonprofit': {
        'badge': 'STK & topluluk',
        'headline': 'Üye, bağışçı ve kampanya yönetimi.',
        'lead': 'Dernek ve topluluklar için üye rehberi, firma ilişkileri ve iletişim kampanyaları.',
        'highlights': (
            ('heart-handshake', 'Üye Rehberi', 'Üye ve gönüllü kartları'),
            ('building-2', 'Kurumlar', 'Firma ve sponsor'),
            ('megaphone', 'Kampanyalar', 'Toplu iletişim'),
            ('cloud', 'WhatsApp API', 'Resmi hat gönderimi'),
        ),
    },
}

DEFAULT_LANDING_VERTICAL = 'kobi'
