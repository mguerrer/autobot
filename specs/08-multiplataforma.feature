@multi-platform @integration
Feature: Soporte Multi-Plataforma
  Como cliente de la plataforma
  Quiero conectar bots en diferentes plataformas de mensajería
  Para gestionar todas mis comunicaciones desde un solo lugar

  Background:
    Given un tenant autenticado con plan "Enterprise"

  Scenario: Agregar canal de Telegram
    Given el tenant en la sección de canales
    When agrega un bot de Telegram usando el token de BotFather
    Then el canal de Telegram se conecta
    And el bot puede recibir y enviar mensajes en Telegram
    And los contactos de Telegram se unifican con los de WhatsApp si el teléfono coincide

  Scenario: Enrutar mensaje según plataforma de origen
    Given un tenant con canales de WhatsApp y Telegram activos
    When un contacto escribe desde WhatsApp
    Then el sistema identifica la plataforma de origen
    And el mensaje se etiqueta con "whatsapp"
    And las reglas de automatización aplican según la plataforma

  Scenario: Vista unificada de conversaciones multi-platforma
    Given un contacto que ha interactuado por WhatsApp y Telegram
    When el tenant ve la conversación
    Then ve todos los mensajes en orden cronológico
    And cada mensaje indica su plataforma de origen con un ícono
    And puede responder desde cualquier plataforma

  Scenario: Configurar mensaje de bienvenida por plataforma
    Given el tenant configurando mensajes automáticos
    When configura:
      | plataforma | mensaje                           |
      | WhatsApp   | "Bienvenido a nuestro WhatsApp"   |
      | Telegram   | "Bienvenido a nuestro Telegram"   |
    Then cada plataforma usa su propio mensaje de bienvenida
    And cuando un nuevo contacto escribe desde WhatsApp, recibe el mensaje de WhatsApp

  Scenario: Desconectar plataforma
    Given un tenant con WhatsApp y Telegram conectados
    When desconecta el canal de Telegram
    Then el canal de Telegram se desactiva
    And los mensajes de Telegram dejan de recibirse
    But los contactos y datos históricos de Telegram se conservan

  @smoke
  Scenario: Estadísticas consolidadas multi-platforma
    Given un tenant con WhatsApp y Telegram activos
    When ve el dashboard de analytics
    Then puede ver métricas consolidadas de todas las plataformas
    And puede filtrar por plataforma individual
    And puede comparar rendimiento entre plataformas
