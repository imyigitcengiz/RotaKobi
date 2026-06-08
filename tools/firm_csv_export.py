"""Firma rehberi CSV dışa aktarma."""

from __future__ import annotations

from django.db.models import Q

from tools.models import MapsScrapedFirm
from tools.outreach_memory import CUSTOMER_SHADOW_NOTE

FIRM_CSV_HEADER = [
    'Firma adı',
    'Adres',
    'Telefon',
    'Web sitesi',
    'Bölge',
    'Not',
    'Tür',
    'Etiketler',
    'Puan',
    'Yorum',
    'Maps URL',
]


def firms_directory_queryset(
    *,
    request=None,
    q: str = '',
    kind: str = '',
    region: str = '',
    tag_id=None,
):
    qs = (
        MapsScrapedFirm.objects.prefetch_related('tags', 'solution_partner__partner_type')
        .exclude(notes=CUSTOMER_SHADOW_NOTE)
        .order_by('-last_scraped_at')
    )
    if request is not None:
        from common.brand_scope import filter_firms
        qs = filter_firms(qs, request)
    kind = (kind or '').strip()
    if kind and kind != 'all':
        qs = qs.filter(firm_kind=kind)
    q = (q or '').strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(address__icontains=q)
            | Q(notes__icontains=q)
            | Q(region__icontains=q)
        )
    region = (region or '').strip()
    if region:
        qs = qs.filter(region__iexact=region)
    if tag_id:
        try:
            qs = qs.filter(tags__id=int(tag_id))
        except (TypeError, ValueError):
            pass
    return qs.distinct()


def firm_csv_row(firm: MapsScrapedFirm) -> list[str]:
    tags = ' | '.join(t.name for t in firm.tags.all())
    return [
        firm.name,
        firm.address or '',
        firm.phone or '',
        firm.website or '',
        firm.region or '',
        firm.notes or '',
        firm.get_firm_kind_display(),
        tags,
        firm.rating or '',
        firm.reviews or '',
        firm.maps_url or '',
    ]


def export_firms_csv_response(request):
    from common.csv_io import csv_response

    kind = (request.GET.get('kind') or '').strip()
    qs = firms_directory_queryset(
        request=request,
        q=request.GET.get('q'),
        kind=kind,
        region=request.GET.get('region'),
        tag_id=request.GET.get('tag_id'),
    )
    rows = [firm_csv_row(firm) for firm in qs.iterator(chunk_size=200)]
    filename = 'firma-rehberi.csv' if kind in ('', 'all') else f'firma-rehberi-{kind}.csv'
    return csv_response(filename, rows, header=FIRM_CSV_HEADER)
