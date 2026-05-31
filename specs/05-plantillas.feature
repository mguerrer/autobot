@templates @messaging
Feature: Gestión de Plantillas de Mensajes
  Como cliente de la plataforma
  Quiero crear y gestionar plantillas de mensajes aprobadas por Meta
  Para enviar mensajes estructurados y reutilizables

  Background:
    Given un tenant autenticado con un bot conectado
    And el tenant tiene acceso al módulo de plantillas

  @smoke
  Scenario: Crear plantilla de tipo UTILITY
    Given el tenant en el editor de plantillas
    When crea una plantilla con:
      | nombre      | "confirmacion_pedido"     |
      | categoria   | UTILITY                   |
      | idioma      | es_MX                     |
      | body        | "Hola {{1}}, tu pedido {{2}} ha sido confirmado" |
    Then la plantilla se guarda con estado "draft"
    And se envía para aprobación a Meta
    And cuando Meta la aprueba, cambia a "approved"

  Scenario: Editar plantilla rechazada
    Given una plantilla con estado "rejected"
    And motivo de rechazo: "Incluye lenguaje promocional en categoria UTILITY"
    When el tenant edita el body y cambia la categoría a MARKETING
    Then la plantilla se reenvía para aprobación
    And el historial de versiones se conserva

  Scenario: Enviar plantilla con header de imagen
    Given una plantilla "promo_verano" aprobada con header de imagen
    When el tenant envía la plantilla a un contacto
    Then el mensaje incluye la imagen del header
    And el body con los parámetros reemplazados
    And el footer opcional

  Scenario: Plantilla con botones CTA
    Given una plantilla "visita_tienda" aprobada
    When la plantilla incluye un botón "Visitar sitio" con URL
    Then al enviarla, el contacto ve el botón
    And al hacer clic, se abre el navegador con la URL

  @error-handling
  Scenario: Rechazo por contenido no permitido
    Given un tenant creando una plantilla
    When el body contiene "¡GANA DINERO YA!" (lenguaje spam)
    Then el sistema detecta contenido sospechoso
    And advierte al tenant sobre posible rechazo
    And permite enviar igual pero con advertencia

  Scenario: Listar todas las plantillas con filtros
    Given 10 plantillas en diferentes estados
    When el tenant filtra por estado "approved"
    Then ve solo las plantillas aprobadas
    And puede ver el idioma, fecha de aprobación y última modificación

  Scenario: Eliminar plantilla
    Given una plantilla en estado "draft"
    When el tenant la elimina
    Then la plantilla se borra permanentemente
    But si la plantilla está "approved"
    Then solo se desactiva, no se elimina

  Scenario: Plantilla multi-idioma
    Given una plantilla "bienvenida" en español (es_MX)
    When el tenant crea una variante en inglés (en_US)
    Then ambas comparten el mismo nombre base
    And se envían según el idioma del contacto
