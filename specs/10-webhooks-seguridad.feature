@webhooks @security @critical
Feature: Webhooks y Seguridad
  Como operador de la plataforma
  Quiero garantizar la seguridad e integridad de los webhooks
  Para proteger los datos de los clientes y cumplir con los requisitos de Meta

  Background:
    Given el sistema de webhooks está operativo
    And hay un bot conectado con webhook configurado

  @smoke
  Scenario: Verificación de webhook (challenge)
    Given Meta envía una solicitud GET a /webhook/whatsapp
      | parámetro      | valor          |
      | hub.mode       | subscribe      |
      | hub.verify_token| mi_token_123  |
      | hub.challenge  | 1234567890     |
    When el sistema valida el verify_token contra el almacenado
    Then responde con status 200 y body igual al challenge
    And la verificación es exitosa

  Scenario: Rechazo de webhook con token inválido
    Given Meta envía una solicitud GET a /webhook/whatsapp
      | hub.verify_token | token_invalido |
    When el sistema valida el token
    Then responde con status 403
    And se registra el intento fallido en el audit log
    And se envía una alerta de seguridad al tenant

  Scenario: Recepción de mensaje con firma válida
    Given Meta envía un POST a /webhook/whatsapp
    And el header X-Hub-Signature-256 contiene la firma correcta
    When el sistema verifica la firma usando el App Secret
    Then el payload se acepta y procesa
    And se responde con 200 OK

  Scenario: Rechazo de payload con firma inválida
    Given un atacante envía un POST falso a /webhook/whatsapp
    When el sistema verifica la firma y no coincide
    Then responde con status 401
    And el payload se descarta
    And se registra el incidente de seguridad

  @smoke
  Scenario: Idempotencia en procesamiento de webhooks
    Given el sistema recibe un webhook con MessageID "msg_123"
    When el webhook se procesa exitosamente
    And Meta reenvía el mismo webhook (por retry)
    Then el sistema detecta que msg_123 ya fue procesado
    And responde 200 OK sin reprocesar
    And se registra como duplicado en el log

  Scenario: Timeout y procesamiento asíncrono
    Given el sistema recibe un webhook entrante
    When el payload es grande o complejo
    Then el sistema responde 200 OK inmediatamente (< 2 segundos)
    And encola el procesamiento en un job asíncrono
    And el mensaje se procesa en background

  Scenario: Rotación de verify_token
    Given un bot con verify_token actual
    When el tenant rota el token
    Then el nuevo token se guarda inmediatamente
    And el token anterior se mantiene como válido por 24 horas (ventana de migración)
    And después de 24 horas, el token anterior expira

  Scenario: Logueo de payloads de webhook
    Given un webhook recibido y procesado
    When el payload se registra en webhook_logs
    Then los datos sensibles (números de teléfono, mensajes) se enmascaran
    And el log incluye: timestamp, bot_id, tipo de evento, status_code
    And los logs se retienen por 30 días
