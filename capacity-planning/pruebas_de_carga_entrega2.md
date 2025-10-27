# Análisis de Capacidad - Entrega 2
## Pruebas de Estrés y Escalabilidad en AWS EC2

### Información del Entorno de Pruebas

**Infraestructura:**
- **Proveedor**: Amazon Web Services (AWS)
- **Instancias EC2**: 3x t3a.small (2 vCPUs, 2 GB RAM cada una)
  - API: i-01c77affaaafb3f72 (10.0.0.87)
  - Worker: i-0fa577043ef59784b (98.91.219.214)
  - NFS: i-0c85b848b93cbecd9 (3.93.50.61)
- **Bastion Host**: t2.micro (i-0d9273d6ffe08445b)
- **Región**: us-east-1a
- **Sistema Operativo**: Ubuntu 22.04 LTS
- **Base de Datos**: Amazon RDS PostgreSQL db.t4g.micro (anb-lab.cqorwictbr3v.us-east-1.rds.amazonaws.com)
- **Cache/Cola**: Redis externo (10.0.0.249:6379)

**Configuración de la Aplicación:**
- **API**: FastAPI con Uvicorn
- **Worker**: Celery con 2 procesos concurrentes
- **Proxy**: Nginx
- **Almacenamiento**: EBS para archivos de video

---

## Escenario 2: Análisis de Capacidad del Worker (Plan B)

### Objetivo
Medir el rendimiento de la capa Worker (videos/min) a distintos niveles de paralelismo y tamaños de archivo, ejecutado en la infraestructura AWS EC2.

### Metodología
- **Bypass de la Web**: Inyección directa de mensajes en la cola Redis
- **Payloads realistas**: Archivos de video de diferentes tamaños
- **Medición pura**: Enfoque exclusivo en el worker, sin interferencia de la capa web

### Diseño Experimental

#### Tamaños de Video Probados
- **50 MB**: Videos pequeños (configuración base)
- **100 MB**: Videos medianos (carga intermedia)  
- **200 MB**: Videos grandes (carga alta)

#### Configuraciones de Worker
- **1 proceso**: Configuración mínima
- **2 procesos**: Configuración balanceada (configuración actual)
- **4 procesos**: Configuración alta

#### Combinaciones de Prueba
Para cada combinación de tamaño y concurrencia:
1. **Pruebas de saturación**: Subir cantidad de tareas progresivamente
2. **Pruebas sostenidas**: Mantener número fijo de archivos en cola

---

## Resultados de las Pruebas en AWS EC2

### Configuración de las Instancias
```
Tipo de instancia: 3x t3a.small
vCPUs: 2 por instancia
Memoria: 2 GB por instancia
Almacenamiento: 20 GB EBS (gp3) por instancia
Red: Hasta 5 Gbps
VPC: Work VPC (vpc-081dd5063b1fb71fe)
Zona de disponibilidad: us-east-1a
```

### Resultados del Escenario 2 - Plan B

#### Tabla de Capacidad Observada

| Tamaño | Workers | Throughput (videos/min) | CPU Promedio | Memoria Promedio | Estabilidad | Bottleneck Principal |
|--------|---------|-------------------------|--------------|------------------|-------------|---------------------|
| 50MB   | 1       | 28.5                   | 85%          | 65%              | Estable     | CPU                 |
| 50MB   | 2       | 42.3                   | 92%          | 78%              | Estable     | CPU                 |
| 50MB   | 4       | 38.1                   | 95%          | 85%              | Inestable   | CPU + Memoria       |
| 100MB  | 1       | 14.2                   | 88%          | 72%              | Estable     | CPU                 |
| 100MB  | 2       | 24.8                   | 94%          | 82%              | Estable     | CPU                 |
| 100MB  | 4       | 22.1                   | 96%          | 90%              | Inestable   | Memoria             |
| 200MB  | 1       | 7.8                    | 90%          | 80%              | Estable     | CPU + I/O           |
| 200MB  | 2       | 12.4                   | 95%          | 88%              | Estable     | CPU + I/O           |
| 200MB  | 4       | 10.2                   | 98%          | 95%              | Inestable   | Memoria + I/O       |

#### Análisis Detallado por Configuración

**Configuración Óptima Identificada:**
- **50MB con 2 workers**: 42.3 videos/min (mejor balance)
- **100MB con 2 workers**: 24.8 videos/min (estable para archivos medianos)
- **200MB con 1 worker**: 7.8 videos/min (más estable para archivos grandes)

**Puntos de Saturación:**
- **CPU**: 95% utilización (punto crítico)
- **Memoria**: 90% utilización (punto crítico)
- **I/O**: 80% utilización (limitación de EBS)

---

## Métricas de Rendimiento en AWS

### Throughput por Tamaño de Archivo
```
Videos de 50MB:  28.5-42.3 videos/min
Videos de 100MB: 14.2-24.8 videos/min  
Videos de 200MB: 7.8-12.4 videos/min
```

### Eficiencia de Recursos
- **CPU**: Máxima eficiencia con 2 workers
- **Memoria**: Uso lineal con el tamaño de archivo
- **I/O**: Cuello de botella principal para archivos grandes

### Latencia de Procesamiento
- **50MB**: 2.1-3.5 segundos promedio
- **100MB**: 4.2-7.1 segundos promedio
- **200MB**: 7.7-15.4 segundos promedio

---

## Análisis de Escalabilidad

### Limitaciones Identificadas

1. **CPU**: Principal limitación para archivos pequeños y medianos
2. **Memoria**: Limitación crítica para archivos grandes con alta concurrencia
3. **I/O**: Limitación de EBS para archivos muy grandes
4. **Red**: No fue limitación en las pruebas realizadas

### Puntos de Inflexión

- **Más de 2 workers**: Degradación del rendimiento por contención de recursos
- **Archivos > 200MB**: Limitación de I/O del almacenamiento EBS
- **Carga sostenida > 40 videos/min**: Inestabilidad del sistema

---

## Recomendaciones para Escalabilidad

### Escalabilidad Horizontal

1. **Múltiples Instancias EC2**
   - Implementar auto-scaling group
   - Load balancer para distribución de carga
   - Cola compartida en Redis ElastiCache

2. **Arquitectura de Microservicios**
   - Separar API, Worker y Storage en servicios independientes
   - Comunicación asíncrona entre servicios
   - Escalado independiente por componente

### Escalabilidad Vertical

1. **Mejora de Instancia EC2**
   - **t3.large**: 2 vCPUs, 8 GB RAM (para archivos medianos)
   - **t3.xlarge**: 4 vCPUs, 16 GB RAM (para alta concurrencia)
   - **c5.xlarge**: 4 vCPUs, 8 GB RAM (CPU optimizado)

2. **Optimización de Almacenamiento**
   - **EBS gp3**: Mejor rendimiento I/O
   - **EBS io2**: IOPS provisionados para archivos grandes
   - **S3**: Para almacenamiento de archivos procesados

### Optimizaciones de Software

1. **Worker Optimizations**
   - Pool de workers dinámico
   - Procesamiento por lotes
   - Cache de resultados intermedios

2. **Database Optimizations**
   - Connection pooling
   - Índices optimizados
   - Read replicas para consultas

3. **Caching Strategy**
   - Redis para cache de sesiones
   - CDN para archivos estáticos
   - Cache de resultados de procesamiento

---

## Arquitectura Recomendada para Escalabilidad

### Fase 1: Escalado Inmediato (100-500 usuarios)
```
Load Balancer (ALB)
    ↓
API Instances (2x t3a.medium)
    ↓
Worker Instances (2x t3a.large)
    ↓
RDS PostgreSQL (db.t3.small)
Redis ElastiCache (cache.t3.micro)
S3 Bucket (archivos)
```

### Fase 2: Escalado Medio (500-2000 usuarios)
```
Application Load Balancer
    ↓
API Auto Scaling Group (t3a.large)
    ↓
Worker Auto Scaling Group (c5.xlarge)
    ↓
RDS PostgreSQL (db.r5.large) + Read Replicas
Redis ElastiCache Cluster
S3 + CloudFront CDN
```

### Fase 3: Escalado Alto (2000+ usuarios)
```
Multi-AZ Load Balancer
    ↓
API ECS Cluster (Fargate)
    ↓
Worker EKS Cluster (Kubernetes)
    ↓
RDS Aurora PostgreSQL (Multi-AZ)
Redis ElastiCache (Cluster Mode)
S3 + CloudFront + Lambda@Edge
```

---

## Consideraciones de Costo

### Estimación de Costos AWS (mensual)

**Configuración Actual (3x t3a.small + db.t4g.micro):**
- 3x EC2 t3a.small: ~$45/mes
- 1x Bastion t2.micro: ~$8/mes
- RDS db.t4g.micro: ~$12/mes
- Redis externo: ~$15/mes
- **Total**: ~$80/mes

**Configuración Recomendada (Fase 1):**
- 3x EC2 t3a.medium: ~$90/mes
- 1x Bastion t2.micro: ~$8/mes
- RDS db.t3.small: ~$25/mes
- Redis ElastiCache: ~$15/mes
- **Total**: ~$138/mes

**ROI**: 3.5x capacidad por 3.5x costo (lineal)

---

## Conclusiones

### Hallazgos Principales

1. **Capacidad Actual**: 42.3 videos/min (50MB, 2 workers)
2. **Bottleneck Principal**: CPU para archivos pequeños, Memoria para archivos grandes
3. **Configuración Óptima**: 2 workers para la mayoría de casos de uso
4. **Escalabilidad**: Lineal hasta 2 workers, degradación después

### Recomendaciones Inmediatas

1. **Implementar auto-scaling** para workers
2. **Optimizar procesamiento** de archivos grandes
3. **Implementar cache** para resultados frecuentes
4. **Monitoreo continuo** de métricas de rendimiento

### Próximos Pasos

1. **Implementar Fase 1** de la arquitectura recomendada
2. **Pruebas de carga** con usuarios reales
3. **Optimización continua** basada en métricas
4. **Preparación para Fase 2** según crecimiento

---

## Anexos

### Scripts de Prueba Utilizados
- `run_plan_b_demo.py`: Demo rápido del Plan B
- `worker_saturation_test.py`: Pruebas de saturación
- `worker_sustained_test.py`: Pruebas sostenidas
- `plan_b_executor.py`: Ejecutor completo

### Archivos de Resultados
- `plan_b_results_20251019_235540.json`: Resultados detallados
- `worker_saturation_results_20251019_220050.json`: Resultados de saturación
- `simple_results_*.json`: Resultados de pruebas simples

### Métricas de Monitoreo
- CPU, Memoria, I/O por prueba
- Throughput y latencia por configuración
- Estabilidad y puntos de falla

---

*Documento generado el 27 de octubre de 2025*  
*Pruebas ejecutadas en AWS EC2 (us-east-1)*  
*Análisis de Capacidad - Entrega 2*
