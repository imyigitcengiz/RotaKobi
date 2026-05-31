const express = require('express');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = process.env.WHATSAPP_BRIDGE_PORT || 3939;
/** Docker / Coolify: 0.0.0.0 — yerel geliştirme varsayılanı 127.0.0.1 */
const BIND_HOST = process.env.WHATSAPP_BRIDGE_BIND || '127.0.0.1';
const SECRETS_DIR = process.env.COOLOPS_SECRETS_DIR || process.env.KOBIOPS_SECRETS_DIR || '/run/kobiops-secrets';
const app = express();

function readBridgeToken() {
  const env = (process.env.WHATSAPP_BRIDGE_TOKEN || '').trim();
  if (env) return env;
  try {
    const tokenPath = path.join(SECRETS_DIR, 'whatsapp_bridge_token');
    return fs.readFileSync(tokenPath, 'utf8').trim();
  } catch (_) {
    return '';
  }
}

app.use(express.json({ limit: '1mb' }));

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'gy-whatsapp-bridge' });
});

app.use((req, res, next) => {
  if (req.path === '/health') return next();
  const expected = readBridgeToken();
  if (!expected) {
    if (BIND_HOST !== '127.0.0.1' && BIND_HOST !== '::1') {
      return res.status(503).json({ ok: false, error: 'Bridge token not configured yet.' });
    }
    return next();
  }
  const auth = req.headers.authorization || '';
  if (auth !== `Bearer ${expected}`) {
    return res.status(401).json({ ok: false, error: 'Unauthorized' });
  }
  next();
});

/* WhatsApp Bağlan sayfasında gösterilecek dosya günlüğü — bridge_ui.log */
(function attachUiLogMirror() {
  const logPath = path.join(__dirname, 'bridge_ui.log');
  const maxSize = 100000;
  function append(level, args) {
    const parts = args.map((a) => {
      if (a instanceof Error) return a.stack || a.message;
      try {
        return typeof a === 'string' ? a : JSON.stringify(a);
      } catch (_) {
        return String(a);
      }
    });
    const line = `[${new Date().toISOString()}] [${level}] ${parts.join(' ')}\n`;
    try {
      fs.appendFileSync(logPath, line, 'utf8');
      const st = fs.statSync(logPath);
      if (st.size > maxSize) {
        const txt = fs.readFileSync(logPath, 'utf8');
        fs.writeFileSync(logPath, txt.slice(-Math.floor(maxSize / 2)), 'utf8');
      }
    } catch (_) {}
  }
  const origLog = console.log.bind(console);
  const origErr = console.error.bind(console);
  const origWarn = console.warn.bind(console);
  console.log = (...a) => { origLog(...a); append('log', a); };
  console.error = (...a) => { origErr(...a); append('error', a); };
  console.warn = (...a) => { origWarn(...a); append('warn', a); };
})();

/** @type {Map<string, { client: import('whatsapp-web.js').Client | null, initializing: boolean, state: object }>} */
const sessions = new Map();

function defaultState() {
  return {
    status: 'disconnected',
    qrDataUrl: null,
    phone: null,
    pushname: null,
    lastError: null,
  };
}

function getSession(id) {
  const key = String(id || '').trim();
  if (!key) throw new Error('Bağlantı kimliği gerekli.');
  if (!sessions.has(key)) {
    sessions.set(key, { client: null, initializing: false, state: defaultState() });
  }
  return sessions.get(key);
}

function serializeSession(id, session) {
  return {
    id: String(id),
    status: session.state.status,
    phone: session.state.phone,
    pushname: session.state.pushname,
    qrDataUrl: session.state.qrDataUrl,
    lastError: session.state.lastError,
    initializing: session.initializing,
  };
}

function chatIdFromPhone(phone) {
  const digits = String(phone || '').replace(/\D/g, '');
  if (!digits) throw new Error('Geçersiz telefon numarası.');
  if (digits.startsWith('90') && digits.length >= 12 && digits[2] !== '5') {
    throw new Error('Sabit hat numarası WhatsApp ile gönderilemez.');
  }
  if (digits.startsWith('0') && digits.length >= 3 && '234'.includes(digits[1]) && !digits.startsWith('05')) {
    throw new Error('Sabit hat numarası WhatsApp ile gönderilemez.');
  }
  return `${digits}@c.us`;
}

function attachClientEvents(id, session, waClient) {
  waClient.on('qr', async (qr) => {
    console.log(`[${id}] QR kodu hazır`);
    session.state.status = 'qr';
    session.state.qrDataUrl = await qrcode.toDataURL(qr);
    session.state.lastError = null;
  });

  waClient.on('authenticated', () => {
    session.state.lastError = null;
  });

  waClient.on('ready', () => {
    session.state.status = 'ready';
    session.state.qrDataUrl = null;
    session.state.lastError = null;
    const wid = waClient.info && waClient.info.wid;
    session.state.phone = wid ? wid.user : null;
    session.state.pushname = waClient.info ? waClient.info.pushname : null;
    console.log(`[${id}] WhatsApp hazır (${session.state.phone || 'numara yok'})`);
  });

  waClient.on('auth_failure', (msg) => {
    session.state.status = 'disconnected';
    session.state.lastError = msg || 'Kimlik doğrulama başarısız.';
  });

  waClient.on('disconnected', (reason) => {
    Object.assign(session.state, defaultState());
    session.state.lastError = reason || 'Bağlantı kesildi.';
    session.client = null;
    session.initializing = false;
  });
}

const SESSION_DIR = path.join(__dirname, 'session');

function listPersistedSessionIds() {
  const ids = [];
  try {
    if (!fs.existsSync(SESSION_DIR)) return ids;
    for (const name of fs.readdirSync(SESSION_DIR)) {
      const m = name.match(/^session-(.+)$/);
      if (m) ids.push(m[1]);
    }
  } catch (err) {
    console.warn('Oturum klasörü okunamadı:', err.message || err);
  }
  return ids;
}

async function restorePersistedSessions() {
  const ids = listPersistedSessionIds();
  if (!ids.length) return;
  console.log(`Kayıtlı ${ids.length} WhatsApp oturumu geri yükleniyor…`);
  for (const id of ids) {
    try {
      await ensureClient(id);
    } catch (err) {
      console.warn(`[${id}] Geri yükleme hatası:`, err.message || err);
    }
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
}

async function ensureClient(id) {
  const session = getSession(id);
  if (session.client || session.initializing) return session;
  session.initializing = true;
  session.state.lastError = null;
  session.state.status = 'connecting';
  console.log(`[${id}] WhatsApp istemcisi başlatılıyor…`);

  const puppeteerOpts = {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--no-zygote',
    ],
  };
  const chromePath = (process.env.PUPPETEER_EXECUTABLE_PATH || '').trim();
  if (chromePath) {
    puppeteerOpts.executablePath = chromePath;
  }

  const waClient = new Client({
    authStrategy: new LocalAuth({
      clientId: String(id),
      dataPath: path.join(__dirname, 'session'),
    }),
    puppeteer: puppeteerOpts,
  });

  session.client = waClient;
  attachClientEvents(id, session, waClient);
  waClient.initialize().catch((err) => {
    Object.assign(session.state, defaultState());
    session.state.lastError = err.message || String(err);
    session.client = null;
    session.initializing = false;
  }).finally(() => {
    session.initializing = false;
  });
  return session;
}

app.get('/api/connections', (_req, res) => {
  const connections = [];
  for (const [id, session] of sessions.entries()) {
    connections.push(serializeSession(id, session));
  }
  res.json({ ok: true, connections });
});

app.get('/api/connections/:id/status', (req, res) => {
  try {
    const session = getSession(req.params.id);
    res.json({ ok: true, ...serializeSession(req.params.id, session) });
  } catch (err) {
    res.status(400).json({ ok: false, error: err.message || String(err) });
  }
});

app.post('/api/connections/:id/connect', async (req, res) => {
  try {
    const session = await ensureClient(req.params.id);
    res.json({ ok: true, ...serializeSession(req.params.id, session) });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

app.post('/api/connections/:id/disconnect', async (req, res) => {
  const id = req.params.id;
  const session = getSession(id);
  try {
    if (session.client) {
      await session.client.logout();
      await session.client.destroy();
    }
  } catch (err) {
    session.state.lastError = err.message || String(err);
  } finally {
    session.client = null;
    session.initializing = false;
    Object.assign(session.state, defaultState());
  }
  res.json({ ok: true, ...serializeSession(id, session) });
});

app.post('/api/send', async (req, res) => {
  try {
    const connectionId = req.body && req.body.connection_id;
    const phone = req.body && req.body.phone;
    const message = req.body && req.body.message;
    if (!connectionId) {
      return res.status(400).json({ ok: false, error: 'connection_id gerekli.' });
    }
    const session = getSession(connectionId);
    if (!session.client || session.state.status !== 'ready') {
      return res.status(409).json({ ok: false, error: 'WhatsApp bağlı değil. Önce QR kodu taratın.' });
    }
    if (!phone || !message) {
      return res.status(400).json({ ok: false, error: 'Telefon ve mesaj gerekli.' });
    }
    const chatId = chatIdFromPhone(phone);
    const result = await session.client.sendMessage(chatId, String(message));
    res.json({
      ok: true,
      messageId: result.id && result.id._serialized ? result.id._serialized : null,
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

/* Geriye dönük uyumluluk — tek oturum "default" */
app.get('/api/status', (_req, res) => {
  const session = getSession('default');
  res.json({ ok: true, ...serializeSession('default', session) });
});

app.post('/api/connect', async (_req, res) => {
  try {
    const session = await ensureClient('default');
    res.json({ ok: true, status: session.state.status });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

app.post('/api/disconnect', async (_req, res) => {
  const session = getSession('default');
  try {
    if (session.client) {
      await session.client.logout();
      await session.client.destroy();
    }
  } catch (err) {
    session.state.lastError = err.message || String(err);
  } finally {
    session.client = null;
    session.initializing = false;
    Object.assign(session.state, defaultState());
  }
  res.json({ ok: true, status: session.state.status });
});

app.listen(PORT, BIND_HOST, () => {
  console.log(`WhatsApp bridge listening on http://${BIND_HOST}:${PORT}`);
  restorePersistedSessions().catch((err) => {
    console.error('Oturum geri yükleme hatası:', err.message || err);
  });
});
