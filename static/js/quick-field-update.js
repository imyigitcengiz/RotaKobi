/** Durum/öncelik hızlı güncelleme — tam sayfa yenilemesi yerine rozet günceller. */
(function (global) {
  function hexToRgba(hex, alpha) {
    const h = (hex || '#64748b').replace('#', '');
    if (h.length !== 6) return `rgba(100, 116, 139, ${alpha})`;
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function applyBadgeStyles(el, hex) {
    if (!el || !hex) return;
    el.style.backgroundColor = hexToRgba(hex, 0.12);
    el.style.color = hex;
    el.style.borderColor = hexToRgba(hex, 0.35);
  }

  function patchQuickField(serviceId, field, data) {
    const wrap = document.querySelector(
      `.quick-update-wrap[data-service-id="${serviceId}"][data-field="${field}"]`
    );
    if (!wrap || !data?.label) return false;
    const trigger = wrap.querySelector('.quick-update-trigger');
    if (!trigger) return false;
    if (field === 'priority') {
      trigger.innerHTML = `<span class="w-1.5 h-1.5 rounded-full shrink-0" style="background-color:${data.color}"></span> ${data.label}`;
    } else {
      trigger.textContent = data.label;
    }
    applyBadgeStyles(trigger, data.color);
    return true;
  }

  global.GyQuickFieldUpdate = { patchQuickField, applyBadgeStyles };
})(window);
