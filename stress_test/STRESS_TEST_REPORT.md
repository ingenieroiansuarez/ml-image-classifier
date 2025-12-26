# Reporte de Pruebas de Estrés - Proyecto ML Image Classifier

## Introducción
Este reporte compara el rendimiento del sistema de clasificación de imágenes con diferentes configuraciones de escalado del servicio de Machine Learning.

## Configuración de las Pruebas
- **Herramienta**: Locust 2.42.6
- **Usuarios simultáneos**: 10
- **Spawn rate**: 2 usuarios/segundo
- **Duración**: 30 segundos
- **Host**: http://localhost:8000

## Endpoints Probados
1. **GET /docs** - Documentación de la API (peso: 1)
2. **POST /model/predict** - Predicción de imágenes (peso: 3)

## Resultados

### Escenario 1: 1 Instancia del Servicio ML

| Métrica | GET /docs | POST /model/predict | Total |
|---------|-----------|---------------------|-------|
| Requests totales | 19 | 72 | 91 |
| Failures | 0 (0%) | 0 (0%) | 0 (0%) |
| Avg response time | 16ms | 158ms | 128ms |
| Min response time | 3ms | 104ms | 3ms |
| Max response time | 81ms | 625ms | 625ms |
| Median response time | 8ms | 120ms | 110ms |
| Requests/sec | 0.66 | 2.51 | **3.17** |
| 95th percentile | 82ms | 290ms | 280ms |
| 99th percentile | 82ms | 630ms | 630ms |

### Escenario 2: 3 Instancias del Servicio ML

| Métrica | GET /docs | POST /model/predict | Total |
|---------|-----------|---------------------|-------|
| Requests totales | 18 | 76 | 94 |
| Failures | 0 (0%) | 0 (0%) | 0 (0%) |
| Avg response time | 38ms | 148ms | 127ms |
| Min response time | 1ms | 105ms | 1ms |
| Max response time | 438ms | 746ms | 746ms |
| Median response time | 6ms | 120ms | 120ms |
| Requests/sec | 0.62 | 2.60 | **3.22** |
| 95th percentile | 440ms | 230ms | 230ms |
| 99th percentile | 440ms | 750ms | 750ms |

## Análisis Comparativo

### Throughput (Requests por segundo)
- **1 instancia**: 3.17 req/s
- **3 instancias**: 3.22 req/s
- **Mejora**: +1.6%

### Tiempo de Respuesta Promedio
- **1 instancia**: 128ms
- **3 instancias**: 127ms
- **Mejora**: -0.8% (ligeramente más rápido)

### Tiempo de Respuesta del Endpoint /model/predict
- **1 instancia**: 158ms promedio, 290ms (p95)
- **3 instancias**: 148ms promedio, 230ms (p95)
- **Mejora**: -6.3% en promedio, -20.7% en p95

### Estabilidad
- Ambos escenarios completaron todas las requests sin fallos (0% failure rate)
- Ambos escenarios mantienen tiempos de respuesta consistentes

## Observaciones

1. **Mejora Moderada**: Con solo 10 usuarios concurrentes durante 30 segundos, la carga no es lo suficientemente alta para observar diferencias dramáticas. El sistema con 1 instancia ya maneja bien esta carga.

2. **Reducción de Latencia en Percentiles Altos**: La mejora más notable está en el percentil 95 del endpoint de predicción (290ms → 230ms), lo que indica mejor distribución de carga en escenarios de alta concurrencia.

3. **Sin Cuellos de Botella**: El hecho de que no haya fallos indica que Redis está manejando correctamente la cola de trabajos y los workers están procesando las predicciones eficientemente.

4. **Tiempo de Respuesta Máximo**: El tiempo máximo aumentó con 3 instancias (625ms → 746ms), probablemente debido al overhead inicial de carga del modelo en las instancias nuevas al inicio del test.

## Conclusiones

1. **Escalabilidad Horizontal Funcional**: El sistema escala correctamente agregando más instancias del servicio ML. La arquitectura basada en Redis permite distribuir la carga entre múltiples workers.

2. **Mejora en Percentiles Altos**: Aunque la mejora promedio es pequeña, los percentiles altos (p95) muestran una reducción significativa del 20.7%, lo que beneficia a los usuarios en escenarios de alta carga.

3. **Recomendación para Producción**: Para cargas superiores a 10 usuarios concurrentes, se recomienda usar al menos 2-3 instancias del servicio ML para garantizar tiempos de respuesta consistentes.

4. **Test de Carga Limitado**: Para obtener resultados más concluyentes, se recomienda realizar pruebas con:
   - Mayor cantidad de usuarios (50-100)
   - Mayor duración (5-10 minutos)
   - Diferentes patterns de carga (picos, rampa, steady-state)

## Archivos Generados
- `report_1_instance.html` - Reporte detallado con 1 instancia
- `report_3_instances.html` - Reporte detallado con 3 instancias

---

**Fecha**: 26 de Diciembre de 2025  
**Autor**: Sistema de Testing Automático  
**Proyecto**: Image Classifier ML - Master's Degree Assignment
