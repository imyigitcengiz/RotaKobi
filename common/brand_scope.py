"""Aktif marka / firma kapsamı — oturum, üyelik ve queryset filtreleri."""

from __future__ import annotations

from django.db.models import Q, QuerySet

SESSION_ACTIVE_BRAND = 'active_brand_id'


def user_brands(user):
    from core_settings.models import BusinessBrand

    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return BusinessBrand.objects.none()
    qs = BusinessBrand.objects.filter(is_active=True)
    if user.is_superuser:
        return qs.order_by('name')
    return qs.filter(memberships__user=user).distinct().order_by('name')


def user_memberships(user):
    from core_settings.models import BrandMembership

    if not user or not user.is_authenticated:
        return BrandMembership.objects.none()
    return (
        BrandMembership.objects.filter(user=user, brand__is_active=True)
        .select_related('brand')
        .order_by('brand__name')
    )


def default_brand_for_user(user):
    from core_settings.models import BrandMembership

    if not user or not user.is_authenticated:
        return None
    mem = (
        BrandMembership.objects.filter(user=user, brand__is_active=True, is_default=True)
        .select_related('brand')
        .first()
    )
    if mem:
        return mem.brand
    mem = (
        BrandMembership.objects.filter(user=user, brand__is_active=True)
        .select_related('brand')
        .order_by('joined_at')
        .first()
    )
    return mem.brand if mem else None


def system_default_brand():
    from core_settings.models import BusinessBrand

    return (
        BusinessBrand.objects.filter(is_default=True, is_active=True).first()
        or BusinessBrand.objects.filter(is_active=True).order_by('pk').first()
    )


def _brand_id_allowed_for_user(user, brand_id: int) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        from core_settings.models import BusinessBrand

        return BusinessBrand.objects.filter(pk=brand_id, is_active=True).exists()
    from core_settings.models import BrandMembership

    return BrandMembership.objects.filter(user=user, brand_id=brand_id, brand__is_active=True).exists()


def get_active_brand_id(request) -> int | None:
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None
    cached = getattr(request, '_active_brand_id', None)
    if cached is not None:
        return cached or None
    raw = request.session.get(SESSION_ACTIVE_BRAND)
    if raw:
        try:
            bid = int(raw)
        except (TypeError, ValueError):
            bid = None
        else:
            if bid and _brand_id_allowed_for_user(request.user, bid):
                request._active_brand_id = bid
                return bid
    if request.user.is_superuser:
        request._active_brand_id = None
        return None
    default = default_brand_for_user(request.user) or system_default_brand()
    bid = default.pk if default else None
    request._active_brand_id = bid
    return bid


def get_active_brand(request):
    from core_settings.models import BusinessBrand

    bid = get_active_brand_id(request)
    if not bid:
        return None
    cached = getattr(request, '_active_brand_obj', None)
    if cached is not None and cached.pk == bid:
        return cached
    brand = BusinessBrand.objects.filter(pk=bid, is_active=True).first()
    request._active_brand_obj = brand
    return brand


def set_active_brand(request, brand_id: int) -> bool:
    if not _brand_id_allowed_for_user(request.user, brand_id):
        return False
    request.session[SESSION_ACTIVE_BRAND] = brand_id
    request._active_brand_id = brand_id
    request._active_brand_obj = None
    return True


def ensure_session_brand(request) -> None:
    """Middleware: oturumda geçerli aktif marka yoksa varsayılanı yaz."""
    if not request.user.is_authenticated:
        return
    if request.user.is_superuser and not request.session.get(SESSION_ACTIVE_BRAND):
        return
    bid = get_active_brand_id(request)
    if bid:
        request.session[SESSION_ACTIVE_BRAND] = bid


def filter_by_brand(qs: QuerySet, request, *, field: str = 'brand') -> QuerySet:
    if not hasattr(qs.model, field):
        return qs
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and user.is_superuser:
        session_brand = None
        if hasattr(request, 'session'):
            raw = request.session.get(SESSION_ACTIVE_BRAND)
            if raw:
                try:
                    session_brand = int(raw)
                except (TypeError, ValueError):
                    session_brand = None
        if not session_brand:
            return qs
        return qs.filter(**{f'{field}_id': session_brand})
    bid = get_active_brand_id(request)
    if bid:
        return qs.filter(**{f'{field}_id': bid})
    if user and user.is_authenticated:
        return qs.none()
    return qs.none()


def filter_customers(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_customer_for_request(request, pk):
    """Aktif marka kapsamında müşteri; cross-tenant erişimde 404."""
    from django.shortcuts import get_object_or_404
    from customers.models import Customer

    return get_object_or_404(filter_customers(Customer.objects.all(), request), pk=pk)


def filter_services(qs: QuerySet, request) -> QuerySet:
    bid = get_active_brand_id(request)
    if not bid:
        return qs
    return qs.filter(Q(brand_id=bid) | Q(customer__brand_id=bid)).distinct()


def get_service_for_request(request, pk, *, queryset=None):
    """Aktif marka kapsamında servis kaydı; cross-tenant erişimde 404."""
    from django.shortcuts import get_object_or_404
    from services.models import ServiceRecord

    base = queryset if queryset is not None else ServiceRecord.objects.all()
    return get_object_or_404(filter_services(base, request), pk=pk)


def filter_sales_leads(qs: QuerySet, request) -> QuerySet:
    """Satış / teklif kayıtları — müşteri markası üzerinden filtre."""
    bid = get_active_brand_id(request)
    if not bid:
        return qs
    return qs.filter(customer__brand_id=bid)


def get_sales_lead_for_request(request, pk, *, queryset=None):
    from django.shortcuts import get_object_or_404
    from sales_leads.models import SalesLead

    base = queryset if queryset is not None else SalesLead.objects.all()
    return get_object_or_404(filter_sales_leads(base, request), pk=pk)


def get_sales_quote_for_request(request, pk, *, queryset=None):
    from django.shortcuts import get_object_or_404
    from sales_leads.models import SalesQuote

    base = queryset if queryset is not None else SalesQuote.objects.all()
    return get_object_or_404(filter_sales_leads(base, request), pk=pk)


def filter_finance(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def filter_firms(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_firm_for_request(request, pk):
    from django.shortcuts import get_object_or_404
    from tools.models import MapsScrapedFirm

    return get_object_or_404(filter_firms(MapsScrapedFirm.objects.all(), request), pk=pk)


def filter_outreach_collections(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_outreach_collection_for_request(request, pk):
    from django.shortcuts import get_object_or_404
    from tools.models import OutreachCollection

    return get_object_or_404(
        filter_outreach_collections(OutreachCollection.objects.all(), request),
        pk=pk,
    )


def filter_whatsapp_connections(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_whatsapp_connection_for_request(request, pk):
    from django.shortcuts import get_object_or_404
    from tools.models import WhatsappConnection

    return get_object_or_404(
        filter_whatsapp_connections(WhatsappConnection.objects.all(), request),
        pk=pk,
    )


def filter_personnel(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_personnel_for_request(request, pk):
    from django.shortcuts import get_object_or_404
    from core_settings.models import ServicePersonnel

    return get_object_or_404(
        filter_personnel(ServicePersonnel.objects.all(), request),
        pk=pk,
    )


def filter_solution_partners(qs: QuerySet, request) -> QuerySet:
    return filter_by_brand(qs, request, field='brand')


def get_solution_partner_for_request(request, pk):
    from django.shortcuts import get_object_or_404
    from core_settings.models import SolutionPartner

    return get_object_or_404(
        filter_solution_partners(SolutionPartner.objects.all(), request),
        pk=pk,
    )


def filter_outreach_messages(qs: QuerySet, request) -> QuerySet:
    bid = get_active_brand_id(request)
    if not bid:
        return qs.none()
    return qs.filter(
        Q(collection__brand_id=bid)
        | Q(customer__brand_id=bid)
        | Q(firm__brand_id=bid)
    ).distinct()


def users_share_brand(user_a, user_b, *, brand_id: int | None = None) -> bool:
    """İki kullanıcı aynı aktif markada üye mi?"""
    from core_settings.models import BrandMembership

    if not user_a or not user_b or not user_a.is_authenticated or not user_b.is_authenticated:
        return False
    if user_a.pk == user_b.pk:
        return True
    qs = BrandMembership.objects.filter(brand__is_active=True)
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    a_brands = set(qs.filter(user=user_a).values_list('brand_id', flat=True))
    if not a_brands:
        return False
    return qs.filter(user=user_b, brand_id__in=a_brands).exists()


def authorized_whatsapp_batch_qs(request, batch_id: str):
    """Kampanya batch'i — başka markanın müşteri mesajı içeriyorsa boş döner."""
    from tools.models import WhatsappOutboundMessage

    batch_id = (batch_id or '').strip()
    if not batch_id:
        return WhatsappOutboundMessage.objects.none()
    base = WhatsappOutboundMessage.objects.filter(batch_id=batch_id)
    bid = get_active_brand_id(request)
    if not bid:
        return WhatsappOutboundMessage.objects.none()
    if base.filter(customer__isnull=False).exclude(customer__brand_id=bid).exists():
        return WhatsappOutboundMessage.objects.none()
    return base


def assign_brand(instance, request, *, field: str = 'brand') -> None:
    if getattr(instance, f'{field}_id', None):
        return
    bid = get_active_brand_id(request)
    if bid:
        setattr(instance, f'{field}_id', bid)


def create_brand_for_user(
    user,
    name: str,
    *,
    panel_kind=None,
    parent_brand=None,
    tenant_routing=None,
    host_slug='',
    bypass_plan_limit=False,
    **extra,
):
    """Yeni marka oluşturur; kullanıcıyı sahip yapar."""
    from core_settings.models import BrandMembership, BusinessBrand

    name = (name or '').strip()
    if not name:
        raise ValueError('Marka adı gerekli.')

    panel_kind = panel_kind or BusinessBrand.PANEL_HQ
    if user.is_superuser:
        raise ValueError('Süper admin marka sahibi olamaz. Abonelik sahibi seçin.')

    if panel_kind == BusinessBrand.PANEL_DEALER:
        if not parent_brand:
            raise ValueError('Bayi paneli için merkez marka gerekli.')
        if not user.is_superuser and not BrandMembership.objects.filter(
            user=user,
            brand=parent_brand,
            role=BrandMembership.ROLE_OWNER,
        ).exists():
            raise ValueError('Bayi paneli yalnızca merkez marka sahibi tarafından oluşturulabilir.')

    plan = user.active_plan
    if panel_kind == BusinessBrand.PANEL_HQ:
        hq_count = BrandMembership.objects.filter(
            user=user,
            role=BrandMembership.ROLE_OWNER,
            brand__panel_kind=BusinessBrand.PANEL_HQ,
            brand__is_active=True,
        ).count()
        limit = getattr(plan, 'max_hq_brands', None) or plan.max_brands
        if not bypass_plan_limit and hq_count >= limit:
            raise ValueError(
                f"Mevcut planınız ({plan.name}) en fazla {limit} merkez panel oluşturmanıza izin veriyor."
            )
    else:
        hq_ids = BrandMembership.objects.filter(
            user=user,
            role=BrandMembership.ROLE_OWNER,
            brand__panel_kind=BusinessBrand.PANEL_HQ,
        ).values_list('brand_id', flat=True)
        dealer_count = BusinessBrand.objects.filter(
            panel_kind=BusinessBrand.PANEL_DEALER,
            parent_brand_id__in=hq_ids,
            is_active=True,
        ).count()
        limit = getattr(plan, 'max_dealer_panels', 0)
        if not bypass_plan_limit and dealer_count >= limit:
            raise ValueError(
                f"Mevcut planınız ({plan.name}) en fazla {limit} bayi alt panel oluşturmanıza izin veriyor."
            )

    has_any = BrandMembership.objects.filter(user=user).exists()
    allowed_fields = {'legal_name', 'phone', 'address', 'currency_code'}
    brand = BusinessBrand(
        name=name,
        created_by=user,
        panel_kind=panel_kind,
        parent_brand=parent_brand if panel_kind == BusinessBrand.PANEL_DEALER else None,
        tenant_routing=tenant_routing or BusinessBrand.TENANT_SUBDOMAIN,
        host_slug=(host_slug or '').strip(),
        is_default=not BusinessBrand.objects.exists() and panel_kind == BusinessBrand.PANEL_HQ,
        **{k: v for k, v in extra.items() if k in allowed_fields},
    )
    brand.save()
    BrandMembership.objects.create(
        user=user,
        brand=brand,
        role=BrandMembership.ROLE_OWNER,
        is_default=not has_any,
    )
    return brand
