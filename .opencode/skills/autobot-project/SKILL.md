# Autobot - Project Context

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 async, SQLite (aiosqlite)
- **AI**: Ollama (gemma3:1b)
- **Templates**: Jinja2 + Bootstrap 5.3 dark
- **WA Bridge**: Node.js, Express, @whiskeysockets/baileys (multi-sesión, sin Puppeteer)
- **Run**: `uvicorn app.main:app --port 8000` (Python) + `node wa-bridge/index.js` (Node)

## Estructura
```
app/
  main.py          # FastAPI app factory, lifespan
  config.py        # Pydantic Settings from .env
  database.py      # SQLAlchemy async engine + session
  models.py        # Contacto, Conversacion, Mensaje
  schemas.py       # Pydantic schemas (WebhookIn, MensajeOut, etc.)
  routers/
    admin.py       # Panel: dashboard, negocios CRUD, chats, WA Bridge
    api.py         # REST: /api/negocios, /api/conversaciones, /api/conversaciones/{id}/mensajes
    webhook.py     # POST /webhook/whatsapp, /webhook/meta, /webhook/baileys
  services/
    whatsapp_service.py  # procesar_mensaje_entrante, providers (Mock/Meta/Baileys)
    ollama_service.py    # generar_respuesta() -> Ollama
    rule_engine.py       # cargar_negocios(), construir_prompt_sistema()
  templates/       # Jinja2 templates
  static/          # style.css
wa-bridge/
  index.js         # Baileys multi-session (v3). Lee negocios.json, auto-sync cada 30s.
  package.json     # express, @whiskeysockets/baileys, qrcode, pino
  run.sh           # Auto-restart loop
datos/
  negocios.json    # Array de negocios {rut, nombre, rubro_id, bot_whatsapp, activo, ...}
  rubros.json      # 11 rubros
  reglas_generales.md, reglas_negocio.md  # Prompts del bot
```

## Cambios recientes
- **Baileys multi-sesión**: wa-bridge ahora con @whiskeysockets/baileys (sin Chrome/Puppeteer). Cada bot_whatsapp activo en negocios.json genera una sesión independiente. Sincroniza cada 30s.
- **Detalle conversación**: GET /admin/chats/{id} con UI tipo chat. Scroll automático.
- **Responder desde admin**: POST /admin/chats/{id}/responder. Envía via provider y guarda en DB.
- **WA Bridge panel**: Muestra estado + QR por cada número.
- **Baileys provider**: Envía bot_whatsapp al bridge para routing.

## Endpoints clave
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /admin/ | Dashboard |
| GET | /admin/chats | Lista conversaciones |
| GET | /admin/chats/{id} | Detalle conversación + mensajes |
| POST | /admin/chats/{id}/responder | Enviar respuesta como bot |
| GET | /admin/wa-bridge | Estado multi-sesión del bridge |
| POST | /webhook/baileys | Webhook que recibe msgs del bridge |
| GET | /api/conversaciones | API conversaciones (filtro ?negocio_rut=, ?estado=) |
| GET | /api/conversaciones/{id}/mensajes | API mensajes de conversación |

## WA Bridge API (puerto 9090)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /status | Estado de todas las sesiones |
| GET | /qr/{numero} | QR data URL para escanear |
| POST | /send | Enviar mensaje {to, message, bot_whatsapp} |

## .env
```
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
DATABASE_URL=sqlite+aiosqlite:///./datos/autobot.db
WHATSAPP_PROVIDER=mock
WHATSAPP_API_TOKEN=
WA_BRIDGE_URL=http://localhost:9090
WA_BOT_WHATSAPP=
```

## Configuración WhatsApp
1. Iniciar bridge: `cd wa-bridge && node index.js`
2. Iniciar server: `uvicorn app.main:app --port 8000`
3. Abrir http://localhost:8000/admin/wa-bridge
4. Escanear QR de cada número con WhatsApp > Dispositivos vinculados

## Reglas del repositorio
- **No instalar software** dentro del repositorio: no `npm install`, `pip install`, `pipenv install`, `poetry install`, `bun install`, `yarn add`, etc. Esto incluye `node_modules/`, `.venv/`, `venv/` y similares.
- **No crear archivos temporales** en el repositorio: cachés de compilación, logs, `.pytest_cache/`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `.coverage`, `htmlcov/`.
- **No trackear archivos de entorno**: `.env`, `.env.local`, `.env.*.local` contienen credenciales y no deben committearse.
- **No trackear la base de datos**: `*.db`, `*.sqlite`, `*.sqlite3` son datos locales de desarrollo.
- **No trackear sessions de WA Bridge**: `wa-bridge/sessions/` contiene autenticación real de WhatsApp.
- Excepciones documentadas: `.env.example` si existe, o `.opencode/` (configuración del asistente).
- Si necesitas instalar dependencias o crear archivos temporales, usa `/tmp/opencode` o un directorio fuera del repo.

## Notas
- node_modules estaba trackeado en git (error histórico). Se agregó a .gitignore.
- La DB SQLite se crea automáticamente en datos/autobot.db al iniciar.
- Los negocios se configuran en datos/negocios.json. Activo=true genera sesión en bridge.
