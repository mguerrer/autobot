# Autobot — WhatsApp Bot Platform

## Visión General

Plataforma multi-tenant para bots de WhatsApp con IA vía Ollama. Hecha con Python/FastAPI, SQLite (dev) y desplegada en Kubernetes local con KinD.

---

## 1. Funcionalidades Implementadas

### 1.1 Autenticación y Roles
- Login con usuario y contraseña (sesión vía cookie firmada HMAC, 24h TTL)
- Roles: **admin** y **cliente**
- Admin: acceso a Dashboard, Negocios, Chats (sin ver contenido de conversaciones — privacidad)
- Cliente: acceso solo a su negocio, incluyendo conversaciones completas
- Logout con eliminación de cookie de sesión
- Usuarios seed: `admin`, `cliente1`, `cliente2`, `cliente3`
- Clave secreta configurable via `SECRET_KEY` en `.env`

### 1.2 Panel Cliente (`/cliente/`)
- Dashboard con info del negocio (nombre, RUT, estado, número WhatsApp)
- Lista de conversaciones del negocio
- Vista detalle de conversación con mensajes
- Editar contexto de la IA (reglas de negocio en Markdown)
- Encender / Apagar el bot por negocio

### 1.3 Panel Admin (`/admin/`)
- Dashboard con cards de negocio y últimas conversaciones
- CRUD de negocios (listar, detalle, editar, toggle activo)
- **Editar reglas del bot por negocio** (editor Markdown con EasyMDE en página de editar negocio)
- Lista de chats (sin contenido para admin)
- Gestión de WA Bridge (solo clientes)
- Breadcrumbs de navegación

### 1.4 Multi-Tenancy
- Cada negocio tiene un RUT único como identificador
- Contactos, conversaciones y mensajes asociados por `negocio_rut`
- Clientes ven solo sus datos propios
- Admin ve todo (excepto contenido de conversaciones)

### 1.5 Canales de Mensajería (WhatsApp)
- **Mock**: log a consola (dev)
- **Meta Cloud API**: webhook con verificación de challenge
- **Baileys**: bridge Node.js multi-sesión (Express + @whiskeysockets/baileys)
- Webhooks: `POST /webhook/whatsapp`, `POST /webhook/meta`, `POST /webhook/baileys`
- Verificación: `GET /webhook/whatsapp` con `hub.mode`, `hub.verify_token`, `hub.challenge`

### 1.6 IA con Ollama
- Modelo configurable: `gemma3:1b`, `qwen2.5-coder:3b`, etc.
- Prompt system construido con reglas generales + reglas por negocio + rubro
- Contexto de negocio editable desde panel cliente y desde panel admin (editar negocio)
- Reglas persistentes en base de datos (tablas `ReglaGeneral` y `ReglaNegocio`)

### 1.7 Base de Datos
- SQLite vía SQLAlchemy async + aiosqlite
- Modelos: `Usuario`, `Contacto`, `Conversacion`, `Mensaje`, `ReglaGeneral`, `ReglaNegocio`
- Reglas de negocio persistentes en DB (no en archivos planos), compartidas entre réplicas K8s
- Migración automática de reglas desde archivos a DB al iniciar (solo si tabla vacía)
- Seed automático de usuarios por defecto

### 1.8 Pruebas Automatizadas
- Framework: pytest + pytest-asyncio
- 43 tests: rule engine (18), API endpoints (18), modelos (6), webhook (9)
- Fixtures: engine in-memory SQLite, session factory, datos dir con monkeypatch
- Clientes autenticados: `admin_client`, `cliente_client` (cookie de sesión HMAC)
- Tests de reglas de negocio: carga desde DB, guardado, edición desde admin y cliente

### 1.9 Despliegue Local (K8s)
- Dockerfiles para API (Python) y WA Bridge (Node.js)
- Helm chart con deployments, services, ingress
- 2 réplicas por servicio con balanceo round-robin
- KinD cluster local con Traefik como ingress controller
- Túnel público serveo.net para acceso desde internet

---

## 2. Stack Tecnológico

| Capa            | Tecnología                          |
|-----------------|-------------------------------------|
| Lenguaje        | Python 3.12 + Node.js 20           |
| Framework API   | FastAPI                             |
| ORM             | SQLAlchemy async + aiosqlite        |
| Base de datos   | SQLite (dev), PostgreSQL (futuro)   |
| WA Bridge       | Express + @whiskeysockets/baileys   |
| IA              | Ollama (gemma3, qwen2.5-coder)      |
| Frontend        | Jinja2 templates + Bootstrap 5      |
| Contenedores    | Docker, multi-stage builds          |
| Orquestación    | Kubernetes (KinD), Helm charts      |
| Ingress         | Traefik                             |
| Autenticación   | Cookies firmadas HMAC               |

---

## 3. Usuarios por Defecto

| Usuario   | Password    | Rol     | Negocio              |
|-----------|-------------|---------|----------------------|
| admin     | admin123    | admin   | —                    |
| cliente1  | cliente123  | cliente | Pizzería Napoli      |
| cliente2  | cliente123  | cliente | TechSupport Ltda.    |
| cliente3  | cliente123  | cliente | Panadería El Pulento |

---

## 4. Endpoints

| Ruta                        | Método | Auth     | Descripción                        |
|-----------------------------|--------|----------|------------------------------------|
| `/admin/login`              | GET    | —        | Página de login                    |
| `/admin/login`              | POST   | —        | Autenticación                      |
| `/admin/logout`             | GET    | —        | Cerrar sesión                      |
| `/admin/`                   | GET    | sí       | Dashboard                          |
| `/admin/negocios`           | GET    | sí       | Lista de negocios                  |
| `/admin/negocios/{rut}`     | GET    | sí       | Detalle de negocio                 |
| `/admin/negocios/{rut}/editar` | GET/POST | sí | Editar negocio (incluye reglas del bot con EasyMDE) |
| `/admin/negocios/{rut}/toggle` | POST | sí     | Activar/desactivar                 |
| `/admin/chats`              | GET    | sí       | Lista de conversaciones            |
| `/admin/chats/{id}`         | GET    | sí       | Detalle conversación (oculto admin)|
| `/admin/chats/{id}/responder` | POST | sí (no admin) | Responder como bot           |
| `/admin/wa-bridge`          | GET    | sí       | Estado WA Bridge                   |
| `/cliente/`                 | GET    | sí       | Dashboard cliente                  |
| `/cliente/conversaciones`   | GET    | sí       | Conversaciones del cliente         |
| `/cliente/conversaciones/{id}` | GET | sí      | Detalle conversación               |
| `/cliente/configuracion`    | GET    | sí       | Configuración del bot              |
| `/cliente/configuracion/reglas` | POST | sí    | Guardar contexto IA                |
| `/cliente/configuracion/toggle` | POST | sí    | Encender/apagar bot                |
| `/webhook/whatsapp`         | GET    | —        | Verificación Meta                  |
| `/webhook/whatsapp`         | POST   | —        | Webhook genérico                   |
| `/webhook/meta`             | GET    | —        | Verificación Meta                  |
| `/webhook/meta`             | POST   | —        | Webhook Meta Cloud API             |
| `/webhook/baileys`          | POST   | —        | Webhook WA Bridge                  |
| `/api/negocios`             | GET    | —        | API REST negocios                  |
| `/api/conversaciones`       | GET    | —        | API REST conversaciones            |
| `/api/conversaciones/{id}/mensajes` | GET | —    | API REST mensajes                  |
| `/`                         | GET    | —        | Redirige a `/admin/login`          |

---

## 5. Pendientes / Futuro

- PostgreSQL como base de datos principal
- Redis para caché y colas
- Bull/BullMQ para procesamiento asíncrono de mensajes
- Templates de mensajes WhatsApp aprobados
- Rate limiting por IP/usuario
- JWT con refresh tokens
- Audit log de acciones administrativas
- CI/CD pipeline
- Multi-stage Docker builds optimizados
- Endpoint `/health` con chequeo de dependencias
- Monitoreo con Prometheus + Grafana
