@contacts @gdpr
Feature: Gestión de Contactos
  Como cliente de la plataforma
  Quiero gestionar mis contactos de WhatsApp
  Para segmentar y comunicarme efectivamente con ellos

  Background:
    Given un tenant autenticado con un bot conectado

  @smoke
  Scenario: Importar contactos desde archivo CSV
    Given el tenant en la sección de contactos
    When importa un archivo CSV con 100 contactos
      | teléfono     | nombre | apellido |
      | 521551234... | Juan   | Pérez    |
    Then los contactos se importan con estado "pending_opt_in"
    And se muestra un resumen: 100 importados, 0 duplicados, 0 inválidos

  Scenario: Contacto duplicado en importación
    Given un contacto existente con teléfono "5215512345678"
    When se importa un CSV que incluye ese mismo teléfono
    Then el contacto existente se actualiza con los nuevos datos
    And se reporta como "actualizado" en el resumen

  Scenario: Enviar invitación de opt-in
    Given un contacto con estado "pending_opt_in"
    When el tenant envía una invitación de opt-in
    Then se envía un template de confirmación al contacto
    And si el contacto responde "Sí", cambia a "active"
    And si el contacto no responde en 48h, se marca como "expired"

  Scenario: Etiquetar contactos
    Given 3 contactos activos en el sistema
    When el tenant selecciona 2 contactos y les asigna la etiqueta "vip"
    Then los contactos quedan etiquetados como "vip"
    And puede filtrar contactos por esa etiqueta

  @smoke
  Scenario: Buscar contacto por teléfono
    Given un contacto con teléfono "5215512345678"
    When el tenant busca "5512345678"
    Then el contacto aparece en los resultados
    And muestra nombre, etiquetas, última interacción

  Scenario: Ver conversación de un contacto
    Given un contacto con historial de mensajes
    When el tenant hace clic en el contacto
    Then ve el historial completo de mensajes
    And puede ver el estado de cada mensaje (sent/delivered/read)
    And puede responder desde la misma vista

  Scenario: Exportar contactos
    Given 50 contactos activos con etiquetas
    When el tenant exporta los contactos
    Then descarga un archivo CSV con todos los contactos y sus datos
    And el CSV incluye: teléfono, nombre, etiquetas, estado, última interacción

  @gdpr
  Scenario: Solicitar borrado de datos (GDPR)
    Given un contacto activo
    When el contacto solicita el borrado de sus datos
    Then el contacto se marca como "deleted"
    And sus datos personales seanonimizan
    But el historial de mensajes se conserva anonimizado por auditoría

  Scenario: Bloquear contacto
    Given un contacto activo
    When el tenant bloquea al contacto
    Then el contacto cambia a estado "blocked"
    And no puede recibir más mensajes del bot
    And los mensajes entrantes de ese contacto se ignoran

  Scenario: Segmentar contactos por atributos
    Given contactos con diferentes etiquetas y atributos
    When el tenant crea un segmento: etiqueta "vip" Y ciudad "CDMX"
    Then ve solo los contactos que cumplen ambas condiciones
    And puede enviar mensajes a todo el segmento
