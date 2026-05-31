@onboarding @critical
Feature: Onboarding de Tenant
  Como proveedor de la plataforma de bots
  Quiero que los clientes puedan registrarse y configurar su cuenta
  Para que puedan empezar a usar el servicio

  Background:
    Given que el sistema está operativo
    And se dispone de un plan gratuito y planes pagos

  @regression
  Scenario: Registro exitoso con email y contraseña
    Given un visitante con email "cliente@email.com" y contraseña válida
    When completa el formulario de registro
    Then se crea su cuenta con estado "pending_verification"
    And se envía un email de verificación
    And recibe un token de API temporal

  Scenario: Registro con email ya existente
    Given un usuario registrado con email "existente@email.com"
    When un visitante intenta registrarse con el mismo email
    Then recibe un error "EMAIL_ALREADY_EXISTS"
    And el nuevo registro no se crea

  Scenario: Verificación de email exitosa
    Given un tenant con estado "pending_verification"
    When hace clic en el enlace de verificación
    Then su estado cambia a "active"
    And puede iniciar sesión

  Scenario: Registro con onboarding de WhatsApp
    Given un tenant recién registrado
    When completa el onboarding guiado
    Then se le solicita conectar un número de WhatsApp
    And se le muestra el wizard de configuración inicial
    And se crea un bot por defecto con nombre "Mi Bot"

  @smoke
  Scenario: Selección de plan durante el registro
    Given un visitante en la página de planes
    When selecciona el plan "Pro" y completa el pago
    Then su cuenta se actualiza al plan "Pro"
    And se habilitan las features: templates ilimitados, 5 números, analytics avanzados
