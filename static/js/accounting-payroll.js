(function () {
  'use strict';

  function parseMoney(value) {
    const n = parseFloat(String(value || '').replace(',', '.'));
    return Number.isFinite(n) ? n : 0;
  }

  function currencySym() {
    return (window.COOLOPS_CURRENCY && window.COOLOPS_CURRENCY.symbol) || '₺';
  }

  function formatMoney(value) {
    return parseMoney(value).toLocaleString('tr-TR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function moneyWithSym(value) {
    const sym = currencySym();
    const num = formatMoney(value);
    const pos = (window.COOLOPS_CURRENCY && window.COOLOPS_CURRENCY.position) || 'after';
    return pos === 'before' ? sym + num : num + ' ' + sym;
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function readMeta() {
    const el = document.getElementById('personnelPayMeta');
    if (!el) return {};
    try {
      return JSON.parse(el.textContent || '{}');
    } catch (_e) {
      return {};
    }
  }

  function netPreviewText(meta, personnelId, extraAdvance) {
    const row = meta[String(personnelId)];
    if (!row || !row.gross) return '';
    const gross = parseMoney(row.gross);
    const currentAdv = parseMoney(row.advances);
    const addAdv = parseMoney(extraAdvance);
    const totalAdv = currentAdv + addAdv;
    const net = gross - totalAdv;
    let text = moneyWithSym(gross) + ' brüt maaş';
    if (totalAdv > 0) {
      text += ' − ' + moneyWithSym(totalAdv) + ' avans';
    }
    text += ' = ';
    if (net >= 0) {
      text += moneyWithSym(net) + ' net ödeme';
    } else {
      text += 'avans fazla (' + moneyWithSym(net) + ')';
    }
    return text;
  }

  function bindSheet() {
    const backdrop = document.getElementById('acctSheetBackdrop');
    const panel = document.getElementById('acctSheetPanel');
    if (!backdrop || !panel) return null;

    const meta = readMeta();
    const titleEl = document.getElementById('acctSheetTitle');
    const subtitleEl = document.getElementById('acctSheetSubtitle');
    const previewEl = document.getElementById('acctSheetPreview');
    const forms = {
      advance: document.getElementById('acctFormAdvance'),
      salary: document.getElementById('acctFormSalary'),
      settings: document.getElementById('acctFormSettings'),
      cycle: document.getElementById('acctFormCycle'),
    };

    function hideAllForms() {
      Object.values(forms).forEach(function (f) {
        if (f) f.classList.add('hidden');
      });
    }

    function refreshPreview(personnelId, extraAdvance) {
      if (!previewEl) return;
      const text = netPreviewText(meta, personnelId, extraAdvance);
      if (text) {
        previewEl.textContent = text;
        previewEl.classList.remove('hidden');
      } else {
        previewEl.classList.add('hidden');
      }
    }

    function setField(form, name, value) {
      const input = form && form.querySelector('[name="' + name + '"]');
      if (input && value !== undefined && value !== null) {
        input.value = value;
      }
    }

    function open(mode, data) {
      hideAllForms();
      const form = forms[mode];
      if (!form) return;

      form.classList.remove('hidden');
      const pid = data.personnelId || '';
      const pname = data.personnelName || '';
      const row = meta[String(pid)] || {};

      if (titleEl) {
        const titles = {
          advance: 'Avans kaydı',
          salary: 'Maaş ödemesi',
          settings: 'Maaş tanımı',
          cycle: 'Döngüsel maaş ödemesi',
        };
        titleEl.textContent = titles[mode] || 'İşlem';
      }
      if (subtitleEl) {
        subtitleEl.textContent = pname ? pname + ' · ' + (data.periodLabel || '') : (data.periodLabel || '');
      }

      if (mode === 'advance') {
        const personnelSelect = form.querySelector('select[name="personnel"]');
        if (personnelSelect && pid) personnelSelect.value = String(pid);
        setField(form, 'period', data.period || '');
        setField(form, 'payment_date', todayIso());
        setField(form, 'amount', data.amount || '');
        setField(form, 'notes', '');
        refreshPreview(personnelSelect && personnelSelect.value, data.amount || 0);
      } else if (mode === 'salary') {
        const sel = form.querySelector('select[name="personnel"]');
        if (sel && pid) sel.value = String(pid);
        setField(form, 'period', data.period || '');
        setField(form, 'payment_date', row.due_date || todayIso());
        const grossInput = form.querySelector('input[name="gross_amount"]');
        if (grossInput) {
          grossInput.value = '';
          grossInput.placeholder = row.gross ? row.gross + ' ' + currencySym() + ' (aylık)' : 'Aylık maaş kullanılır';
        }
        setField(form, 'notes', '');
        refreshPreview(pid, 0);
      } else if (mode === 'settings') {
        setField(form, 'personnel', pid);
        setField(form, 'period', data.period || '');
        setField(form, 'monthly_salary', data.gross || row.gross || '');
        setField(form, 'salary_pay_date', data.payDate || row.due_date || todayIso());
      } else if (mode === 'cycle') {
        setField(form, 'personnel', pid);
        setField(form, 'period', data.period || '');
        setField(form, 'salary_pay_date', data.payDate || row.due_date || todayIso());
        setField(form, 'notes', '');
        refreshPreview(pid, 0);
      }

      backdrop.classList.add('is-open');
      panel.classList.add('is-open');
      backdrop.setAttribute('aria-hidden', 'false');
      panel.setAttribute('aria-hidden', 'false');
      document.body.classList.add('overflow-hidden');

      const focusTarget = form.querySelector('input:not([type="hidden"]), select, textarea');
      if (focusTarget) {
        window.setTimeout(function () {
          focusTarget.focus();
        }, 120);
      }
    }

    function close() {
      backdrop.classList.remove('is-open');
      panel.classList.remove('is-open');
      backdrop.setAttribute('aria-hidden', 'true');
      panel.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('overflow-hidden');
    }

    backdrop.addEventListener('click', close);
    document.querySelectorAll('[data-acct-sheet-close]').forEach(function (btn) {
      btn.addEventListener('click', close);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.classList.contains('is-open')) close();
    });

    document.querySelectorAll('[data-payroll-action]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        open(btn.dataset.payrollAction, {
          personnelId: btn.dataset.personnelId,
          personnelName: btn.dataset.personnelName,
          period: btn.dataset.period,
          periodLabel: btn.dataset.periodLabel,
          gross: btn.dataset.gross,
          payDate: btn.dataset.payDate,
          amount: btn.dataset.amount,
        });
      });
    });

    const advanceForm = forms.advance;
    if (advanceForm) {
      const amountInput = advanceForm.querySelector('input[name="amount"]');
      const personnelSelect = advanceForm.querySelector('select[name="personnel"]');
      if (personnelSelect) {
        personnelSelect.addEventListener('change', function () {
          refreshPreview(this.value, amountInput && amountInput.value);
        });
      }
      if (amountInput) {
        amountInput.addEventListener('input', function () {
          refreshPreview(personnelSelect && personnelSelect.value, amountInput.value);
        });
      }
      advanceForm.addEventListener('submit', function (e) {
        const val = parseMoney(amountInput && amountInput.value);
        if (!personnelSelect || !personnelSelect.value) {
          e.preventDefault();
          window.erpNotify?.('Personel seçin.', 'warn');
          return;
        }
        if (val <= 0) {
          e.preventDefault();
          window.erpNotify?.('Geçerli bir avans tutarı girin.', 'warn');
        }
      });
    }

    const salaryForm = forms.salary;
    if (salaryForm) {
      const personnelSelect = salaryForm.querySelector('select[name="personnel"]');
      if (personnelSelect) {
        personnelSelect.addEventListener('change', function () {
          refreshPreview(this.value, 0);
        });
      }
    }

    document.querySelectorAll('[data-acct-quick-amount]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const form = forms.advance;
        if (!form) return;
        const amountInput = form.querySelector('input[name="amount"]');
        const personnelSelect = form.querySelector('select[name="personnel"]');
        if (amountInput) amountInput.value = btn.dataset.amount;
        refreshPreview(personnelSelect && personnelSelect.value, btn.dataset.amount);
      });
    });

    return { open: open, close: close };
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindSheet();

    document.querySelectorAll('form[data-acct-confirm]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        const msg = form.getAttribute('data-acct-confirm');
        if (msg && !window.confirm(msg)) e.preventDefault();
      });
    });
  });
})();
