"""CSV içe aktarma türleri — alan şemaları ve izinler."""

from __future__ import annotations

from common.csv_mapping import ImportField

FINANCE_FIELDS = (
    ImportField('type', 'Tür', required=True, aliases=('TÜR', 'TUR', 'TYPE', 'GELIR_GIDER')),
    ImportField('category', 'Kategori', aliases=('KATEGORİ', 'KATEGORI', 'CATEGORY')),
    ImportField('title', 'Açıklama', required=True, aliases=('AÇIKLAMA', 'ACIKLAMA', 'BAŞLIK', 'BASLIK', 'TITLE')),
    ImportField('amount', 'Tutar', required=True, aliases=('TUTAR', 'MİKTAR', 'MIKTAR', 'AMOUNT')),
    ImportField('date', 'Tarih', aliases=('TARİH', 'TARIH', 'DATE')),
    ImportField('account', 'Hesap', aliases=('HESAP', 'KASA', 'ACCOUNT')),
    ImportField('sales_id', 'Satış ID', aliases=('SATIŞ_ID', 'SATIS_ID', 'SALES_ID')),
    ImportField('customer', 'Müşteri', aliases=('MÜŞTERİ', 'MUSTERI', 'SATIŞ_ETİKET', 'SATIS_ETIKET', 'AD SOYAD')),
    ImportField('project', 'Proje', aliases=('PROJE', 'PROJECT')),
    ImportField('notes', 'Not', aliases=('NOT', 'NOTLAR', 'NOTES')),
)

PAYROLL_FIELDS = (
    ImportField('period', 'Dönem', aliases=('DÖNEM', 'DONEM', 'PERIOD')),
    ImportField('personnel', 'Personel', required=True, aliases=('PERSONEL', 'AD SOYAD', 'AD')),
    ImportField('type', 'Tür', required=True, aliases=('TÜR', 'TUR', 'TYPE')),
    ImportField('amount', 'Tutar', required=True, aliases=('TUTAR', 'MİKTAR', 'MIKTAR')),
    ImportField('date', 'Tarih', aliases=('TARİH', 'TARIH', 'ÖDEME TARİHİ', 'ODEME TARIHI')),
    ImportField('notes', 'Not', aliases=('NOT', 'NOTLAR')),
)

SALES_FIELDS = (
    ImportField('customer_name', 'Müşteri adı', required=True, aliases=('AD SOYAD', 'MÜŞTERİ', 'MUSTERI', 'AD')),
    ImportField('phone', 'Telefon', aliases=('TELEFON', 'TEL', 'PHONE')),
    ImportField('region', 'Bölge', aliases=('YER', 'BÖLGE', 'BOLGE', 'REGION')),
    ImportField('project', 'Proje', aliases=('PROJE', 'PROJE ADI')),
    ImportField('date', 'Satış tarihi', aliases=('TARİH', 'TARIH', 'SATIŞ TARİHİ')),
    ImportField('total', 'Toplam', aliases=('TOPLAM', 'TUTAR', 'SATIŞ TUTARI')),
    ImportField('down_payment', 'Peşinat', aliases=('PEŞİNAT', 'PESINAT')),
    ImportField('notes', 'Not', aliases=('NOT', 'NOTLAR')),
)

CUSTOMER_FIELDS = (
    ImportField('name', 'Müşteri adı', required=True, aliases=('AD SOYAD', 'MÜŞTERİ', 'MUSTERI', 'AD', 'NAME')),
    ImportField('phone', 'Telefon', aliases=('TELEFON', 'TEL')),
    ImportField('region', 'Bölge', aliases=('YER', 'BÖLGE', 'BOLGE')),
    ImportField('address', 'Adres', aliases=('ADRES', 'ADDRESS')),
    ImportField('contract_date', 'Sözleşme tarihi', aliases=('SÖZLEŞME', 'SOZLESME', 'SÖZLEŞME TARİHİ')),
)

FIRM_FIELDS = (
    ImportField('name', 'Firma adı', required=True, aliases=('FIRMA ADI', 'FIRMA ADI', 'FIRMA', 'NAME', 'AD')),
    ImportField('address', 'Adres', aliases=('ADRES', 'ADDRESS')),
    ImportField('phone', 'Telefon', aliases=('TELEFON', 'TEL')),
    ImportField('website', 'Web sitesi', aliases=('WEB SITESI', 'WEB', 'WEBSITE')),
    ImportField('region', 'Bölge', aliases=('YER', 'BÖLGE', 'BOLGE', 'REGION')),
    ImportField('notes', 'Not', aliases=('NOT', 'NOTLAR')),
)

IMPORT_TYPES: dict[str, dict] = {
    'finance': {
        'label': 'Gelir & gider',
        'icon': 'receipt',
        'color': 'emerald',
        'permission': 'accounting.finance',
        'fields': FINANCE_FIELDS,
        'redirect_name': 'accounting_finance',
        'sample_hint': 'TÜR; KATEGORİ; AÇIKLAMA; TUTAR; TARİH; HESAP; SATIŞ_ID; PROJE; NOT',
    },
    'payroll': {
        'label': 'Maaş & avans',
        'icon': 'wallet',
        'color': 'violet',
        'permission': 'contact.payroll',
        'fields': PAYROLL_FIELDS,
        'redirect_name': 'accounting_payroll',
        'sample_hint': 'DÖNEM; PERSONEL; TÜR; TUTAR; TARİH; NOT',
    },
    'sales': {
        'label': 'Satış kayıtları',
        'icon': 'badge-dollar-sign',
        'color': 'amber',
        'permission': 'sales.manage',
        'fields': SALES_FIELDS,
        'redirect_name': 'sales_lead_list',
        'sample_hint': 'AD SOYAD; TELEFON; YER; PROJE; TARİH; TOPLAM; PEŞİNAT; NOT',
    },
    'customers': {
        'label': 'Müşteriler (rehber)',
        'icon': 'users',
        'color': 'brand',
        'permission': 'contact.customers',
        'fields': CUSTOMER_FIELDS,
        'redirect_name': 'customers',
        'sample_hint': 'AD SOYAD; TELEFON; YER; ADRES; SÖZLEŞME TARİHİ',
    },
    'firms': {
        'label': 'Firma rehberi',
        'icon': 'building-2',
        'color': 'rose',
        'permission': 'contact.firms',
        'fields': FIRM_FIELDS,
        'redirect_name': 'contact_firmalar',
        'sample_hint': 'Firma Adı; Adres; Telefon; Web Sitesi; Bölge',
    },
}


def import_type_config(slug: str) -> dict | None:
    return IMPORT_TYPES.get(slug)


def list_import_types_for_user(user) -> list[dict]:
    out = []
    for slug, cfg in IMPORT_TYPES.items():
        perm = cfg.get('permission')
        if user.is_superuser or (perm and user.has_perm_codename(perm)):
            out.append({'slug': slug, **{k: v for k, v in cfg.items() if k != 'fields'}})
    return out


def user_can_import_type(user, slug: str) -> bool:
    cfg = import_type_config(slug)
    if not cfg or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perm = cfg.get('permission')
    return bool(perm and user.has_perm_codename(perm))
