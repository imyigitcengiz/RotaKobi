"""Ortak şablon bağlamı."""

from common import module_labels as ml
from common.capability_routing import resolve_capabilities_hub_url
from common.module_runtime import (
    build_module_sidebar,
    build_modules_nav_flags,
    build_particles_nav_short,
    get_enabled_module_slugs,
)


def gy_branding(request):
    """Modül adları — şablonlarda {{ gy.rehber }}, {{ gy.yardim_masasi }} vb."""
    return {
        'gy': {
            'app_name': ml.APP_NAME,
            'ana_panel': ml.ANA_PANEL,
            'modul_merkezi': ml.MODUL_MERKEZI,
            'entegrasyon_merkezi': ml.ENTEGRASYON_MERKEZI,
            'araclar': ml.ARACLAR,
            'medya_kutuphanesi': ml.MEDYA_KUTUPHANESI,
            'site_ayarlari': ml.SITE_AYARLARI,
            'iletisim_merkezi': ml.ILETISIM_MERKEZI,
            'rehber': ml.REHBER,
            'yardim_masasi': ml.YARDIM_MASASI,
            'satis_birimi': ml.SATIS_BIRIMI,
            'muhasebe': ml.MUHASEBE,
            'ym_ozet': ml.YM_OZET,
            'ym_kayitlar': ml.YM_KAYITLAR,
            'ym_saha_plani': ml.YM_SAHA_PLANI,
            'ym_durumlar': ml.YM_DURUMLAR,
            'ym_ariza': ml.YM_ARIZA_TIPLERI,
            'ym_oncelik': ml.YM_ONCELIKLER,
            'rehber_ozet': ml.REHBER_OZET,
            'rehber_musteriler': ml.REHBER_MUSTERILER,
            'rehber_firmalar': ml.REHBER_FIRMALAR,
            'rehber_firma_bul': ml.REHBER_FIRMA_BUL,
            'rehber_ekipler': ml.REHBER_EKIPLER,
            'rehber_personel': ml.REHBER_PERSONEL,
            'rehber_musteri_360': ml.REHBER_MUSTERI_360,
            'sb_ozet': ml.SB_OZET,
            'sb_kayitlar': ml.SB_KAYITLAR,
            'sb_teklifler': ml.SB_TEKLIFLER,
            'mh_ozet': ml.MH_OZET,
            'mh_maas_avans': ml.MH_MAAS_AVANS,
            'mh_personel': ml.MH_PERSONEL,
            'mh_raporlar': ml.MH_RAPORLAR,
            'mh_gelir_gider': ml.MH_GELIR_GIDER,
            'mh_kasa': ml.MH_KASA,
            'mh_stok': ml.MH_STOK,
            'mh_alacaklar': ml.MH_ALACAKLAR,
            'mh_veri_alisverisi': ml.MH_VERI_ALISVERISI,
            'mh_maas_raporu': ml.MH_MAAS_RAPORU,
            'mh_tagline': ml.MH_TAGLINE,
            'sb_rapor': ml.SB_RAPOR,
            'ortak_urunler': ml.ORTAK_URUNLER,
        },
    }


def module_install_context(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'modules_installed': {},
            'modules_nav': {},
            'particles_nav': {},
            'module_sidebar': {'groups': [], 'capabilities': [], 'integrations': []},
            'profile_sidebar': {'groups': [], 'capabilities': [], 'integrations': []},
            'capabilities_hub_url': None,
        }
    from common.request_cache import cache_get

    enabled_slugs = cache_get(request, 'enabled_module_slugs', get_enabled_module_slugs)
    installed = {slug: slug in enabled_slugs for slug in _all_module_slugs()}
    sidebar = cache_get(
        request,
        'module_sidebar',
        lambda: build_module_sidebar(user, request),
    )
    return {
        'modules_installed': installed,
        'modules_nav': cache_get(request, 'modules_nav', lambda: build_modules_nav_flags(user)),
        'particles_nav': cache_get(request, 'particles_nav', lambda: build_particles_nav_short(user)),
        'module_sidebar': sidebar,
        'profile_sidebar': sidebar,
        'capabilities_hub_url': resolve_capabilities_hub_url(),
    }


def _all_module_slugs():
    from common.module_catalog import MODULES
    return [m['slug'] for m in MODULES]
