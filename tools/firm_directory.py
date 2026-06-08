"""Firma rehberi — kazınan, çözüm ortağı ve manuel kayıtlar."""

from __future__ import annotations

from django.db import transaction

from tools.models import MapsScrapedFirm
from tools.phone_utils import normalize_phone

KIND_SCRAPED = MapsScrapedFirm.KIND_SCRAPED
KIND_PARTNER = MapsScrapedFirm.KIND_PARTNER
KIND_DEALER = MapsScrapedFirm.KIND_DEALER
KIND_BUSINESS = MapsScrapedFirm.KIND_BUSINESS

KIND_LABELS = dict(MapsScrapedFirm.KIND_CHOICES)


def sync_partner_to_directory(partner) -> MapsScrapedFirm | None:
    """Çözüm ağı kaydını firmalar rehberine yansıt."""
    from core_settings.models import SolutionPartner

    if not isinstance(partner, SolutionPartner):
        return None

    phone_norm = normalize_phone(partner.phone or '')
    brand_id = partner.brand_id
    scope = MapsScrapedFirm.objects.filter(brand_id=brand_id) if brand_id else MapsScrapedFirm.objects.none()
    firm = scope.filter(solution_partner_id=partner.pk).first()
    if not firm and phone_norm:
        firm = scope.filter(
            phone_normalized=phone_norm,
            firm_kind=KIND_PARTNER,
        ).first()

    partner_type_name = ''
    if partner.partner_type_id:
        partner_type_name = partner.partner_type.name

    notes = (partner.notes or '').strip()
    if partner_type_name:
        prefix = f'Tür: {partner_type_name}'
        notes = f'{prefix}. {notes}'.strip() if notes else prefix

    payload = {
        'name': partner.name or 'İsimsiz ortak',
        'phone': partner.phone or '',
        'phone_normalized': phone_norm,
        'firm_kind': KIND_PARTNER,
        'solution_partner': partner,
        'is_active': partner.is_active,
        'notes': notes[:255],
    }

    if firm:
        for key, val in payload.items():
            if key != 'solution_partner':
                setattr(firm, key, val)
        firm.solution_partner = partner
        firm.save()
        return firm

    if phone_norm:
        clash = scope.filter(phone_normalized=phone_norm).exclude(
            firm_kind=KIND_PARTNER
        ).first()
        if clash and clash.firm_kind == KIND_SCRAPED:
            clash.firm_kind = KIND_PARTNER
            clash.solution_partner = partner
            clash.is_active = partner.is_active
            clash.name = payload['name']
            clash.phone = payload['phone']
            clash.notes = payload['notes']
            clash.save()
            return clash

    if brand_id:
        payload['brand_id'] = brand_id
    return MapsScrapedFirm.objects.create(**payload)


def remove_partner_from_directory(partner_id: int) -> None:
    MapsScrapedFirm.objects.filter(solution_partner_id=partner_id).delete()


@transaction.atomic
def sync_all_partners_to_directory() -> int:
    from core_settings.models import SolutionPartner

    count = 0
    for partner in SolutionPartner.objects.select_related('partner_type').iterator():
        sync_partner_to_directory(partner)
        count += 1
    return count


def create_manual_firm(
    *,
    name: str,
    phone: str = '',
    firm_kind: str = KIND_BUSINESS,
    region: str = '',
    notes: str = '',
) -> MapsScrapedFirm:
    phone_norm = normalize_phone(phone)
    if firm_kind not in dict(MapsScrapedFirm.KIND_CHOICES):
        firm_kind = KIND_BUSINESS
    if phone_norm:
        existing = MapsScrapedFirm.objects.filter(phone_normalized=phone_norm).first()
        if existing:
            existing.name = name[:255]
            existing.firm_kind = firm_kind
            existing.region = (region or '')[:80]
            existing.notes = (notes or '')[:255]
            existing.is_active = True
            existing.save()
            return existing
    return MapsScrapedFirm.objects.create(
        name=name[:255] or 'İsimsiz',
        phone=phone[:40],
        phone_normalized=phone_norm,
        firm_kind=firm_kind,
        region=(region or '')[:80],
        notes=(notes or '')[:255],
        is_active=True,
    )
