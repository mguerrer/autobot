---
name: web-app-dev
description: Mejores prácticas para desarrollo de aplicaciones web modernas
---

# Web Application Development Best Practices

## Arquitectura

- **SPA con SSR híbrido**: Usa Next.js (React) o Nuxt (Vue) para combinar renderizado del lado del servidor con interactividad del lado del cliente.
- **Separación de capas**: API Gateway → Servicios → Repositorios → Base de datos.
- **Arquitectura modular**: Organiza el código por funcionalidades (features), no por tipo (controllers, models, etc.).
- **Versionado de API**: Usa prefijos `/api/v1/`, `/api/v2/`.

## Seguridad (OWASP Top 10)

- **XSS**: Escapa todo output. Usar CSP headers. No usar `dangerouslySetInnerHTML` / `v-html`.
- **CSRF**: Tokens CSRF en mutaciones. `SameSite=Strict` o `SameSite=Lax` en cookies.
- **SQL Injection**: Siempre usar ORM/query builder parametrizado. Nunca concatenar SQL.
- **Autenticación**: JWT con refresh tokens. TTL corto para access tokens (15min). Almacenar refresh tokens en httpOnly cookies.
- **Rate Limiting**: Por IP, por usuario, por endpoint. Usar Redis como backend.
- **Helmet**: Usar helmet (Node) o similar para headers de seguridad.
- **Validación**: Validar entrada en frontend y backend. Usar librerías tipo Zod, Yup, Joi.
- **CORS**: Restringir a dominios conocidos. No usar `Access-Control-Allow-Origin: *` en producción.

## API Design (REST)

- **Métodos HTTP semánticos**: GET (leer), POST (crear), PUT (reemplazar), PATCH (actualizar parcial), DELETE (borrar).
- **Códigos HTTP**: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error.
- **Paginación**: `GET /items?page=1&limit=20` → Response: `{ data: [...], meta: { total, page, limit, totalPages } }`.
- **Filtros y búsqueda**: Query params `?status=active&search=term`.
- **Errores consistentes**: `{ error: { code: "VALIDATION_ERROR", message: "...", details: [...] } }`.

## Frontend

- **TypeScript estricto**: `strict: true` en tsconfig. Evitar `any`.
- **Componentes atómicos**: Atomic Design (átomos → moléculas → organismos → templates → páginas).
- **State management**: Para estado global usar Zustand, Jotai o Redux Toolkit. Estado de servidor con React Query / SWR / TanStack Query.
- **Lazy loading**: `React.lazy()` + `Suspense` para rutas y componentes pesados.
- **Accesibilidad (a11y)**: Roles ARIA, contraste suficiente, navegación por teclado, labels en inputs.
- **Responsive**: Mobile-first con Tailwind o CSS Modules. Breakpoints consistentes.
- **Testing**: Vitest + Testing Library para unit/integration. Playwright o Cypress para e2e.

## Backend

- **Node.js**: Express + middleware modular, o NestJS para apps más estructuradas.
- **Base de datos**: PostgreSQL (relacional) + Redis (cache/colas). Prisma o Drizzle como ORM.
- **Logging**: Logger estructurado (Pino, Winston). Niveles: debug, info, warn, error, fatal.
- **Manejo de errores**: Middleware global de errores. No exponer stack traces en producción.
- **Background jobs**: Bull/BullMQ con Redis para tareas asíncronas (envíos, notificaciones).
- **Health checks**: Endpoint `GET /health` con checks de DB, Redis, servicios externos.

## Pruebas

- **Pirámide de testing**: Muchos unitarios (70%), algunos de integración (20%), pocos e2e (10%).
- **Unitarias**: Jest/Vitest. Mockear dependencias externas.
- **Integración**: Testear API con supertest + base de datos de prueba.
- **E2E**: Playwright o Cypress. Flujos críticos completos.
- **BDD**: Gherkin + Cucumber / Jest-cucumber para features complejas.

## CI/CD

- **Pipeline**: Lint → Type Check → Unit Tests → Integration Tests → Build → Deploy.
- **Git Flow**: `main` (producción) + `develop` (desarrollo) + `feature/*` (features) + `fix/*` (bugs).
- **Entornos**: development → staging → production. Variables de entorno por entorno.
- **Docker**: Multi-stage builds para mantener imágenes ligeras.

## Performance

- **Caching**: Redis para caché de respuestas. CDN para assets estáticos.
- **Compresión**: gzip/brotli en respuestas HTTP.
- **Base de datos**: Índices en columnas de búsqueda. N+1 queries: usar eager loading.
- **Frontend**: Code splitting, tree shaking, lazy loading de imágenes.
- **Monitorización**: Prometheus + Grafana para métricas. Sentry para errores.
