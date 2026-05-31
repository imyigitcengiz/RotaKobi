(function () {
  function ensureToastHost() {
    let host = document.getElementById('erpToastHost');
    if (!host) {
      host = document.createElement('div');
      host.id = 'erpToastHost';
      host.className = 'fixed top-4 right-4 z-[300] space-y-2 max-w-md pointer-events-none';
      host.setAttribute('role', 'status');
      host.setAttribute('aria-live', 'polite');
      document.body.appendChild(host);
    }
    return host;
  }

  function toast(message, type) {
    if (!message) return;
    const host = ensureToastHost();
    const styles = {
      success: 'pointer-events-auto px-5 py-3 rounded-2xl shadow-xl border text-sm font-semibold bg-emerald-50 border-emerald-200 text-emerald-800',
      warn: 'pointer-events-auto px-5 py-3 rounded-2xl shadow-xl border text-sm font-semibold bg-amber-50 border-amber-200 text-amber-800',
      error: 'pointer-events-auto px-5 py-3 rounded-2xl shadow-xl border text-sm font-semibold bg-red-50 border-red-200 text-red-800',
    };
    const el = document.createElement('div');
    el.className = styles[type] || styles.error;
    el.textContent = String(message);
    host.appendChild(el);
    window.setTimeout(function () {
      el.remove();
    }, 4500);
  }

  window.erpUi = {
    toast: toast,
    notify: function (message, type) {
      toast(message, type || 'error');
    },
  };

  window.erpNotify = window.erpUi.notify;
})();
