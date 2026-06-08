const express = require('express');
const path = require('path');
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');

process.on('uncaughtException', (err) => console.error('Uncaught:', err.message));
process.on('unhandledRejection', (err) => console.error('Unhandled:', err?.message || err));

const PORT = process.env.PORT || 9090;
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:8000/webhook/baileys';
const SESSIONS_DIR = path.join(__dirname, 'sessions');

let client = null;
let currentQR = null;
let connectionState = 'starting';
let connectedJid = null;

const app = express();
app.use(express.json());

function startClient() {
  client = new Client({
    authStrategy: new LocalAuth({ dataPath: SESSIONS_DIR }),
    puppeteer: {
      executablePath: '/usr/bin/google-chrome',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    },
  });

  client.on('qr', async (qr) => {
    currentQR = qr;
    connectionState = 'awaiting_qr';
    console.log('📱 QR generado - escanea con WhatsApp');
  });

  client.on('ready', () => {
    connectionState = 'connected';
    connectedJid = client.info.wid.user;
    currentQR = null;
    console.log(`✅ Conectado como ${connectedJid}`);
  });

  client.on('disconnected', (reason) => {
    connectionState = 'disconnected';
    connectedJid = null;
    console.log(`❌ Desconectado: ${reason}. Reconectando en 10s...`);
    setTimeout(startClient, 10000);
  });

  client.on('message', async (msg) => {
    if (msg.fromMe) return;
    const from = msg.from.replace('@c.us', '');
    const text = msg.body || '';
    if (!text) return;

    console.log(`📩 ${from}: ${text}`);

    try {
      await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_number: from,
          message: text,
          message_id: msg.id._serialized || '',
          bot_whatsapp: process.env.BOT_WHATSAPP || '',
        }),
      });
    } catch (err) {
      console.error(`⚠️ Webhook error: ${err.message}`);
    }
  });

  client.initialize().catch((err) => {
    console.error('Error inicializando cliente:', err.message);
    connectionState = 'error';
    setTimeout(startClient, 15000);
  });
}

app.get('/status', (req, res) => {
  res.json({
    state: connectionState,
    connected: connectionState === 'connected',
    jid: connectedJid,
    hasQR: !!currentQR,
  });
});

app.get('/qr', async (req, res) => {
  if (!currentQR) {
    return res.json({ qr: null, state: connectionState, message: 'No QR disponible' });
  }
  try {
    const dataUrl = await QRCode.toDataURL(currentQR, { width: 300, margin: 2 });
    res.json({ qr: dataUrl, state: connectionState });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/send', async (req, res) => {
  const { to, message } = req.body;
  if (!to || !message) return res.status(400).json({ error: 'to y message requeridos' });
  if (!client || connectionState !== 'connected') {
    return res.status(503).json({ error: 'WhatsApp no conectado', state: connectionState });
  }
  try {
    const jid = to.includes('@c.us') ? to : `${to}@c.us`;
    await client.sendMessage(jid, message);
    res.json({ success: true, to: jid });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

startClient();

app.listen(PORT, () => {
  console.log(`🚀 WA Bridge v2 en puerto ${PORT}`);
  console.log(`📡 Webhook: ${WEBHOOK_URL}`);
});
