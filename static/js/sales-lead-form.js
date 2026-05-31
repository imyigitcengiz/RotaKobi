(function () {
    const cfg = window.SALES_LEAD_FORM || {};
    const products = cfg.products || [];
    const interimContainer = document.getElementById('interimPaymentsContainer');
    const productContainer = document.getElementById('productLinesContainer');
    const addInterimBtn = document.getElementById('addInterimPaymentBtn');
    const addProductBtn = document.getElementById('addProductLineBtn');
    const INPUT = 'w-full p-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-amber-500 outline-none';
    const MONEY = INPUT + ' text-right';

    if (!interimContainer || !productContainer) return;

    function escapeHtml(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function refreshIcons() {
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    }

    function createInterimRow(amount, paymentDate) {
        const row = document.createElement('div');
        row.className = 'flex flex-wrap items-center gap-2 interim-payment-row';
        row.innerHTML = `
            <input type="date" name="interim_payment_date"
                   value="${paymentDate ? escapeHtml(paymentDate) : ''}"
                   class="${INPUT} w-[9.5rem] shrink-0" title="Ödeme tarihi">
            <input type="number" name="interim_payment_amount" step="0.01" min="0"
                   value="${amount != null && amount !== '' ? amount : ''}"
                   placeholder="0,00" class="${MONEY} flex-1 min-w-[7rem]">
            <span class="text-xs text-slate-500 shrink-0">₺</span>
            <button type="button" class="remove-interim p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg" title="Kaldır">
                <i data-lucide="x" class="w-4 h-4"></i>
            </button>
        `;
        row.querySelector('.remove-interim').addEventListener('click', () => row.remove());
        return row;
    }

    function colorOptionsForProduct(productId, selectedId) {
        const product = products.find(p => String(p.id) === String(productId));
        const colors = product ? product.colors : [];
        let html = '<option value="">Renk seçin</option>';
        colors.forEach(c => {
            const sel = String(c.id) === String(selectedId) ? ' selected' : '';
            html += `<option value="${c.id}"${sel}>${escapeHtml(c.name)}</option>`;
        });
        return html;
    }

    function createProductRow(line) {
        const data = line || {};
        const row = document.createElement('div');
        row.className = 'product-line-row p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-3';

        let productOptions = '<option value="">Ürün seçin</option>';
        products.forEach(p => {
            const sel = String(p.id) === String(data.product_id) ? ' selected' : '';
            productOptions += `<option value="${p.id}"${sel}>${escapeHtml(p.name)}</option>`;
        });

        row.innerHTML = `
            <div class="flex items-start justify-between gap-2">
                <span class="text-xs font-bold text-slate-500 uppercase tracking-wide">Ürün satırı</span>
                <button type="button" class="remove-product-line p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg" title="Kaldır">
                    <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div class="md:col-span-2 space-y-1">
                    <label class="text-xs font-semibold text-slate-600">Ürün</label>
                    <select name="product_line_product" class="${INPUT} product-select">${productOptions}</select>
                </div>
                <div class="space-y-1">
                    <label class="text-xs font-semibold text-slate-600">Adet</label>
                    <input type="number" name="product_line_quantity" min="1" step="1"
                           value="${data.quantity || 1}" class="${INPUT}">
                </div>
                <div class="space-y-1">
                    <label class="text-xs font-semibold text-slate-600">Renk</label>
                    <select name="product_line_color" class="${INPUT} color-select"></select>
                </div>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-600">Ürün notu</label>
                <input type="text" name="product_line_note" value="${(data.note || '').replace(/"/g, '&quot;')}"
                       placeholder="Örn. özel ölçü, montaj detayı…" class="${INPUT}">
            </div>
        `;

        const productSelect = row.querySelector('.product-select');
        const colorSelect = row.querySelector('.color-select');

        function syncColors() {
            colorSelect.innerHTML = colorOptionsForProduct(productSelect.value, data.color_id);
            if (data.color_id && productSelect.value === String(data.product_id)) {
                colorSelect.value = String(data.color_id);
            }
        }

        productSelect.addEventListener('change', () => {
            data.color_id = '';
            syncColors();
        });
        syncColors();

        row.querySelector('.remove-product-line').addEventListener('click', () => row.remove());
        return row;
    }

    function initInterimPayments() {
        const items = cfg.interimPayments || [];
        if (items.length) {
            items.forEach(item => interimContainer.appendChild(
                createInterimRow(item.amount, item.payment_date || '')
            ));
        }
    }

    function initProductLines() {
        const items = cfg.productLines || [];
        if (items.length) {
            items.forEach(line => productContainer.appendChild(createProductRow(line)));
        }
    }

    if (addInterimBtn) {
        addInterimBtn.addEventListener('click', () => {
            const saleDateInput = document.querySelector('input[name="sale_date"]');
            const defaultDate = saleDateInput && saleDateInput.value ? saleDateInput.value : '';
            interimContainer.appendChild(createInterimRow('', defaultDate));
            refreshIcons();
        });
    }

    if (addProductBtn) {
        addProductBtn.addEventListener('click', () => {
            productContainer.appendChild(createProductRow({}));
            refreshIcons();
        });
    }

    initInterimPayments();
    initProductLines();
    refreshIcons();
})();
