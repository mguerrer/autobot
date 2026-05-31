---
name: whatsapp-bot-platform
description: Mejores prácticas para plataforma SaaS de bots de WhatsApp multi-tenant
---

# WhatsApp Bot Platform Best Practices

## Arquitectura General

- **Multi-tenant aislado**: Cada tenant (cliente) con su propio `tenant_id`. Datos segregados por tenant en todas las tablas.
- **Cloud agnostic**: Diseñar para Kubernetes. Usar variables de entorno para config.
- **Microservicios o modular monolith**: Empezar con monolith modular. Dividir en servicios solo cuando sea necesario (webhooks, messaging, billing).
- **Webhook Gateway**: Punto de entrada único para webhooks de WhatsApp. Encola mensajes para procesamiento asíncrono.

## WhatsApp Business API

- **Proveedores**: Soportar múltiples BSPs (Business Solution Providers): Meta Cloud API, 360dialog, Twilio, WATI, etc.
- **Webhook verification**: Endpoint `GET /webhook/whatsapp` con challenge verification (`hub.mode`, `hub.verify_token`, `hub.challenge`).
- **Webhook payload**: Procesar mensajes de texto, imágenes, documentos, audio, video, ubicación, contactos, botones, listas, interactivos.
- **Message status**: Manejar `statuses` en webhooks (sent, delivered, read, failed).
- **Rate limits**: Respetar los rate limits de WhatsApp:
  - Business API: 250 msg/s por número (puede variar).
  - Template messages: límites según calidad del template.
- **Retry con backoff**: Exponential backoff + jitter para reintentos. Cola de mensajes fallidos con DLQ (Dead Letter Queue).

## Manejo de Mensajes

- **Message queue**: Bull/BullMQ + Redis. Cada mensaje entrante → job en cola → worker procesa.
- **State machine**: Cada conversación tiene un estado. Usar máquina de estados finitos (XState o similar).
- **Contexto de conversación**: Almacenar historial reciente en Redis (TTL). Persistir en DB cuando sea necesario.
- **Intención y entidades**: NLP ligero (o integración con Dialogflow / LLM) para entender intención del usuario.
- **Mensajes salientes**: Cola priorizada: notificaciones > respuestas automáticas > campañas.

## Webhooks (Best Practices)

- **Idempotencia**: Usar `MessageID` de WhatsApp como clave idempotente. No procesar el mismo mensaje dos veces.
- **Verificación de firma**: Validar firma `X-Hub-Signature-256` en cada webhook entrante.
- **Timeout rápido**: Responder 200 OK inmediatamente. Procesamiento en background.
- **Reintentos**: Meta reintenta hasta 3 veces con backoff. Manejar duplicados con idempotencia.
- **Logging**: Loggear payloads entrantes (sin datos sensibles) para debugging.

## Templates de Mensajes

- **Pre-aprobación**: Los templates de mensaje requieren aprobación de Meta. Gestionar ciclo de vida: draft → submitted → approved → rejected → paused.
- **Categorías**: MARKETING, UTILITY, AUTHENTICATION. Cada una con diferentes reglas.
- **Parámetros dinámicos**: Usar `{{1}}`, `{{2}}` para variables. Validar cantidad de parámetros antes de enviar.
- **Header/Footer/Body**: Soportar header con imagen, body con texto, footer, botones (call-to-action, quick reply).
- **Fallback**: Template en varios idiomas. Fallback a inglés si no hay traducción.

## Media Handling

- **Upload**: Subir media desde WhatsApp → descargar temporalmente → subir a S3/GCS → almacenar URL firmada.
- **Validación**: Verificar tipo MIME, tamaño máximo (WhatsApp: 16MB para video, 5MB para imagen).
- **Expiración**: Media de WhatsApp expira. Descargar inmediatamente al recibir webhook.
- **Cache**: Cachear media procesada (miniaturas, previews).

## Contactos y Grupos

- **Opt-in**: Registrar consentimiento explícito del usuario antes de enviar mensajes. Timestamp + fuente.
- **Estado contacto**: created → opted_in → opted_out → blocked.
- **Listas de difusión**: Segmentar contactos por etiquetas, atributos personalizados.
- **Grupos**: Soportar envío a grupos de WhatsApp (si el BSP lo permite). Manejar participantes.

## Base de Datos

- **Tablas principales**: `tenants`, `users`, `bots`, `contacts`, `conversations`, `messages`, `templates`, `webhook_logs`, `media`.
- **Particionamiento**: Tabla `messages` particionada por fecha. `conversations` por tenant.
- **Índices**: (tenant_id, phone) en contacts. (tenant_id, status, created_at) en messages.
- **Soft delete**: En todas las tablas con `deleted_at`. No borrar datos de conversaciones.

## Monitoreo y Alertas

- **Métricas clave**: Tasa de entrega, tiempo de respuesta, tasa de fallo, mensajes/segundo, contactos activos.
- **Alertas**: Webhook caído >5min, tasa de fallo >10%, cola de mensajes acumulándose.
- **Dashboard**: Grafana con paneles por tenant y global.
- **Logs**: Elasticsearch + Kibana / Loki + Grafana. Retención: 30 días.

## Seguridad Específica

- **Tokens por bot**: Cada bot tiene su propio access token para la API de WhatsApp.
- **Webhook secrets**: `verify_token` único por bot. Rotación periódica.
- **Sanitización**: Sanitizar mensajes entrantes (inyección, XSS en respuestas).
- **Data isolation**: Un tenant no puede acceder a datos de otro. Verificar en cada query.
- **Audit log**: Loggear acciones administrativas (creación de bot, cambio de template, etc.).

## Compliance

- **GDPR/LGPD**: Derecho al olvido (borrar datos de contacto). Exportar datos de usuario.
- **Términos de Meta**: No almacenar más datos de los necesarios. No compartir datos con terceros sin consentimiento.
- **Mensajes salientes**: No enviar mensajes fuera del horario permitido (salvo transaccionales). Respetar política anti-spam.
