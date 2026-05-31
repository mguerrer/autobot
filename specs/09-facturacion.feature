@billing @subscription
Feature: Facturación y Suscripciones
  Como cliente de la plataforma
  Quiero gestionar mi suscripción y métodos de pago
  Para mantener el servicio activo

  Background:
    Given un tenant autenticado

  Scenario: Suscribirse a plan Pro
    Given un tenant con plan "Gratuito"
    When selecciona el plan "Pro" ($29/mes)
    And completa el pago con tarjeta de crédito
    Then su plan se actualiza a "Pro"
    And la fecha de facturación se establece al día del mes actual
    And recibe un comprobante por email

  Scenario: Cambiar de plan (upgrade)
    Given un tenant con plan "Básico" ($19/mes)
    When hace upgrade a "Pro" ($29/mes)
    Then se prorratea el costo del período restante
    And las features del plan Pro se habilitan inmediatamente
    And el próximo cobro será por la diferencia prorrateada

  Scenario: Cambiar de plan (downgrade)
    Given un tenant con plan "Enterprise" ($99/mes)
    When hace downgrade a "Pro" ($29/mes)
    Then el cambio se aplica al final del período de facturación actual
    And las features de Enterprise se mantienen hasta esa fecha
    And se confirma la pérdida de features al tenant

  Scenario: Facturación con múltiples métodos de pago
    Given un tenant en configuración de pago
    When agrega una tarjeta de respaldo
    Then el sistema tiene dos métodos: principal y respaldo
    And si el método principal falla, se intenta con el respaldo

  Scenario: Pago fallido
    Given un tenant con pago programado
    When el pago falla (tarjeta rechazada)
    Then el sistema reintenta hasta 3 veces en 5 días
    And se notifica al tenant después del primer fallo
    And si todos los reintentos fallan, el plan pasa a "suspended"
    And los bots se pausan automáticamente

  Scenario: Reactivar cuenta suspendida
    Given un tenant con estado "suspended" por falta de pago
    When actualiza su método de pago y paga el adeudo
    Then su plan se restablece a "active"
    And los bots se reconectan automáticamente
    And los mensajes encolados durante la suspensión se procesan

  Scenario: Ver historial de facturas
    Given un tenant con 6 meses de suscripción
    When accede a "Historial de facturas"
    Then ve una lista con todas las facturas de los últimos 6 meses
    And puede descargar cada factura en PDF
    And cada factura incluye desglose de impuestos

  Scenario: Cancelar suscripción
    Given un tenant con plan "Pro"
    When cancela la suscripción
    Then se confirma la cancelación
    And el servicio continúa hasta el final del período pagado
    And al finalizar, el plan pasa a "Gratuito"
    And los bots se limitan a las features del plan gratuito
