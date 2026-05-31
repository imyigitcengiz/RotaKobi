/** Modül / entegrasyon aç-kapa — sayfa yenilemeden, scroll korunur. */
(function (global) {
  function csrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function toast(message, level) {
    if (global.GyToast) {
      const fn = global.GyToast[level] || global.GyToast.info;
      fn(message);
      return;
    }
    const el = document.createElement('div');
    el.className = 'fixed bottom-4 right-4 z-[300] px-4 py-2 rounded-xl bg-slate-900 text-white text-sm shadow-lg';
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 3500);
  }

  function findCard(btn) {
    return btn.closest('[data-module-card]');
  }

  function applyCardState(card, data) {
    const installed = !!data.installed;
    const kind = card.dataset.moduleKind || data.kind || 'app';
    const isIntegration = kind === 'integration';

    card.dataset.moduleInstalled = installed ? '1' : '0';

    card.classList.toggle('border-emerald-200', installed && !isIntegration);
    card.classList.toggle('border-slate-200', !installed && !isIntegration);
    card.classList.toggle('border-amber-200', installed && isIntegration);

    const badge = card.querySelector('[data-module-badge]');
    if (badge) {
      badge.textContent = installed ? 'Açık' : 'Kapalı';
      badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-lg h-fit '
        + (installed ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500');
    }

    const btn = card.querySelector('[data-module-toggle]');
    if (btn && data.can_toggle !== false) {
      btn.textContent = installed ? 'Kapat' : 'Aç';
      btn.classList.toggle('text-red-600', installed);
      btn.classList.toggle('text-emerald-700', !installed);
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
    }

    const actions = card.querySelector('[data-module-actions]');
    if (!actions) return;

    let openLink = actions.querySelector('[data-module-open]');
    let permHint = actions.querySelector('[data-module-perm-hint]');

    if (installed && data.can_open && data.open_url) {
      if (permHint) permHint.remove();
      if (!openLink) {
        openLink = document.createElement('a');
        openLink.dataset.moduleOpen = '1';
        openLink.className = isIntegration
          ? 'px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-bold hover:bg-amber-600'
          : 'px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold';
        openLink.textContent = isIntegration ? 'Kullan' : 'Aç';
        actions.insertBefore(openLink, actions.firstChild);
      }
      openLink.href = data.open_url;
      openLink.classList.remove('hidden');
    } else if (openLink) {
      openLink.remove();
    }

    if (installed && !data.can_open) {
      if (!permHint) {
        permHint = document.createElement('span');
        permHint.dataset.modulePermHint = '1';
        permHint.className = 'text-xs text-amber-700 font-semibold';
        permHint.textContent = 'Rol izni gerekir';
        actions.insertBefore(permHint, actions.firstChild);
      }
    } else if (permHint) {
      permHint.remove();
    }
  }

  function updateCounters(data) {
    const hubCount = document.querySelector('[data-module-installed-count]');
    if (hubCount && data.installed_count != null) {
      hubCount.textContent = data.installed_count + ' açık';
    }
    const capCount = document.querySelector('[data-capabilities-enabled-count]');
    if (capCount && data.capabilities_enabled != null) {
      capCount.textContent = String(data.capabilities_enabled);
    }
  }

  async function toggleModule(btn) {
    const slug = btn.dataset.moduleSlug;
    if (!slug || btn.disabled) return;

    const card = findCard(btn);
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    const prevLabel = btn.textContent;
    btn.textContent = '…';

    try {
      const body = new URLSearchParams();
      body.set('module_slug', slug);

      const res = await fetch(global.MODULE_TOGGLE_URL || '/panel/moduller/toggle/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken(),
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: body.toString(),
      });

      const data = await res.json().catch(function () { return { ok: false, error: 'Yanıt okunamadı.' }; });

      if (!res.ok || !data.ok) {
        toast(data.error || 'İşlem başarısız.', 'error');
        btn.textContent = prevLabel;
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        return;
      }

      if (card) applyCardState(card, data);
      document.querySelectorAll('[data-module-card][data-module-slug="' + slug + '"]').forEach(function (c) {
        if (c !== card) applyCardState(c, data);
      });
      updateCounters(data);
      toast(data.message, data.level || 'success');
      window.setTimeout(function () { window.location.reload(); }, 450);
    } catch (err) {
      toast('Bağlantı hatası — tekrar deneyin.', 'error');
      btn.textContent = prevLabel;
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
    }
  }

  function bind(root) {
    (root || document).querySelectorAll('[data-module-toggle]').forEach(function (btn) {
      if (btn.dataset.moduleToggleBound) return;
      btn.dataset.moduleToggleBound = '1';
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        toggleModule(btn);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bind(document);
    document.querySelectorAll('form[data-preserve-scroll]').forEach(function (form) {
      form.addEventListener('submit', function () {
        try { sessionStorage.setItem('moduleHubScrollY', String(window.scrollY)); } catch (e) { /* ignore */ }
      });
    });
    try {
      const y = sessionStorage.getItem('moduleHubScrollY');
      if (y != null) {
        sessionStorage.removeItem('moduleHubScrollY');
        requestAnimationFrame(function () { window.scrollTo(0, parseInt(y, 10) || 0); });
      }
    } catch (e) { /* ignore */ }
  });

  global.ModuleToggle = { bind: bind, toggle: toggleModule };
})(window);
