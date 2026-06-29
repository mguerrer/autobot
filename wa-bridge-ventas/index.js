const express = require('express');
const path = require('path');
const fs = require('fs');
const { makeWASocket, useMultiFileAuthState, DisconnectReason, Browsers } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const pino = require('pino');

process.on('uncaughtException', (err) => console.error('Uncaught:', err.message));
process.on('unhandledRejection', (err) => console.error('Unhandled:', err?.message || err));

const PORT = process.env.PORT || 9091;
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:8000/webhook/baileys';
const NEGOCIOS_PATH = process.env.NEGOCIOS_PATH || path.join(__dirname, '..', 'datos', 'negocios_ventas.json');
const SESSIONS_DIR = path.join(__dirname, 'sessions');
const API_KEY = process.env.BRIDGE_API_KEY || '';

const logger = pino({ level: 'silent' });
const app = express();
app.use(express.json());

if (API_KEY) {
  app.use((req, res, next) => {
    if (req.headers['x-api-key'] !== API_KEY) {
      return res.status(401).json({ error: 'API key requerida' });
    }
    next();
  });
}

const sessions = new Map();
const pausedSessions = new Set();

function normalizarNumero(num) {
  return num.replace(/[^0-9]/g, '');
}

function obtenerNumerosActivos() {
  try {
    if (!fs.existsSync(NEGOCIOS_PATH)) return [];
    const data = fs.readFileSync(NEGOCIOS_PATH, 'utf-8');
    const negocios = JSON.parse(data);
    const numeros = [...new Set(
      negocios
        .filter(n => n.activo && n.bot_whatsapp)
        .map(n => normalizarNumero(n.bot_whatsapp))
    )];
    return numeros.filter(Boolean);
  } catch (e) {
    console.error('Error leyendo negocios_ventas.json:', e.message);
    return [];
  }
}

function syncSessions() {
  const activos = new Set(obtenerNumerosActivos());
  for (const [num, ses] of sessions) {
    if (!activos.has(num)) {
      console.log(`Cerrando sesión ventas para ${num}`);
      ses.sock?.end(new Error('Eliminado de negocios.json'));
      fs.rmSync(path.join(SESSIONS_DIR, num), { recursive: true, force: true });
      sessions.delete(num);
    }
  }
}

async function iniciarSesion(numero) {
  if (sessions.has(numero)) return;
  const sessionDir = path.join(SESSIONS_DIR, numero);
  fs.mkdirSync(sessionDir, { recursive: true });
  const { state, saveCreds } = await useMultiFileAuthState(sessionDir);
  const sock = makeWASocket({
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: Browsers.macOS('Chrome'),
    syncFullHistory: false,
    markOnlineOnConnect: false,
    generateHighQualityLinkPreview: false,
  });
  const session = { sock, state: 'connecting', qr: null, jid: null, numero };
  sessions.set(numero, session);
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      session.qr = qr;
      session.state = 'awaiting_qr';
      console.log(`QR generado para ${numero}`);
    }
    if (connection === 'open') {
      session.state = 'connected';
      session.jid = sock.user?.id || null;
      session.qr = null;
      console.log(`Conectado ${numero}`);
    }
    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const errMsg = lastDisconnect?.error?.message || '';
      const errData = lastDisconnect?.error?.data;
      console.log(`Desconectado ${numero} (código: ${statusCode}) mensaje: ${errMsg}`);
      if (errData) console.log(`  data:`, JSON.stringify(errData).slice(0, 200));
      session.state = 'disconnected';
      session.jid = null;
      session.qr = null;
      sessions.delete(numero);
      if (statusCode === DisconnectReason.loggedOut || statusCode === DisconnectReason.restartRequired) {
        fs.rmSync(sessionDir, { recursive: true, force: true });
        console.log(`Auth eliminada para ${numero}`);
      }
      // No auto-reconnect — usuario debe presionar Iniciar
    }
  });
  sock.ev.on('creds.update', saveCreds);
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (msg.key?.fromMe) continue;
      if (!msg.message?.conversation && !msg.message?.extendedTextMessage?.text) continue;
      const from = msg.key.remoteJid?.replace('@s.whatsapp.net', '') || '';
      const text = msg.message.conversation || msg.message.extendedTextMessage.text || '';
      if (!from || !text) continue;
      console.log(`📩 ${numero} <- ${from}: ${text.slice(0, 80)}`);
      try {
        await fetch(WEBHOOK_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bot_whatsapp: `+${numero}`,
            from_number: from,
            message: text,
            message_id: msg.key?.id || '',
          }),
        });
      } catch (err) {
        console.error(`Webhook error: ${err.message}`);
      }
    }
  });
}

const STATUS_MAP = {
  connected: 'Conectado',
  awaiting_qr: 'Esperando QR',
  connecting: 'Conectando...',
  disconnected: 'Desconectado',
};

app.get('/status', (req, res) => {
  const activos = obtenerNumerosActivos();
  const lista = [];
  const vistos = new Set();
  for (const [num, ses] of sessions) {
    vistos.add(num);
    lista.push({
      numero: `+${num}`,
      state: ses.state,
      label: STATUS_MAP[ses.state] || ses.state,
      connected: ses.state === 'connected',
      jid: ses.jid,
      hasQR: !!ses.qr,
    });
  }
  for (const num of activos) {
    if (!vistos.has(num)) {
      lista.push({
        numero: `+${num}`,
        state: 'stopped',
        label: 'Detenido',
        connected: false,
        jid: null,
        hasQR: false,
      });
    }
  }
  res.json({ sessions: lista, total: lista.length });
});

app.get('/qr/:numero', async (req, res) => {
  const num = normalizarNumero(req.params.numero);
  const ses = sessions.get(num);
  if (!ses || !ses.qr) {
    return res.json({ qr: null, state: ses?.state || 'not_found', message: 'No QR disponible' });
  }
  try {
    const dataUrl = await QRCode.toDataURL(ses.qr, { width: 300, margin: 2 });
    res.json({ qr: dataUrl, state: ses.state, numero: `+${num}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send', async (req, res) => {
  const { to, message, bot_whatsapp } = req.body;
  if (!to || !message) return res.status(400).json({ error: 'to y message requeridos' });
  const num = normalizarNumero(bot_whatsapp || '');
  const ses = num ? sessions.get(num) : null;
  if (!ses || ses.state !== 'connected') {
    if (!num) return res.status(400).json({ error: 'bot_whatsapp requerido' });
    return res.status(503).json({ error: `${num} no conectado`, state: ses?.state || 'not_found' });
  }
  try {
    const jid = to.includes('@s.whatsapp.net') ? to : `${to}@s.whatsapp.net`;
    await ses.sock.sendMessage(jid, { text: message });
    res.json({ success: true, to: jid, via: `+${num}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/session/:numero/start', async (req, res) => {
  const num = normalizarNumero(req.params.numero);
  pausedSessions.delete(num);
  if (sessions.has(num)) {
    return res.json({ success: true, message: `${num} ya está activo` });
  }
  console.log(`Iniciando sesión ventas para ${num}`);
  await iniciarSesion(num);
  res.json({ success: true, message: `Iniciando sesión para ${num}` });
});

app.post('/session/:numero/stop', (req, res) => {
  const num = normalizarNumero(req.params.numero);
  const ses = sessions.get(num);
  if (ses) {
    pausedSessions.add(num);
    ses.sock?.end(new Error('Detenido por admin'));
    fs.rmSync(path.join(SESSIONS_DIR, num), { recursive: true, force: true });
    sessions.delete(num);
    console.log(`Detenido ${num} por admin`);
  }
  res.json({ success: true, message: `${num} detenido` });
});

app.post('/session/:numero/restart', async (req, res) => {
  const num = normalizarNumero(req.params.numero);
  const ses = sessions.get(num);
  if (ses) {
    pausedSessions.delete(num);
    ses.sock?.end(new Error('Reiniciado por admin'));
    fs.rmSync(path.join(SESSIONS_DIR, num), { recursive: true, force: true });
    sessions.delete(num);
  }
  console.log(`Reiniciando sesión ventas para ${num}`);
  await iniciarSesion(num);
  res.json({ success: true, message: `Reiniciando ${num}` });
});

// Cleanup stale sessions every 5 minutes (no auto-start)
setInterval(syncSessions, 300000);

app.listen(PORT, () => {
  console.log(`Bridge Ventas en puerto ${PORT}`);
  console.log(`Webhook: ${WEBHOOK_URL}`);
  console.log(`Negocios: ${NEGOCIOS_PATH}`);
});
