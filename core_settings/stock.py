"""Malzeme stoku ve ürün reçetesi (BOM) — satış/serviste malzeme düşümü."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from core_settings.models import Material, ProductOption, ProductRecipeLine, StockMovement, StockSettings


class InsufficientStockError(Exception):
    def __init__(self, material: Material, requested: Decimal, available: Decimal):
        self.material = material
        self.requested = requested
        self.available = available
        super().__init__(
            f'{material.name}: {requested} {material.get_unit_display()} gerekli, '
            f'stokta {available} {material.get_unit_display()} var.'
        )


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def get_stock_settings() -> StockSettings:
    obj, _ = StockSettings.objects.get_or_create(pk=1)
    return obj


def save_stock_settings(**kwargs) -> StockSettings:
    settings = get_stock_settings()
    for key, value in kwargs.items():
        setattr(settings, key, value)
    settings.save()
    return settings


def is_low_stock(material: Material) -> bool:
    if material.min_stock_level <= 0:
        return False
    return material.stock_quantity <= material.min_stock_level


def recipe_requirements(product: ProductOption, units: Decimal) -> list[tuple[Material, Decimal]]:
    """1 satış ürünü × units → malzeme ihtiyacı listesi."""
    lines = product.recipe_lines.select_related('material').filter(material__is_active=True)
    return [(line.material, _to_decimal(line.quantity) * units) for line in lines]


def aggregate_requirements(items: list[tuple[ProductOption, Decimal]]) -> dict[int, Decimal]:
    """[(product, qty), …] → {material_id: total_qty}."""
    totals: dict[int, Decimal] = {}
    for product, units in items:
        for material, need in recipe_requirements(product, units):
            totals[material.id] = totals.get(material.id, Decimal('0')) + need
    return totals


@transaction.atomic
def apply_movement(
    material: Material,
    delta: Decimal,
    *,
    reason: str,
    note: str = '',
    sales_lead=None,
    service_record=None,
    recorded_by=None,
    force: bool = False,
) -> StockMovement | None:
    delta = _to_decimal(delta)
    if delta == 0:
        return None

    material = Material.objects.select_for_update().get(pk=material.pk)
    if not material.is_active and not force:
        return None

    settings = get_stock_settings()
    new_qty = material.stock_quantity + delta
    if new_qty < 0 and settings.block_negative_stock:
        raise InsufficientStockError(material, abs(delta), material.stock_quantity)

    Material.objects.filter(pk=material.pk).update(
        stock_quantity=F('stock_quantity') + delta,
    )
    material.refresh_from_db(fields=['stock_quantity'])

    return StockMovement.objects.create(
        material=material,
        delta=delta,
        quantity_after=material.stock_quantity,
        reason=reason,
        note=note,
        sales_lead=sales_lead,
        service_record=service_record,
        recorded_by=recorded_by,
    )


def build_stock_context(*, low_only: bool = False, recipe_product_id: int | None = None) -> dict:
    materials = list(Material.objects.filter(is_active=True).order_by('name'))
    if low_only:
        materials = [m for m in materials if is_low_stock(m)]

    low_count = Material.objects.filter(is_active=True).filter(
        min_stock_level__gt=0,
        stock_quantity__lte=F('min_stock_level'),
    ).count()

    recent = (
        StockMovement.objects.select_related('material', 'recorded_by', 'sales_lead')
        .order_by('-created_at')[:30]
    )

    products = list(ProductOption.objects.order_by('name'))
    recipe_product = None
    recipe_lines = []
    if recipe_product_id:
        recipe_product = ProductOption.objects.filter(pk=recipe_product_id).first()
        if recipe_product:
            recipe_lines = list(
                recipe_product.recipe_lines.select_related('material').order_by('material__name')
            )

    products_without_recipe = [
        p for p in products
        if not p.recipe_lines.exists()
    ]

    return {
        'stock_materials': materials,
        'stock_show_all': not low_only,
        'stock_low_count': low_count,
        'stock_tracked_count': Material.objects.filter(is_active=True).count(),
        'stock_total_units': sum(m.stock_quantity for m in materials),
        'stock_recent_movements': recent,
        'stock_settings': get_stock_settings(),
        'recipe_products': products,
        'recipe_product': recipe_product,
        'recipe_lines': recipe_lines,
        'products_without_recipe_count': len(products_without_recipe),
    }


def _sale_already_deducted(lead_id: int) -> bool:
    return StockMovement.objects.filter(
        sales_lead_id=lead_id,
        reason=StockMovement.REASON_SALE,
    ).exists()


def _restore_sale_stock(lead, *, recorded_by=None):
    movements = StockMovement.objects.filter(
        sales_lead=lead,
        reason=StockMovement.REASON_SALE,
    ).select_related('material')
    for mov in movements:
        apply_movement(
            mov.material,
            mov.delta * Decimal('-1'),
            reason=StockMovement.REASON_SALE_CANCEL,
            note=f'Satış #{lead.pk} iptal',
            sales_lead=lead,
            recorded_by=recorded_by,
            force=True,
        )
    movements.delete()


def _deduct_requirements(
    requirements: dict[int, Decimal],
    *,
    reason: str,
    note: str,
    sales_lead=None,
    service_record=None,
    recorded_by=None,
) -> list[str]:
    warnings: list[str] = []
    materials = {
        m.id: m
        for m in Material.objects.filter(pk__in=requirements.keys(), is_active=True)
    }
    for material_id, need in requirements.items():
        material = materials.get(material_id)
        if not material or need <= 0:
            continue
        try:
            apply_movement(
                material,
                -need,
                reason=reason,
                note=note,
                sales_lead=sales_lead,
                service_record=service_record,
                recorded_by=recorded_by,
            )
        except InsufficientStockError as exc:
            warnings.append(str(exc))
    return warnings


def sync_sale_stock(lead, *, recorded_by=None) -> list[str]:
    """Tamamlanan satışta reçeteye göre malzeme düş; iptalde geri al."""
    from sales_leads.models import SalesLead

    settings = get_stock_settings()
    warnings: list[str] = []

    if lead.status == SalesLead.STATUS_CANCELLED:
        if _sale_already_deducted(lead.pk):
            _restore_sale_stock(lead, recorded_by=recorded_by)
        return warnings

    if not settings.auto_deduct_on_sale or lead.status != SalesLead.STATUS_COMPLETED:
        return warnings

    if _sale_already_deducted(lead.pk):
        return warnings

    items = []
    for line in lead.product_lines.select_related('product'):
        items.append((line.product, _to_decimal(line.quantity)))

    if not items:
        for product in lead.products.all():
            items.append((product, Decimal('1')))

    requirements = aggregate_requirements(items)
    if not requirements:
        return warnings

    warnings.extend(_deduct_requirements(
        requirements,
        reason=StockMovement.REASON_SALE,
        note=f'Satış #{lead.pk} reçete',
        sales_lead=lead,
        recorded_by=recorded_by,
    ))
    return warnings


def _service_already_deducted(service_id: int) -> bool:
    return StockMovement.objects.filter(
        service_record_id=service_id,
        reason=StockMovement.REASON_SERVICE,
    ).exists()


def sync_service_stock(service, *, recorded_by=None) -> list[str]:
    settings = get_stock_settings()
    if not settings.auto_deduct_on_service:
        return []
    if _service_already_deducted(service.pk):
        return []

    items = [(product, Decimal('1')) for product in service.products.all()]
    requirements = aggregate_requirements(items)
    if not requirements:
        return []

    return _deduct_requirements(
        requirements,
        reason=StockMovement.REASON_SERVICE,
        note=f'Servis #{service.pk} reçete',
        service_record=service,
        recorded_by=recorded_by,
    )
