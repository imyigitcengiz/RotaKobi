(function () {
    const cfg = window.GY_TEAM_CHAT;
    if (!cfg) return;

    const panel = document.getElementById('teamChatPanel');
    const toggle = document.getElementById('teamChatToggle');
    const closeBtn = document.getElementById('teamChatClose');
    const badge = document.getElementById('teamChatBadge');
    const threadList = document.getElementById('teamChatThreadList');
    const userList = document.getElementById('teamChatUserList');
    const messagesEl = document.getElementById('teamChatMessages');
    const form = document.getElementById('teamChatForm');
    const input = document.getElementById('teamChatInput');
    const subtitle = document.getElementById('teamChatSubtitle');

    let open = false;
    let activeThreadId = null;
    let lastMessageId = 0;
    let threads = [];
    let users = [];
    let pollTimer = null;
    let socket = null;
    let reconnectDelay = 1000;

    function csrf() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    function escapeHtml(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function formatTime(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        const now = new Date();
        const sameDay = d.toDateString() === now.toDateString();
        return sameDay
            ? d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })
            : d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    }

    function setBadge(n) {
        if (!badge) return;
        if (n > 0) {
            badge.textContent = n > 99 ? '99+' : String(n);
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    async function apiPost(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify(body || {}),
        });
        return res.json();
    }

    async function loadSummary() {
        const res = await fetch(cfg.api.summary);
        const data = await res.json();
        if (!data.ok) return;
        threads = data.threads || [];
        setBadge(data.unread_total || 0);
        renderThreadList();
        if (!activeThreadId && data.team_thread) {
            await openThread(data.team_thread.id);
        }
    }

    async function loadUsers() {
        const res = await fetch(cfg.api.users);
        const data = await res.json();
        if (!data.ok) return;
        users = data.users || [];
        renderUserList();
    }

    function renderThreadList() {
        if (!threadList) return;
        if (!threads.length) {
            threadList.innerHTML = '<p class="text-xs text-slate-400 p-2">Sohbet yok</p>';
            return;
        }
        threadList.innerHTML = threads.map((t) => {
            const active = t.id === activeThreadId;
            const unread = t.unread > 0 ? `<span class="ml-auto text-[10px] font-bold bg-violet-600 text-white px-1.5 rounded-full">${t.unread}</span>` : '';
            const preview = t.last_message ? escapeHtml(t.last_message.body.slice(0, 40)) : 'Mesaj yok';
            const icon = t.kind === 'team' ? 'users' : 'user';
            return `<button type="button" data-thread-id="${t.id}" class="w-full text-left px-2 py-2 rounded-lg flex items-start gap-2 ${active ? 'bg-white shadow-sm border border-slate-200' : 'hover:bg-white/80'}">
                <span class="w-7 h-7 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center shrink-0 text-[10px] font-bold">${t.kind === 'team' ? '#' : escapeHtml(t.peer?.initials || t.title?.slice(0, 2) || '?')}</span>
                <span class="min-w-0 flex-1">
                    <span class="flex items-center gap-1"><span class="font-semibold text-slate-800 truncate text-xs">${escapeHtml(t.title)}</span>${unread}</span>
                    <span class="text-[10px] text-slate-400 truncate block">${preview}</span>
                </span>
            </button>`;
        }).join('');
        threadList.querySelectorAll('[data-thread-id]').forEach((btn) => {
            btn.addEventListener('click', () => openThread(Number(btn.dataset.threadId)));
        });
    }

    function renderUserList() {
        if (!userList) return;
        userList.innerHTML = users.map((u) =>
            `<button type="button" data-user-id="${u.id}" class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-white text-xs text-slate-700 flex items-center gap-2">
                <span class="w-6 h-6 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-[9px] font-bold">${escapeHtml(u.initials)}</span>
                <span class="truncate">${escapeHtml(u.name)}</span>
            </button>`
        ).join('');
        userList.querySelectorAll('[data-user-id]').forEach((btn) => {
            btn.addEventListener('click', () => startDirect(Number(btn.dataset.userId)));
        });
    }

    function renderMessages(items, append) {
        if (!append) messagesEl.innerHTML = '';
        const meId = cfg.me.id;
        items.forEach((m) => {
            const mine = m.sender.id === meId;
            const row = document.createElement('div');
            row.className = `flex ${mine ? 'justify-end' : 'justify-start'}`;
            row.dataset.msgId = m.id;
            row.innerHTML = mine
                ? `<div class="max-w-[85%]"><div class="bg-violet-600 text-white px-3 py-2 rounded-2xl rounded-br-md text-sm">${escapeHtml(m.body)}</div><p class="text-[10px] text-slate-400 text-right mt-0.5">${formatTime(m.created_at)}</p></div>`
                : `<div class="max-w-[85%]"><p class="text-[10px] font-bold text-slate-500 mb-0.5">${escapeHtml(m.sender.name)}</p><div class="bg-white border border-slate-200 px-3 py-2 rounded-2xl rounded-tl-md text-sm text-slate-800 shadow-sm">${escapeHtml(m.body)}</div><p class="text-[10px] text-slate-400 mt-0.5">${formatTime(m.created_at)}</p></div>`;
            messagesEl.appendChild(row);
            lastMessageId = Math.max(lastMessageId, m.id);
        });
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function openThread(threadId) {
        activeThreadId = threadId;
        lastMessageId = 0;
        renderThreadList();
        const t = threads.find((x) => x.id === threadId);
        if (subtitle && t) subtitle.textContent = t.title;
        messagesEl.innerHTML = '<p class="text-center text-slate-400 text-sm py-8">Yükleniyor…</p>';
        const res = await fetch(cfg.api.messages(threadId));
        const data = await res.json();
        if (!data.ok) {
            messagesEl.innerHTML = `<p class="text-red-600 text-sm p-4">${escapeHtml(data.error || 'Yüklenemedi')}</p>`;
            return;
        }
        renderMessages(data.messages || [], false);
        await fetch(cfg.api.read(threadId), { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
        await loadSummary();
    }

    async function startDirect(userId) {
        const data = await apiPost(cfg.api.direct, { user_id: userId });
        if (!data.ok) {
            alert(data.error || 'Sohbet açılamadı');
            return;
        }
        await loadSummary();
        await openThread(data.thread.id);
    }

    async function pollNewMessages() {
        if (!activeThreadId || !open) return;
        const res = await fetch(cfg.api.messages(activeThreadId) + '?since=' + lastMessageId);
        const data = await res.json();
        if (data.ok && data.messages && data.messages.length) {
            renderMessages(data.messages, true);
            await fetch(cfg.api.read(activeThreadId), { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
        }
    }

    function onWsPayload(payload) {
        if (!payload || payload.event !== 'chat.message' || !payload.message) return;
        const m = payload.message;
        if (m.thread_id === activeThreadId && open) {
            if (!messagesEl.querySelector(`[data-msg-id="${m.id}"]`)) {
                renderMessages([m], true);
                fetch(cfg.api.read(activeThreadId), { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
            }
        }
        loadSummary();
    }

    function connectWs() {
        try {
            socket = new WebSocket(cfg.wsUrl);
            socket.onopen = () => { reconnectDelay = 1000; };
            socket.onmessage = (ev) => {
                try { onWsPayload(JSON.parse(ev.data)); } catch (e) {}
            };
            socket.onclose = () => {
                setTimeout(connectWs, reconnectDelay);
                reconnectDelay = Math.min(reconnectDelay * 2, 12000);
            };
        } catch (e) {}
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text || !activeThreadId) return;
        input.value = '';
        const data = await apiPost(cfg.api.send(activeThreadId), { body: text });
        if (!data.ok) {
            alert(data.error || 'Gönderilemedi');
            input.value = text;
            return;
        }
        if (!messagesEl.querySelector(`[data-msg-id="${data.message.id}"]`)) {
            renderMessages([data.message], true);
        }
        loadSummary();
    });

    function setOpen(val) {
        open = val;
        panel.classList.toggle('hidden', !open);
        if (open) {
            input.focus();
            loadSummary();
            loadUsers();
            apiPost(cfg.api.joinTeam, {});
            if (!pollTimer) pollTimer = setInterval(pollNewMessages, 4000);
        }
        if (window.lucide) lucide.createIcons();
    }

    toggle.addEventListener('click', () => setOpen(!open));
    closeBtn.addEventListener('click', () => setOpen(false));

    connectWs();
    loadSummary();
    setInterval(loadSummary, 30000);
})();
