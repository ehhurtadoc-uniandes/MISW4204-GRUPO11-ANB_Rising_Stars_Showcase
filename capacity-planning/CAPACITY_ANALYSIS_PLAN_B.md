# Plan de Análisis de Capacidad - Plan B

## Objetivo

Implementar el Plan B del análisis de capacidad según los requerimientos del documento de análisis de capacidad, enfocado en medir el rendimiento de la capa Worker (videos/min) a distintos niveles de paralelismo y tamaños de archivo.

## Estrategia de Implementación

### Bypass de la Web
- Inyectar directamente mensajes en la cola (script/productor) con payloads realistas
- Rutas a archivos en storage de pruebas
- Bypass completo de la capa web para medición pura del worker

### Diseño Experimental

#### Tamaños de Video
- **50 MB**: Videos pequeños (configuración base)
- **100 MB**: Videos medianos (carga intermedia)
- **200 MB**: Videos grandes (carga alta)

#### Concurrencia de Worker
- **1 proceso**: Configuración mínima
- **2 procesos**: Configuración balanceada
- **4 procesos**: Configuración alta

#### Combinaciones de Prueba
Para cada combinación de tamaño y concurrencia:
1. **Pruebas de saturación**: Subir cantidad de tareas progresivamente
2. **Pruebas sostenidas**: Mantener número fijo de archivos en cola

## Métricas y Cálculos

### Métricas Clave
- **Throughput observado**: X = videos procesados / minuto
- **Tiempo medio de servicio**: S = tiempo_proceso_promedio por video
- **Utilización de recursos**: CPU, memoria, I/O
- **Estabilidad de cola**: Tendencia ~0 durante prueba

### Criterios de Éxito/Fallo
- **Capacidad nominal**: (videos/min) documentada
- **Estabilidad**: Cola no crece sin control
- **Recursos**: CPU < 90%, Memory < 85%

## Herramientas Implementadas

### Scripts de Prueba
- **`worker_bypass.py`**: Bypass de la web para inyección directa
- **`simulated_worker.py`**: Worker simulado para procesamiento
- **`worker_saturation_test.py`**: Pruebas de saturación
- **`worker_sustained_test.py`**: Pruebas sostenidas
- **`plan_b_executor.py`**: Ejecutor completo del Plan B

### Monitoreo
- **`psutil`**: Métricas del sistema (CPU, memoria, I/O)
- **Redis**: Cola de mensajes y monitoreo
- **Logging**: Trazabilidad completa de jobs

## Resultados Esperados

### Tabla de Capacidad
| Tamaño | Workers | Throughput | Estabilidad | Bottlenecks |
|--------|---------|------------|-------------|-------------|
| 50MB   | 1       | 30.0/min   | Estable     | CPU         |
| 50MB   | 2       | 45.8/min   | Estable     | CPU         |
| 50MB   | 4       | 60.2/min   | Estable     | CPU         |
| 100MB  | 1       | 15.5/min   | Estable     | CPU         |
| 100MB  | 2       | 28.3/min   | Estable     | CPU         |
| 100MB  | 4       | 45.1/min   | Estable     | CPU         |

### Puntos de Saturación
- **CPU**: 90% utilización
- **Memoria**: 85% utilización
- **I/O**: 80% utilización

## Ejecución

### Demo Rápido (2 minutos)
```bash
python capacity-planning/run_plan_b_demo.py
```

### Análisis Completo (10-15 minutos)
```bash
python capacity-planning/plan_b_executor.py
```

### Pruebas Específicas
```bash
# Saturación
python capacity-planning/worker_saturation_test.py --test-type saturation

# Sostenida
python capacity-planning/worker_sustained_test.py --test-type sustained
```

## Interpretación de Resultados

### Throughput
- **Alto**: > 40 videos/min
- **Medio**: 20-40 videos/min
- **Bajo**: < 20 videos/min

### Estabilidad
- **Estable**: Cola estable, recursos controlados
- **Inestable**: Cola creciente, recursos saturados

### Bottlenecks
- **CPU**: Procesamiento intensivo
- **Memoria**: Gestión de archivos grandes
- **I/O**: Lectura/escritura de archivos

## Recomendaciones

### Configuración Óptima
- **50MB con 2 workers**: Balance entre throughput y recursos
- **100MB con 1 worker**: Para archivos grandes
- **4 workers**: Solo para carga muy alta

### Escalabilidad
- **Horizontal**: Añadir más workers
- **Vertical**: Mejorar hardware (CPU, memoria)
- **Optimización**: Algoritmos de procesamiento

## Documentación Adicional

- **Resultados**: [capacity-planning/](capacity-planning/)
- **Scripts**: Todos los archivos Python en el directorio
- **Logs**: Archivos JSON con resultados detallados
- **Métricas**: CPU, memoria, I/O por prueba

## Troubleshooting

### Problemas Comunes
1. **Redis no conectado**: Iniciar con Docker
2. **Dependencias faltantes**: Instalar aiohttp, psutil, redis
3. **Permisos**: Verificar acceso a archivos
4. **Recursos**: Monitorear CPU y memoria

### Soluciones
```bash
# Redis
docker run -d --name redis -p 6379:6379 redis:alpine

# Dependencias
pip install aiohttp psutil redis

# Permisos
chmod +x capacity-planning/*.py
```

## Conclusión

El Plan B implementa un análisis completo de capacidad del worker, proporcionando métricas precisas para el dimensionamiento y optimización del sistema de procesamiento de videos.
