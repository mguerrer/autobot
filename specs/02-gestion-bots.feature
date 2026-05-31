@bots @core
Feature: Gestión de Bots
  Como cliente de la plataforma
  Quiero crear y configurar bots de WhatsApp
  Para tener presencia automatizada en diferentes números

  Background:
    Given un tenant autenticado con plan activo
    And el tenant tiene al menos un slot de bot disponible

  @smoke
  Scenario: Crear un nuevo bot
    Given el tenant en el panel de gestión de bots
    When crea un bot con:
      | nombre     | "Bot Ventas"           |
      | plataforma | WhatsApp               |
      | proveedor  | Meta Cloud API         |
    Then el bot se crea con estado "disconnected"
    And se genera un verify_token único
    And se le asigna un webhook_url único

  Scenario: Conectar número de WhatsApp
    Given un bot con estado "disconnected"
    When el tenant escanea el código QR de WhatsApp
    Then el bot cambia a estado "connecting"
    And cuando la conexión se establece
    Then el bot cambia a estado "connected"
    And el webhook comienza a recibir eventos

  Scenario: Configurar webhook del bot
    Given un bot conectado
    When el tenant configura la URL del webhook personalizado
    And verifica el token de verificación
    Then el sistema valida el webhook con un challenge
    And si la validación es exitosa, el webhook queda "active"

  Scenario: Pausar un bot
    Given un bot con estado "connected"
    When el tenant pausa el bot
    Then el bot cambia a estado "paused"
    And no se procesan mensajes entrantes
    And los mensajes salientes se encolan

  Scenario: Reactivar un bot pausado
    Given un bot con estado "paused"
    When el tenant reactiva el bot
    Then el bot cambia a estado "connected"
    And los mensajes encolados comienzan a enviarse

  Scenario: Eliminar un bot
    Given un bot con estado "connected"
    When el tenant elimina el bot
    Then se confirma la eliminación con una advertencia
    And el bot se marca como "deleted"
    And el webhook se desactiva
    And los templates asociados se archivan

  @error-handling
  Scenario: Límite de bots alcanzado
    Given un tenant con plan "Básico" (máx 2 bots)
    And ya tiene 2 bots activos
    When intenta crear un tercer bot
    Then recibe un error "BOT_LIMIT_REACHED"
    And se le ofrece actualizar su plan

  Scenario: Desconexión inesperada del bot
    Given un bot conectado
    When ocurre una desconexión inesperada
    Then el bot cambia a estado "disconnected"
    And se envía una notificación al tenant
    And se registra el evento en el audit log
