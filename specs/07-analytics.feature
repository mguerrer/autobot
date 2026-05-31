@analytics @dashboard
Feature: Analytics y Dashboard
  Como cliente de la plataforma
  Quiero ver métricas y estadísticas de mis bots
  Para medir el rendimiento y tomar decisiones

  Background:
    Given un tenant autenticado con un bot conectado
    And el bot tiene actividad en los últimos 30 días

  @smoke
  Scenario: Ver dashboard resumen
    Given el tenant en el dashboard principal
    Then ve las métricas clave:
      | métrica                    | periodo |
      | Total mensajes enviados    | hoy     |
      | Total mensajes recibidos   | hoy     |
      | Contactos activos          | hoy     |
      | Tasa de entrega            | hoy     |
      | Tasa de lectura            | hoy     |
    And puede ver la evolución en un gráfico de líneas de los últimos 7 días

  Scenario: Filtrar dashboard por período
    Given el dashboard con datos de los últimos 30 días
    When el tenant selecciona el período "Este mes"
    Then las métricas se actualizan para mostrar datos del mes actual
    And los gráficos se recalculan

  Scenario: Ver analytics por bot
    Given un tenant con 3 bots
    When selecciona un bot específico en el filtro
    Then las métricas se limitan a ese bot
    And puede comparar con el promedio de todos sus bots

  Scenario: Reporte de mensajes más exitosos
    Given múltiples templates enviados en el último mes
    When el tenant accede al reporte de templates
    Then ve una tabla con:
      | template              | enviados | entregados | leídos | tasa conversión |
    And puede ordenar por cualquier columna

  Scenario: Exportar reporte a CSV
    Given un reporte de analytics generado
    When el tenant hace clic en "Exportar CSV"
    Then descarga un archivo CSV con los datos del reporte actual
    And el archivo incluye encabezados y datos formateados

  Scenario: Ver conversaciones activas en tiempo real
    Given el dashboard de tiempo real
    When un contacto envía un mensaje
    Then la conversación aparece en la lista de "activas ahora"
    And se muestra el tiempo transcurrido desde el último mensaje

  Scenario: Mapa de calor por hora y día
    Given datos de mensajes de las últimas 4 semanas
    When el tenant ve el mapa de calor
    Then puede identificar los días y horas de mayor actividad
    And ajustar sus campañas según los picos de actividad
