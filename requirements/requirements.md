# WhatsApp Bot Platform — Requirements

## Visión General

Plataforma SaaS multi-tenant para bots de WhatsApp, alojada en Kubernetes, capaz de atender 50+ clientes en paralelo chateando simultáneamente. Cada cliente (tenant) administra su propio bot con números de teléfono WhatsApp Business independientes.

---

## 1. Requisitos Funcionales

### 1.1 Multi-Tenancy
- RF-01: Cada tenant debe tener un `tenant_id` único que segregue todos sus datos.
- RF-02: Un tenant no puede acceder a datos de otro tenant.
- RF-03: Cada tenant puede tener uno o más bots (números de WhatsApp).
- RF-04: Cada bot tiene su propio token de acceso a WhatsApp Business API.

### 1.2 Canales de Mensajería (WhatsApp Business API)
- RF-05: Soportar múltiples BSPs: Meta Cloud API, 360dialog, Twilio, WATI.
- RF-06: Endpoint `GET /webhook/whatsapp` con verificación de challenge (`hub.mode`, `hub.verify_token`, `hub.challenge`).
- RF-07: Procesar mensajes entrantes de texto, imágenes, documentos, audio, video, ubicación, contactos, botones, listas e interactivos.
- RF-08: Manejar `statuses` en webhooks: sent, delivered, read, failed.
- RF-09: Validar firma `X-Hub-Signature-256` en cada webhook entrante.
- RF-10: Responder 200 OK inmediatamente en webhooks; procesamiento en background.
- RF-11: Idempotencia basada en `MessageID` de WhatsApp.

### 1.3 Manejo de Mensajes
- RF-12: Mensajes entrantes se encolan para procesamiento asíncrono (Bull/BullMQ + Redis).
- RF-13: Cada conversación tiene una máquina de estados finitos.
- RF-14: Almacenar historial reciente de conversación en Redis con TTL.
- RF-15: Persistir conversaciones en base de datos cuando sea necesario.
- RF-16: Cola priorizada de mensajes salientes: notificaciones > respuestas automáticas > campañas.
- RF-17: Sistema de reintentos con exponential backoff + jitter.
- RF-18: Dead Letter Queue para mensajes que fallan definitivamente.

### 1.4 Templates de Mensajes
- RF-19: Gestionar ciclo de vida de templates: draft → submitted → approved → rejected → paused.
- RF-20: Soportar categorías MARKETING, UTILITY, AUTHENTICATION.
- RF-21: Parámetros dinámicos `{{1}}`, `{{2}}` en templates.
- RF-22: Soportar header con imagen, body con texto, footer y botones (call-to-action, quick reply).
- RF-23: Fallback a idioma por defecto si no hay traducción disponible.

### 1.5 Media Handling
- RF-24: Descargar media de WhatsApp inmediatamente al recibir webhook (la media expira).
- RF-25: Subir media a S3/GCS y almacenar URL firmada.
- RF-26: Validar tipo MIME y tamaño máximo (WhatsApp: 16MB video, 5MB imagen).
- RF-27: Cachear media procesada (miniaturas, previews).

### 1.6 Contactos y Usuarios
- RF-28: Registrar consentimiento explícito (opt-in) con timestamp y fuente.
- RF-29: Estados de contacto: created → opted_in → opted_out → blocked.
- RF-30: Segmentar contactos por etiquetas y atributos personalizados.
- RF-31: Soportar envío a grupos de WhatsApp (cuando el BSP lo permita).

### 1.7 Monitoreo
- RF-32: Endpoint `GET /health` con checks de DB, Redis y servicios externos.
- RF-33: Dashboard Grafana con métricas por tenant y globales.
- RF-34: Logs estructurados con retención de 30 días (Loki + Grafana / Elasticsearch + Kibana).
- RF-35: Alertas: webhook caído >5min, tasa de fallo >10%, cola acumulándose.

---

## 2. Requisitos No Funcionales

### 2.1 Escalabilidad y Concurrencia
- NFR-01: Soportar **50 clientes en paralelo** chateando simultáneamente.
- NFR-02: Procesamiento asíncrono mediante colas (Bull/BullMQ + Redis).
- NFR-03: Los webhooks deben responder en <500ms (responder OK, procesar después).
- NFR-04: La plataforma debe escalar horizontalmente en Kubernetes.

### 2.2 Despliegue y Operaciones
- NFR-05: Alojado en Kubernetes. Manifiestos Helm o Kustomize.
- NFR-06: Cloud agnostic. Configuración vía variables de entorno.
- NFR-07: CI/CD pipeline: lint → type check → tests → build → deploy.
- NFR-08: Entornos: development → staging → production.
- NFR-09: Multi-stage Docker builds para imágenes ligeras.

### 2.3 Base de Datos
- NFR-10: PostgreSQL como base de datos principal (Prisma o Drizzle ORM).
- NFR-11: Redis para caché, colas y sesiones.
- NFR-12: Tabla `messages` particionada por fecha.
- NFR-13: Soft delete (`deleted_at`) en todas las tablas.
- NFR-14: Índices en (tenant_id, phone) en contacts; (tenant_id, status, created_at) en messages.

### 2.4 Seguridad
- NFR-15: JWT con refresh tokens para autenticación. Access tokens TTL 15min.
- NFR-16: Rate limiting por IP, usuario y endpoint (Redis backend).
- NFR-17: Helmet para headers de seguridad.
- NFR-18: CORS restringido a dominios conocidos.
- NFR-19: Validación de entrada con Zod.
- NFR-20: Tokens de WhatsApp únicos por bot.
- NFR-21: Audit log de acciones administrativas.

### 2.5 Compliance
- NFR-22: Derecho al olvido (GDPR/LGPD). Exportar y borrar datos de contacto.
- NFR-23: No almacenar más datos de los necesarios (términos de Meta).
- NFR-24: Respetar política anti-spam de Meta. No enviar fuera de horario permitido.

---

## 3. Stack Tecnológico Propuesto

| Capa            | Tecnología                                                                 |
|-----------------|----------------------------------------------------------------------------|
| Lenguaje        | TypeScript (Node.js)                                                       |
| Framework API   | Express + middleware modular, o NestJS                                     |
| ORM             | Prisma o Drizzle                                                            |
| Base de datos   | PostgreSQL + Redis                                                         |
| Colas           | Bull/BullMQ                                                                |
| Frontend        | Next.js (React) con TypeScript, Tailwind CSS, React Query                  |
| Contenedores    | Docker, multi-stage builds                                                 |
| Orquestación    | Kubernetes (Helm / Kustomize)                                              |
| Monitoreo       | Prometheus + Grafana, Loki para logs                                       |
| Errores         | Sentry                                                                     |
| Testing         | Vitest + Testing Library, Playwright para e2e                              |
| NLP opcional    | LLM local (Ollama) o Dialogflow para entender intención                    |
