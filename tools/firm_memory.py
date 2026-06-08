from django.db import IntegrityError, transaction

from django.utils import timezone



from tools.models import FirmTag, MapsScrapedFirm

from tools.outreach_memory import get_last_message_at, get_sent_count, has_been_messaged_globally, merge_firm_records

from tools.phone_utils import is_turkish_landline, is_whatsapp_eligible, normalize_phone, whatsapp_url
from tools.firm_delete_guard import PARTNER_DELETE_MESSAGE, is_partner_protected





def _field(data, key, default=''):

    val = data.get(key)

    if val is None or val == '-':

        return default

    return str(val).strip() or default





def _build_payload(data: dict) -> dict:

    place_id = _field(data, 'place_id')

    phone_raw = _field(data, 'phone')

    phone_norm = normalize_phone(phone_raw)

    payload = {

        'name': _field(data, 'name', 'İsimsiz'),

        'address': _field(data, 'address'),

        'phone': phone_raw,

        'phone_normalized': phone_norm,

        'website': _field(data, 'website'),

        'rating': _field(data, 'rating'),

        'reviews': _field(data, 'reviews'),

        'maps_url': _field(data, 'maps_url'),

        'lat': _field(data, 'lat'),

        'lng': _field(data, 'lng'),
        'last_scraped_at': timezone.now(),
    }
    region = _field(data, 'region')
    if region:
        payload['region'] = region[:80]
    if place_id:
        payload['place_id'] = place_id

    return payload





def _apply_payload(firm: MapsScrapedFirm, payload: dict) -> None:

    for key, val in payload.items():

        if key == 'firm_kind' and firm.solution_partner_id:

            continue

        if key == 'last_scraped_at' or val:

            setattr(firm, key, val)





def _matches_phone_filter(phone_raw: str, phone_norm: str, phone_filter: str) -> bool:

    if phone_filter == 'all':

        return bool(phone_norm) or bool(phone_raw)

    is_ll = is_turkish_landline(phone_raw, phone_norm)

    is_mob = bool(phone_norm) and not is_ll

    if phone_filter == 'mobile':

        return is_mob

    if phone_filter == 'landline':

        return is_ll

    return True





def _serialize_raw_row(data: dict) -> dict:

    phone_raw = _field(data, 'phone')

    phone_norm = normalize_phone(phone_raw)

    is_ll = is_turkish_landline(phone_raw, phone_norm)

    return {

        'firm_id': None,

        'place_id': _field(data, 'place_id'),

        'name': _field(data, 'name', 'İsimsiz'),

        'address': _field(data, 'address'),

        'phone': phone_raw or '-',

        'phone_normalized': phone_norm,

        'whatsapp_url': whatsapp_url(phone_raw),

        'website': _field(data, 'website') or '-',

        'rating': _field(data, 'rating') or '-',

        'reviews': _field(data, 'reviews') or '-',

        'maps_url': _field(data, 'maps_url') or '-',

        'lat': _field(data, 'lat'),

        'lng': _field(data, 'lng'),
        'region': _field(data, 'region'),
        'tags': [],
        'already_in_memory': False,

        'saved_to_memory': False,

        'messages_sent': 0,

        'last_message_at': None,

        'first_scraped_at': None,

        'last_scraped_at': None,

        'is_landline': is_ll,

        'whatsapp_eligible': is_whatsapp_eligible(phone_raw, phone_norm),

        'can_message': False,

        'globally_messaged': False,

    }





def _firm_scope(*, brand_id: int | None = None):
    qs = MapsScrapedFirm.objects.all()
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    return qs


@transaction.atomic

def register_scrape(data: dict, *, brand_id: int | None = None) -> tuple[MapsScrapedFirm, bool]:

    payload = _build_payload(data)

    place_id = payload.get('place_id', '')

    phone_norm = payload.get('phone_normalized', '')

    scope = _firm_scope(brand_id=brand_id)

    firm_by_place = scope.filter(place_id=place_id).first() if place_id else None

    firm_by_phone = scope.filter(phone_normalized=phone_norm).first() if phone_norm else None



    if firm_by_place and firm_by_phone and firm_by_place.pk != firm_by_phone.pk:

        primary = firm_by_place

        if (firm_by_phone.messages_sent_count or 0) > (firm_by_place.messages_sent_count or 0):

            primary = firm_by_phone

            secondary = firm_by_place

        else:

            secondary = firm_by_phone

        firm = merge_firm_records(primary, secondary)

        _apply_payload(firm, payload)

        firm.save()

        return firm, False



    firm = firm_by_place or firm_by_phone

    if firm:

        _apply_payload(firm, payload)

        firm.save()

        return firm, False



    payload.setdefault('firm_kind', MapsScrapedFirm.KIND_SCRAPED)
    if brand_id:
        payload['brand_id'] = brand_id

    try:

        firm = MapsScrapedFirm.objects.create(**payload)

        return firm, True

    except IntegrityError:

        firm = None

        if place_id:

            firm = scope.filter(place_id=place_id).first()

        if not firm and phone_norm:

            firm = scope.filter(phone_normalized=phone_norm).first()

        if not firm:

            raise

        _apply_payload(firm, payload)

        firm.save()

        return firm, False





def serialize_firm(firm: MapsScrapedFirm, *, already_in_memory: bool | None = None) -> dict:

    phone_norm = firm.phone_normalized

    messages_sent = get_sent_count(phone_norm) if phone_norm else firm.messages_sent_count

    last_msg = get_last_message_at(phone_norm) if phone_norm else firm.last_message_at

    wa_eligible = is_whatsapp_eligible(firm.phone, phone_norm)

    tags = [{'id': t.id, 'name': t.name, 'color': t.color} for t in firm.tags.all()]



    partner_type = ''
    sp = getattr(firm, 'solution_partner', None)
    if sp and getattr(sp, 'partner_type_id', None):
        partner_type = sp.partner_type.name

    return {

        'firm_id': firm.id,

        'firm_kind': firm.firm_kind,

        'firm_kind_label': firm.get_firm_kind_display(),

        'partner_type': partner_type,

        'is_active': firm.is_active,

        'solution_partner_id': firm.solution_partner_id,

        'place_id': firm.place_id,

        'name': firm.name,

        'address': firm.address,

        'phone': firm.phone or '-',

        'phone_normalized': phone_norm,

        'whatsapp_url': whatsapp_url(firm.phone),

        'website': firm.website or '-',

        'rating': firm.rating or '-',

        'reviews': firm.reviews or '-',

        'maps_url': firm.maps_url or '-',

        'lat': firm.lat,

        'lng': firm.lng,
        'region': firm.region or '',
        'tags': tags,
        'already_in_memory': already_in_memory if already_in_memory is not None else True,

        'saved_to_memory': True,

        'messages_sent': messages_sent,

        'last_message_at': last_msg.isoformat() if last_msg else None,

        'first_scraped_at': firm.first_scraped_at.isoformat(),

        'last_scraped_at': firm.last_scraped_at.isoformat(),

        'is_landline': is_turkish_landline(firm.phone, phone_norm),

        'whatsapp_eligible': wa_eligible,

        'can_message': wa_eligible and not has_been_messaged_globally(phone_norm),

        'globally_messaged': has_been_messaged_globally(phone_norm) if phone_norm else False,

        'delete_protected': is_partner_protected(firm),

        'delete_block_reason': PARTNER_DELETE_MESSAGE if is_partner_protected(firm) else '',

    }





def enrich_search_results(

    results: list[dict],

    *,

    phone_filter: str = 'all',

    tag_ids: list | None = None,
    scrape_region: str = '',
    brand_id: int | None = None,
) -> list[dict]:
    tag_ids = tag_ids or []
    scrape_region = (scrape_region or '').strip()[:80]
    tag_qs = FirmTag.objects.filter(pk__in=tag_ids) if tag_ids else FirmTag.objects.none()
    if brand_id:
        tag_qs = tag_qs.filter(brand_id=brand_id)
    tags = list(tag_qs)
    enriched = []

    for row in results:
        if scrape_region:
            row = {**row, 'region': scrape_region}
        phone_raw = _field(row, 'phone')
        phone_norm = normalize_phone(phone_raw)



        if not _matches_phone_filter(phone_raw, phone_norm, phone_filter):

            firm = None

            scope = _firm_scope(brand_id=brand_id)
            if phone_norm:

                firm = scope.filter(phone_normalized=phone_norm).prefetch_related('tags').first()

            if not firm:

                place_id = _field(row, 'place_id')

                if place_id:

                    firm = scope.filter(place_id=place_id).prefetch_related('tags').first()

            item = serialize_firm(firm, already_in_memory=True) if firm else _serialize_raw_row(row)

            item['saved_to_memory'] = False

            enriched.append(item)

            continue



        firm, created = register_scrape(row, brand_id=brand_id)

        if tags:

            firm.tags.add(*tags)

        firm = MapsScrapedFirm.objects.prefetch_related('tags').get(pk=firm.pk)

        item = serialize_firm(firm, already_in_memory=not created)

        item['saved_to_memory'] = True

        enriched.append(item)



    return enriched


