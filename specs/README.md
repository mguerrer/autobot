# Especificaciones BDD — Autobot

Este directorio contiene los escenarios BDD en formato Gherkin para la plataforma de bots de WhatsApp.

## Convenciones

- **Idioma**: Español (funcionalidades orientadas a negocio)
- **Tags**: Usamos tags para categorizar y filtrar escenarios:
  - `@smoke` — Smoke tests (flujos críticos)
  - `@regression` — Tests de regresión
  - `@critical` — Funcionalidades críticas
  - `@error-handling` — Casos de error
  - Tags funcionales: `@onboarding`, `@bots`, `@messaging`, `@contacts`, `@templates`, `@automation`, `@analytics`, `@multi-platform`, `@billing`, `@webhooks`, `@security`

## Features

| Archivo | Descripción |
|---------|-------------|
| `01-onboarding.feature` | Registro, verificación y selección de plan |
| `02-gestion-bots.feature` | CRUD de bots, conexión WhatsApp, webhooks |
| `03-mensajes.feature` | Envío/recepción de mensajes, media, interactivos |
| `04-contactos.feature` | Importación, segmentación, opt-in, GDPR |
| `05-plantillas.feature` | Templates, aprobación Meta, multi-idioma |
| `06-automatizaciones.feature` | Reglas de negocio, flujos conversacionales |
| `07-analytics.feature` | Dashboard, reportes, exportación |
| `08-multiplataforma.feature` | Soporte Telegram, vista unificada |
| `09-facturacion.feature` | Suscripciones, pagos, facturas |
| `10-webhooks-seguridad.feature` | Webhook verification, firmas, idempotencia |

## Ejecución

```bash
# Todos los tests
npx cucumber-js specs/

# Solo smoke tests
npx cucumber-js specs/ --tags "@smoke"

# Solo una feature específica
npx cucumber-js specs/03-mensajes.feature
```
