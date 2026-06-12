/**
 * Hızlı arama (/) ve bildirim paneli.
 */
(function () {
    'use strict';

    const searchUrl = '/api/hizli-arama/';
    const notificationsUrl = '/api/bildirimler/';
    const markAllUrl = '/api/bildirimler/tumu-okundu/';

    function csrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function isTypingTarget(el) {
        if (!el) return false;
        const tag = el.tagName;
        return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
    }

    /* —— Hızlı arama —— */
    const modal = document.getElementById('erpQuickSearchModal');
    const backdrop = document.getElementById('erpQuickSearchBackdrop');
    const input = document.getElementById('erpQuickSearchInput');
    const resultsEl = document.getElementById('erpQuickSearchResults');
    const openBtns = [
        document.getElementById('erpQuickSearchOpen'),
        document.getElementById('erpQuickSearchOpenMobile'),
    ].filter(Boolean);

    let searchTimer = null;
    let activeIndex = -1;
    let lastItems = [];

    function openSearch() {
        if (!modal || !input) return;
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        input.value = '';
        activeIndex = -1;
        lastItems = [];
        renderResults([], []);
        window.setTimeout(() => input.focus(), 50);
        fetchSearch('');
    }

    function closeSearch() {
        if (!modal) return;
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        activeIndex = -1;
    }

    function renderGroup(title, items, startIndex) {
        if (!items.length) return '';
        const rows = items.map((item, i) => {
            const idx = startIndex + i;
            const selected = idx === activeIndex ? ' bg-brand-50 border-brand-200' : ' border-transparent hover:bg-slate-50';
            return `
                <a href="${item.url}" data-qs-index="${idx}" class="erp-qs-item flex items-start gap-3 px-3 py-2.5 rounded-xl border${selected}">
                    <span class="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                        <i data-lucide="${item.icon || 'arrow-right'}" class="w-4 h-4"></i>
                    </span>
                    <span class="min-w-0 flex-1">
                        <span class="block text-sm font-semibold text-slate-900 truncate">${item.title}</span>
                        <span class="block text-xs text-slate-500 truncate">${item.subtitle || ''}</span>
                    </span>
                    <span class="text-[10px] font-bold uppercase text-slate-400 shrink-0 pt-1">${item.group || ''}</span>
                </a>`;
        }).join('');
        return `<div class="mb-2"><p class="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">${title}</p>${rows}</div>`;
    }

    function renderResults(pages, records) {
        if (!resultsEl) return;
        lastItems = [...pages, ...records];
        if (!lastItems.length) {
            resultsEl.innerHTML = '<p class="px-3 py-6 text-center text-sm text-slate-400">Sonuç bulunamadı</p>';
            return;
        }
        let html = '';
        if (pages.length) html += renderGroup('Sayfalar & işlemler', pages, 0);
        if (records.length) html += renderGroup('Kayıtlar', records, pages.length);
        resultsEl.innerHTML = html;
        if (window.lucide) lucide.createIcons();
        highlightActive();
    }

    function highlightActive() {
        resultsEl?.querySelectorAll('.erp-qs-item').forEach((el) => {
            const idx = parseInt(el.dataset.qsIndex, 10);
            el.classList.toggle('bg-brand-50', idx === activeIndex);
            el.classList.toggle('border-brand-200', idx === activeIndex);
            el.classList.toggle('border-transparent', idx !== activeIndex);
        });
    }

    function fetchSearch(q) {
        const url = q ? `${searchUrl}?q=${encodeURIComponent(q)}` : searchUrl;
        fetch(url, { headers: { Accept: 'application/json' } })
            .then((r) => r.json())
            .then((data) => {
                if (!data.ok) return;
                renderResults(data.pages || [], data.records || []);
            })
            .catch(() => {});
    }

    openBtns.forEach((btn) => btn.addEventListener('click', openSearch));
    backdrop?.addEventListener('click', closeSearch);

    input?.addEventListener('input', () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(() => fetchSearch(input.value.trim()), 120);
        activeIndex = -1;
    });

    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            e.preventDefault();
            closeSearch();
            return;
        }
        if (!lastItems.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, lastItems.length - 1);
            highlightActive();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            highlightActive();
        } else if (e.key === 'Enter' && activeIndex >= 0) {
            e.preventDefault();
            const item = lastItems[activeIndex];
            if (item?.url) window.location.href = item.url;
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
        if (isTypingTarget(document.activeElement)) return;
        e.preventDefault();
        openSearch();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeSearch();
        }
    });

    /* —— Bildirimler —— */
    const notifBtn = document.getElementById('erpNotificationsBtn');
    const notifPanel = document.getElementById('erpNotificationsPanel');
    const notifList = document.getElementById('erpNotificationsList');
    const notifBadge = document.getElementById('erpNotificationsBadge');
    const markAllBtn = document.getElementById('erpNotificationsMarkAll');
    const notifWrap = document.getElementById('erpNotificationsWrap');

    function setUnread(count) {
        if (!notifBadge) return;
        if (count > 0) {
            notifBadge.textContent = count > 99 ? '99+' : String(count);
            notifBadge.classList.remove('hidden');
            notifBadge.classList.add('flex');
        } else {
            notifBadge.classList.add('hidden');
            notifBadge.classList.remove('flex');
        }
    }

    function levelClass(level) {
        if (level === 'warning') return 'bg-amber-100 text-amber-700';
        if (level === 'success') return 'bg-emerald-100 text-emerald-700';
        return 'bg-slate-100 text-slate-600';
    }

    function renderNotifications(items) {
        if (!notifList) return;
        if (!items.length) {
            notifList.innerHTML = '<p class="px-4 py-8 text-center text-sm text-slate-400">Bildirim yok</p>';
            return;
        }
        notifList.innerHTML = items.map((n) => {
            const unread = n.is_read ? '' : ' bg-brand-50/40';
            const body = n.body ? `<p class="text-xs text-slate-500 mt-0.5 line-clamp-2">${n.body}</p>` : '';
            const tag = `<span class="inline-block mt-1 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${levelClass(n.level)}">${n.source}</span>`;
            const inner = `
                <div class="px-4 py-3${unread}">
                    <div class="flex items-start justify-between gap-2">
                        <p class="text-sm font-semibold text-slate-900 leading-snug">${n.title}</p>
                        <span class="text-[10px] text-slate-400 shrink-0">${n.created_label || ''}</span>
                    </div>
                    ${body}
                    ${tag}
                </div>`;
            if (n.link) {
                return `<a href="${n.link}" data-notif-id="${n.id}" class="block hover:bg-slate-50 transition-colors">${inner}</a>`;
            }
            return `<div data-notif-id="${n.id}">${inner}</div>`;
        }).join('');
    }

    function loadNotifications() {
        fetch(notificationsUrl, { headers: { Accept: 'application/json' } })
            .then((r) => r.json())
            .then((data) => {
                if (!data.ok) return;
                setUnread(data.unread || 0);
                renderNotifications(data.items || []);
            })
            .catch(() => {});
    }

    function toggleNotifications() {
        if (!notifPanel) return;
        notifPanel.classList.toggle('hidden');
        const isOpen = !notifPanel.classList.contains('hidden');
        notifBtn?.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        if (isOpen) loadNotifications();
    }

    notifBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNotifications();
    });

    document.addEventListener('click', (e) => {
        if (!notifWrap || notifPanel?.classList.contains('hidden')) return;
        if (!notifWrap.contains(e.target)) {
            notifPanel.classList.add('hidden');
            notifBtn?.setAttribute('aria-expanded', 'false');
        }
    });

    notifList?.addEventListener('click', (e) => {
        const link = e.target.closest('[data-notif-id]');
        if (!link) return;
        const id = link.dataset.notifId;
        if (!id) return;
        fetch(`/api/bildirimler/${id}/okundu/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                Accept: 'application/json',
            },
        }).catch(() => {});
    });

    markAllBtn?.addEventListener('click', () => {
        fetch(markAllUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                Accept: 'application/json',
            },
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.ok) {
                    setUnread(0);
                    loadNotifications();
                }
            })
            .catch(() => {});
    });

    if (notifBtn) {
        loadNotifications();
        window.setInterval(loadNotifications, 120000);
    }

    /* —— Sidebar: mobilde satır altı, masaüstünde hub yanında küçük popup —— */
    const popoverMq = window.matchMedia('(min-width: 1024px)');
    let hoverOpenTimer = null;
    let hoverCloseTimer = null;

    function clearPopoverPosition(menu) {
        if (!menu) return;
        menu.style.top = '';
        menu.style.left = '';
        menu.style.maxHeight = '';
        menu.style.height = '';
        menu.style.width = '';
        menu.style.overflow = '';
        menu.style.visibility = '';
        menu.style.display = '';
        menu.classList.remove('is-popover-ready');
    }

    function positionSidebarPopover(block) {
        const row = block.querySelector('.erp-sidebar-module__hub-row');
        const menu = block.querySelector('[data-erp-module-menu]');
        if (!row || !menu) return;

        const gap = 8;
        const pad = 8;
        const rowRect = row.getBoundingClientRect();
        const width = Math.min(232, window.innerWidth * 0.32);
        let left = rowRect.right + gap;

        if (left + width > window.innerWidth - pad) {
            left = Math.max(pad, rowRect.left - width - gap);
        }

        menu.style.width = `${width}px`;
        menu.style.maxHeight = 'none';
        menu.style.height = 'auto';
        menu.style.overflow = 'visible';
        menu.style.left = '-10000px';
        menu.style.top = '0';
        menu.style.visibility = 'hidden';
        menu.style.display = 'block';

        const menuHeight = menu.offsetHeight;
        const viewportH = window.innerHeight;
        let top = rowRect.top;

        if (menuHeight > viewportH - pad * 2) {
            top = pad;
        } else if (top + menuHeight > viewportH - pad) {
            top = Math.max(pad, viewportH - menuHeight - pad);
        }
        if (top < pad) {
            top = pad;
        }

        menu.style.left = `${left}px`;
        menu.style.top = `${top}px`;
        menu.style.visibility = '';
        menu.style.display = '';
        menu.classList.add('is-popover-ready');
    }

    function closeAllSidebarModules() {
        document.querySelectorAll('.erp-sidebar-module--expanded').forEach((block) => {
            block.classList.remove('erp-sidebar-module--expanded');
            const toggle = block.querySelector('[data-erp-module-toggle]');
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
            clearPopoverPosition(block.querySelector('[data-erp-module-menu]'));
        });
    }

    function openSidebarModule(block, btn) {
        closeAllSidebarModules();
        block.classList.add('erp-sidebar-module--expanded');
        if (btn) btn.setAttribute('aria-expanded', 'true');
        if (popoverMq.matches) {
            positionSidebarPopover(block);
            if (window.lucide) lucide.createIcons();
        } else {
            window.requestAnimationFrame(() => {
                block.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            });
        }
    }

    function cancelHoverTimers() {
        window.clearTimeout(hoverOpenTimer);
        window.clearTimeout(hoverCloseTimer);
    }

    function schedulePopoverOpen(block) {
        if (!popoverMq.matches) return;
        cancelHoverTimers();
        hoverOpenTimer = window.setTimeout(() => {
            const btn = block.querySelector('[data-erp-module-toggle]');
            openSidebarModule(block, btn);
        }, 160);
    }

    function schedulePopoverClose() {
        if (!popoverMq.matches) return;
        cancelHoverTimers();
        hoverCloseTimer = window.setTimeout(closeAllSidebarModules, 220);
    }

    function wireSidebarPopoverHover(block) {
        const menu = block.querySelector('[data-erp-module-menu]');
        block.addEventListener('mouseenter', () => schedulePopoverOpen(block));
        block.addEventListener('mouseleave', schedulePopoverClose);
        if (menu) {
            menu.addEventListener('mouseenter', cancelHoverTimers);
            menu.addEventListener('mouseleave', schedulePopoverClose);
        }
    }

    function handleSidebarModuleToggle(event) {
        const btn = event.target.closest('[data-erp-module-toggle]');
        if (!btn) return;
        event.preventDefault();
        event.stopPropagation();
        const block = btn.closest('[data-erp-sidebar-module]');
        if (!block) return;
        cancelHoverTimers();
        const wasOpen = block.classList.contains('erp-sidebar-module--expanded');
        if (wasOpen) {
            closeAllSidebarModules();
        } else {
            openSidebarModule(block, btn);
        }
    }

    document.addEventListener('click', handleSidebarModuleToggle);

    document.addEventListener('click', (event) => {
        if (!popoverMq.matches) return;
        const inside = event.target.closest('[data-erp-sidebar-module], [data-erp-module-menu]');
        if (!inside) closeAllSidebarModules();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeAllSidebarModules();
    });

    window.addEventListener('resize', () => {
        if (!popoverMq.matches) {
            document.querySelectorAll('[data-erp-module-menu]').forEach(clearPopoverPosition);
            return;
        }
        const openMenu = document.querySelector('.erp-sidebar-module__menu.is-popover-ready');
        if (!openMenu) return;
        const block = openMenu.closest('[data-erp-sidebar-module]');
        if (block) positionSidebarPopover(block);
    });

    function initSidebarPopovers() {
        document.querySelectorAll('[data-erp-sidebar-module]').forEach(wireSidebarPopoverHover);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebarPopovers);
    } else {
        initSidebarPopovers();
    }
})();
