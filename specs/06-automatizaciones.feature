@automation @rules
Feature: Automatizaciones y Reglas de Negocio
  Como cliente de la plataforma
  Quiero configurar reglas automáticas para responder mensajes
  Para atender a mis contactos sin intervención manual

  Background:
    Given un tenant autenticado con un bot conectado
    And el bot tiene contactos activos

  @smoke
  Scenario: Crear regla de respuesta automática por palabra clave
    Given el tenant en el panel de automatizaciones
    When crea una regla:
      | condición      | mensaje contiene "horario"         |
      | acción         | enviar mensaje "Nuestro horario es..." |
      | prioridad      | 10                                |
    Then la regla se guarda con estado "active"
    And cuando un contacto envía "¿cuál es su horario?"
    Then el bot responde automáticamente con el mensaje configurado

  Scenario: Regla con múltiples condiciones
    Given una regla con condiciones:
      | campo      | operador | valor     |
      | mensaje    | contains | "precio"  |
      | etiqueta   | equals   | vip       |
    When un contacto con etiqueta "vip" pregunta por un precio
    Then se ejecuta la regla y responde con info de precios VIP
    But si el contacto no tiene etiqueta "vip"
    Then la regla no se ejecuta

  Scenario: Regla por horario laboral
    Given una regla configurada solo para horario laboral (9:00-18:00)
    When un contacto envía un mensaje a las 20:00
    Then se activa la respuesta de "fuera de horario"
    And el mensaje se marca para seguimiento al día siguiente

  Scenario: Derivar a agente humano
    Given una regla con acción "derivar a humano"
    When un contacto escribe "hablar con agente"
    Then el bot responde "Un agente te atenderá en breve"
    And se crea un ticket en el panel de atención
    And la conversación se asigna al siguiente agente disponible

  Scenario: Prioridad entre reglas
    Given dos reglas que coinciden con "hola":
      | prioridad | respuesta          |
      | 5         | "Hola, ¿en qué..." |
      | 10        | "¡Bienvenido!"     |
    When un contacto envía "hola"
    Then se ejecuta la regla con prioridad 10 (mayor número)
    And el bot responde "¡Bienvenido!"

  @smoke
  Scenario: Flujo conversacional con múltiples pasos
    Given un flujo configurado:
      | paso | pregunta                 | opciones                      |
      | 1    | "¿Qué deseas hacer?"     | "comprar", "reclamar", "info" |
      | 2    | "Selecciona producto"    | "producto A", "producto B"    |
    When un contacto inicia la conversación
    Then se envía el paso 1 con botones
    When selecciona "comprar"
    Then se envía el paso 2
    And se registra la intención del contacto

  Scenario: Límite de reglas por plan
    Given un tenant con plan "Básico" (máx 5 reglas)
    And ya tiene 5 reglas activas
    When intenta crear una sexta regla
    Then recibe un error "RULE_LIMIT_REACHED"
    And se le sugiere actualizar su plan

  Scenario: Desactivar regla temporalmente
    Given una regla activa
    When el tenant la desactiva
    Then la regla cambia a estado "inactive"
    And no se ejecuta aunque las condiciones coincidan
