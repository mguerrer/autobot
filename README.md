# autobot

Plataforma multi-tenant de chatbots para WhatsApp con inteligencia artificial vía Ollama.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), SQLite (aiosqlite)
- **AI**: Ollama (gemma3:1b)
- **Admin UI**: Jinja2, Bootstrap 5, Bootstrap Icons
- **WhatsApp**: Meta Cloud API (con fallback mock para desarrollo)
- **Tests**: pytest + httpx

## Funcionalidades

- Multi-tenant: múltiples negocios, cada uno con su propio número WhatsApp
- Reglas por negocio vía archivos Markdown
- Rubros configurables
- Historial de conversaciones por contacto
- Panel admin: Dashboard, lista de negocios, detalle, edición, chats
- API REST para consultar negocios, conversaciones y mensajes
- Webhook para recibir mensajes de WhatsApp
- Provider abstracto: intercambiable entre Mock y Meta Cloud API

## Requisitos

```bash
python 3.12+
ollama (con modelo: gemma3:1b)
ngrok (para webhook público)
```

## Instalación

```bash
git clone https://github.com/mguerrer/autobot.git
cd autobot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuración

### Variables de entorno (`.env`)

```ini
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
DATABASE_URL=sqlite+aiosqlite:///./datos/autobot.db
WHATSAPP_PROVIDER=mock
WHATSAPP_API_TOKEN=
WHATSAPP_API_VERSION=v22.0
```

### Datos del negocio

| Archivo | Descripción |
|---|---|
| `datos/negocios.json` | Lista de negocios: RUT, nombre, rubro, dueño, WhatsApp, verify_token, activo |
| `datos/rubros.json` | Catálogo de rubros (Restaurante, Panadería, Tecnología, etc.) |
| `datos/reglas_generales.md` | Reglas que aplican a todos los negocios (tono, políticas generales) |
| `datos/reglas_negocio.md` | Reglas por negocio (precios, horarios, promociones, FAQ) |

Secciones en `reglas_negocio.md` se separan por `## negocio: {RUT}`.

Puedes editar negocios desde el panel admin (`/admin/negocios/{rut}/editar`) o directamente en JSON.

## Ejecución

```bash
ollama run gemma3:1b    # asegúrate que Ollama esté corriendo
uvicorn app.main:app --port 8000
```

Abrir `http://localhost:8000/admin/` en el navegador.

## WhatsApp Integration

### Mock Provider (por defecto)

Sin configuración adicional. Los mensajes se reciben vía API/webhook y las respuestas se simulan en consola. Ideal para desarrollo.

### Meta Cloud API (producción)

Gratis hasta 1.000 conversaciones al mes.

#### 1. Crear app en Meta Developers

1. Ir a [developers.facebook.com](https://developers.facebook.com)
2. **Crear App** → tipo **Business**
3. Agregar producto **WhatsApp**
4. En **API Setup** encontrarás:
   - **Phone Number ID**: ID numérico del número de WhatsApp
   - **Token de acceso**: temporal (24h) o permanente desde Business Settings
5. Si no tienes un número real, Meta asigna uno de prueba gratis

#### 2. Exponer webhook con ngrok

```bash
ngrok http 8000
```

Esto genera una URL pública como `https://xxxx.ngrok-free.app`.

#### 3. Configurar Webhook en Meta

En la sección **Webhook** de tu app de Meta:

- **Callback URL**: `https://TU_SUBDOMINIO.ngrok-free.app/webhook/meta`
- **Verify Token**: el `verify_token` del negocio (ej: `pulento_token_456`)
- Suscribirse a eventos: `messages`

#### 4. Configurar credenciales en autobot

En el panel admin, editar el negocio y pegar el **Phone Number ID** en el campo correspondiente.

Luego en `.env`:

```ini
WHATSAPP_API_TOKEN=EAAl...tu_token...
WHATSAPP_PROVIDER=meta
```

Cuando `WHATSAPP_API_TOKEN` tiene valor, el sistema usa automáticamente `MetaWhatsAppProvider`. Si está vacío, usa `MockWhatsAppProvider`.

#### Endpoints del webhook

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/webhook/meta` | Recibe mensajes desde Meta Cloud API (formato nativo) |
| `GET` | `/webhook/meta` | Verificación del webhook (`hub.challenge`) |
| `POST` | `/webhook/whatsapp` | Endpoint simplificado para pruebas |
| `GET` | `/webhook/whatsapp` | Verificación (mismo handler) |

## API REST

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/negocios` | Listar todos los negocios |
| `GET` | `/api/conversaciones` | Listar conversaciones (filtro: `?negocio_rut=...`) |
| `GET` | `/api/conversaciones/{id}/mensajes` | Mensajes de una conversación |

## Pruebas

```bash
pytest tests/ -q
```

44 tests unitarios (rule_engine, api, admin, webhook, models).

## Estructura del proyecto

```
app/
  main.py              # Entry point FastAPI
  config.py            # Settings desde .env
  database.py          # SQLAlchemy async engine + session
  models.py            # Modelos: Contacto, Conversacion, Mensaje
  schemas.py           # Pydantic schemas
  routers/
    admin.py           # Panel admin (Jinja2)
    api.py             # API REST
    webhook.py         # Webhook WhatsApp (Meta + simplificado)
  services/
    ollama_service.py  # Cliente async Ollama
    whatsapp_service.py# Providers: Mock + Meta Cloud API
    rule_engine.py     # Carga reglas, negocio, rubros
  templates/           # Jinja2 templates
    base.html
    index.html
    negocios.html
    negocio_detail.html
    negocio_edit.html
    chats.html
  static/
    style.css
datos/
  negocios.json
  rubros.json
  reglas_generales.md
  reglas_negocio.md
tests/
  test_api.py
  test_models.py
  test_rule_engine.py
  test_webhook.py
specs/                 # BDD Gherkin features
```

## Licencia

MIT
