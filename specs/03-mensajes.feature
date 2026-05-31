@messaging @core
Feature: Envío y Recepción de Mensajes
  Como cliente de la plataforma
  Quiero enviar y recibir mensajes de WhatsApp
  Para comunicarme con mis contactos

  Background:
    Given un tenant autenticado con un bot conectado
    And el bot tiene al menos un contacto activo

  @smoke
  Scenario: Enviar mensaje de texto
    Given el tenant en la interfaz de conversaciones
    When selecciona un contacto y envía "Hola, ¿cómo estás?"
    Then el mensaje se encola para envío
    And el mensaje aparece como "pending" en la conversación
    When el proveedor confirma la entrega
    Then el mensaje cambia a "sent"
    And cuando llega el delivery receipt, cambia a "delivered"
    And cuando el contacto lee el mensaje, cambia a "read"

  @smoke
  Scenario: Recibir mensaje entrante vía webhook
    Given un webhook activo para el bot
    When un contacto envía "Hola" desde WhatsApp
    Then el sistema recibe el webhook con MessageID único
    And valida la firma del webhook
    And procesa el mensaje asíncronamente
    And el mensaje aparece en la conversación del contacto
    And se dispara la automatización correspondiente

  Scenario: Enviar mensaje con imagen
    Given un contacto activo
    When el tenant envía una imagen (JPEG, < 5MB)
    Then el sistema sube la imagen a S3/GCS
    And envía el media message a través de la API de WhatsApp
    And el contacto recibe la imagen

  Scenario: Enviar mensaje con botones
    Given un contacto activo
    When el tenant envía un mensaje interactivo con botones
      | body    | "¿Desea confirmar su cita?" |
      | button1 | "Sí, confirmar"              |
      | button2 | "Reagendar"                  |
    Then el contacto ve los botones en WhatsApp
    And cuando el contacto presiona "Sí, confirmar"
    Then el webhook recibe el interaction event
    And se ejecuta la acción configurada

  Scenario: Enviar mensaje usando template
    Given un template aprobado "bienvenida" con parámetros
    When el tenant envía el template al contacto
    Then se reemplazan los parámetros {{1}} con el nombre del contacto
    And se envía como template message
    And el mensaje se entrega correctamente

  @error-handling
  Scenario: Envío a contacto sin opt-in
    Given un contacto con estado "opted_out"
    When el tenant intenta enviar un mensaje
    Then el sistema rechaza el envío con "CONTACT_OPTED_OUT"
    And se registra el intento en el log
    And se notifica al tenant

  Scenario: Rate limit excedido
    Given el bot enviando mensajes al máximo permitido
    When se excede el rate limit de WhatsApp (250 msg/s)
    Then el sistema aplica backoff exponencial
    And los mensajes se reencolan con retry
    And se registra una alerta de rate limit

  Scenario: Mensaje fallido con retry
    Given un mensaje en cola para envío
    When el proveedor responde con error temporal (5xx)
    Then el sistema reintenta hasta 3 veces con backoff
    And si todos los reintentos fallan
    Then el mensaje pasa a estado "failed"
    And se mueve a la Dead Letter Queue
    And se notifica al tenant

  Scenario: Historial de mensajes con paginación
    Given una conversación con más de 50 mensajes
    When el tenant solicita los mensajes
    Then recibe los primeros 20 mensajes
    And el response incluye metadata de paginación
    And puede navegar a la página siguiente
