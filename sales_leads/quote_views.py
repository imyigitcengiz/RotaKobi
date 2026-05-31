"""Teklif CRUD ve satışa dönüştürme."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from core_settings.models import ProductColorOption, ProductOption
from sales_leads.models import SalesLead, SalesQuote, SalesQuoteLine
from users.mixins import PermissionRequiredMixin


def _parse_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _products_catalog():
    return [
        {
            'id': p.id,
            'name': p.name,
            'colors': [{'id': c.id, 'name': c.name} for c in p.colors.all()],
        }
        for p in ProductOption.objects.prefetch_related('colors').order_by('name')
    ]


class SalesQuoteListView(PermissionRequiredMixin, ListView):
    permission_required = 'sales.manage'
    model = SalesQuote
    template_name = 'sales_lead/quotes_list.html'
    context_object_name = 'quotes'

    def get_queryset(self):
        return (
            SalesQuote.objects.select_related('customer', 'converted_lead')
            .prefetch_related('lines__product')
            .order_by('-quote_date', '-created_at')
        )


class SalesQuoteCreateView(PermissionRequiredMixin, View):
    permission_required = 'sales.manage'
    template_name = 'sales_lead/quote_form.html'

    def get(self, request):
        from customers.models import Customer

        customer_id = request.GET.get('customer')
        customer = None
        if customer_id and str(customer_id).isdigit():
            customer = Customer.objects.filter(pk=int(customer_id)).first()
        return render(request, self.template_name, {
            'products': _products_catalog(),
            'customer': customer,
            'customers': Customer.objects.order_by('name')[:500],
            'today': timezone.localdate().isoformat(),
        })

    def post(self, request):
        from customers.models import Customer

        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, pk=customer_id)
        quote = SalesQuote.objects.create(
            customer=customer,
            quote_date=request.POST.get('quote_date') or timezone.localdate(),
            valid_until=request.POST.get('valid_until') or None,
            project=(request.POST.get('project') or '').strip(),
            sale_amount=_parse_decimal(request.POST.get('sale_amount')),
            down_payment=_parse_decimal(request.POST.get('down_payment')),
            status=request.POST.get('status') or SalesQuote.STATUS_DRAFT,
            notes=(request.POST.get('notes') or '').strip() or None,
        )
        product_ids = request.POST.getlist('product_line_product')
        quantities = request.POST.getlist('product_line_quantity')
        color_ids = request.POST.getlist('product_line_color')
        notes = request.POST.getlist('product_line_note')
        for idx, product_id in enumerate(product_ids):
            if not product_id or not str(product_id).isdigit():
                continue
            qty = 1
            if idx < len(quantities):
                try:
                    qty = max(1, int(quantities[idx] or 1))
                except (TypeError, ValueError):
                    qty = 1
            color = None
            if idx < len(color_ids) and color_ids[idx] and str(color_ids[idx]).isdigit():
                color = ProductColorOption.objects.filter(
                    pk=int(color_ids[idx]),
                    product_id=int(product_id),
                ).first()
            SalesQuoteLine.objects.create(
                quote=quote,
                product_id=int(product_id),
                quantity=qty,
                color=color,
                note=(notes[idx] if idx < len(notes) else '').strip() or None,
                sort_order=idx,
            )
        messages.success(request, f'Teklif oluşturuldu: {customer.name}')
        return redirect('sales_quote_list')


class SalesQuoteConvertView(PermissionRequiredMixin, View):
    permission_required = 'sales.manage'

    def post(self, request, pk):
        quote = get_object_or_404(
            SalesQuote.objects.prefetch_related('lines__product', 'lines__color'),
            pk=pk,
        )
        if quote.converted_lead_id:
            messages.warning(request, 'Bu teklif zaten satışa dönüştürülmüş.')
            return redirect('sales_quote_list')

        project = quote.project or quote.products_primary
        lead = SalesLead.objects.create(
            customer=quote.customer,
            project=project[:255],
            sale_date=timezone.localdate(),
            sale_amount=quote.sale_amount,
            down_payment=quote.down_payment,
            status=SalesLead.STATUS_PENDING,
            notes=quote.notes,
        )
        product_ids = []
        for idx, line in enumerate(quote.lines.all()):
            from sales_leads.models import SalesLeadProductLine

            SalesLeadProductLine.objects.create(
                sales_lead=lead,
                product=line.product,
                quantity=line.quantity,
                color=line.color,
                note=line.note,
                sort_order=idx,
            )
            product_ids.append(line.product_id)
        if product_ids:
            lead.products.set(product_ids)

        quote.status = SalesQuote.STATUS_CONVERTED
        quote.converted_lead = lead
        quote.save(update_fields=['status', 'converted_lead', 'updated_at'])
        messages.success(request, 'Teklif satış kaydına dönüştürüldü.')
        return redirect('sales_lead_edit', pk=lead.pk)
