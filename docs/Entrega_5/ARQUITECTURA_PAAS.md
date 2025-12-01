# Arquitectura PaaS - Entrega 5

## 📋 Resumen

Este documento describe la arquitectura del sistema ANB Rising Stars Showcase desplegado en un modelo **PaaS (Platform as a Service)** utilizando servicios administrados de AWS, específicamente **AWS Lambda** para la capa web y **Amazon ECS (Elastic Container Service)** con **Fargate** para los workers.

## 🎯 Objetivo

Migrar de un modelo IaaS (EC2 con Auto Scaling) a un modelo PaaS para:
- Reducir complejidad operacional
- Eliminar gestión de servidores
- Aprovechar escalado automático administrado
- Evaluar beneficios de servicios PaaS vs IaaS

---

## 🏗️ Modelo de Despliegue

### Diagrama de Arquitectura PaaS

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   API Gateway        │
              │  - REST API          │
              │  - CORS              │
              │  - SSL/TLS           │
              └──────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │   AWS Lambda: Web Layer            │
        │   (Serverless Functions)            │
        │                                    │
        │  ┌──────────┐      ┌──────────┐   │
        │  │ Function │      │ Function │   │
        │  │  (API)  │      │  (API)  │   │
        │  │          │      │          │   │
        │  │ FastAPI  │      │ FastAPI  │   │
        │  │ Mangum   │      │ Mangum   │   │
        │  └──────────┘      └──────────┘   │
        │                                    │
        │   Auto Scaling: Automático         │
        │   Concurrencia: Hasta 10 (estudiante)│
        └────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   SQS     │   │   S3    │
   │PostgreSQL│    │  Queue    │   │ Bucket  │
   │         │    │           │   │         │
   │db.t3.micro│    │Standard Queue│ │Videos   │
   │Multi-AZ  │    │DLQ Config  │   │Original │
   │         │    │           │   │Processed│
   └─────────┘    └──────────┘   └─────────┘
        │                │               
        │                │               
        ▼                ▼               
   ┌────────────────────────────────────┐
   │   ECS Cluster: Worker Layer       │
   │   Launch Type: Fargate (Serverless)│
   │                                    │
   │  ┌──────────┐      ┌──────────┐   │
   │  │  Task    │      │  Task    │   │
   │  │ (Worker) │      │ (Worker) │   │
   │  │          │      │          │   │
   │  │SQS Worker│      │SQS Worker│   │
   │  │Video Proc│      │Video Proc│   │
   │  └──────────┘      └──────────┘   │
   │                                    │
   │   Auto Scaling: 1-3 tasks          │
   │   Métrica: SQS Queue Depth        │
   └────────────────────────────────────┘
```

---

## 📦 Modelo de Componentes

### Capa de Presentación

#### API Gateway
- **Tipo**: REST API
- **Función**: Punto de entrada HTTP/HTTPS para Lambda
- **Configuración**:
  - Endpoint Regional
  - Resource `{proxy+}` con método ANY
  - Integración Lambda Proxy
  - CORS habilitado
  - SSL/TLS automático

### Capa de Aplicación (Web)

#### AWS Lambda: API
- **Function Name**: `anb-api-lambda`
- **Runtime**: Python 3.12
- **Handler**: `lambda_handler.handler`
- **Adaptador**: Mangum (ASGI adapter para FastAPI)
- **Recursos**:
  - Memoria: 512 MB (configurable 128 MB - 10 GB)
  - Timeout: 30 segundos (máximo 15 minutos)
  - Ephemeral storage: 512 MB (configurable hasta 10 GB)
- **Escalado**:
  - Automático e ilimitado (hasta 10 concurrente en cuentas de estudiante)
  - Sin configuración de auto-scaling necesaria
- **Endpoints**:
  - `/api/auth/*` - Autenticación
  - `/api/videos/*` - Gestión de videos
  - `/api/public/*` - Endpoints públicos
  - `/health` - Health check
- **Ventajas**:
  - ✅ Pago por uso (muy económico)
  - ✅ Escalado automático sin configuración
  - ✅ Sin gestión de servidores
  - ✅ Alta disponibilidad automática

### Capa de Procesamiento (Workers)

#### ECS Service: Workers
- **Cluster**: `anb-rising-stars-cluster`
- **Service**: `anb-worker-service`
- **Launch Type**: Fargate (Serverless)
- **Task Definition**: `anb-worker-task`
- **Contenedor**: SQS Worker (Python 3.12)
- **Recursos**:
  - CPU: 1 vCPU (1024) - Más CPU para procesamiento de video
  - Memoria: 2 GB (2048) - Más memoria para MoviePy/FFmpeg
- **Escalado**:
  - Mínimo: 1 tarea
  - Máximo: 3 tareas
  - Métrica: `ApproximateNumberOfMessagesVisible` de SQS (10 mensajes por tarea)
- **Funcionalidad**:
  - Consume mensajes de SQS
  - Procesa videos (trim, resize, watermark)
  - Sube videos procesados a S3
  - Actualiza estado en RDS

### Capa de Datos

#### Amazon RDS (PostgreSQL)
- **Engine**: PostgreSQL 15.x
- **Instance Class**: `db.t3.micro` (desarrollo) / `db.t3.small` (producción)
- **Storage**: 20 GB gp3 (autoscaling hasta 100 GB)
- **Multi-AZ**: Habilitado (alta disponibilidad)
- **Backup**: Automático (7 días de retención)
- **Uso**: Almacenamiento de metadatos (usuarios, videos, votos)

#### Amazon S3
- **Bucket**: `anb-rising-stars-videos-east1`
- **Prefixes**:
  - `uploads/` - Videos originales
  - `processed_videos/` - Videos procesados
  - `assets/` - Assets estáticos (logo ANB)
- **Configuración**:
  - Lectura pública habilitada (para videos procesados)
  - Versionado habilitado
  - Encriptación SSE-S3

#### Amazon SQS
- **Queue**: `anb-video-processing-queue`
- **Tipo**: Standard Queue
- **Configuración**:
  - Visibility timeout: 300 segundos (5 minutos)
  - Message retention: 14 días
  - Long polling: 20 segundos
  - Dead Letter Queue: `anb-video-processing-dlq`
  - Max receives: 3

### Capa de Monitoreo

#### Amazon CloudWatch
- **Logs**:
  - `/ecs/anb-api` - Logs de la API
  - `/ecs/anb-worker` - Logs de workers
- **Métricas**:
  - ECS: CPU, memoria, tareas activas
  - ALB: Request count, response time, error rate
  - SQS: Queue depth, message age
  - RDS: CPU, conexiones, storage
- **Alarms**: Configurados para auto-scaling y alertas

---

## 🔄 Flujo de Procesamiento

### 1. Subida de Video

```
Usuario → ALB → ECS Task (API) → S3 (uploads/) → SQS → RDS (metadatos)
```

1. Usuario sube video vía API (`POST /api/videos/upload`)
2. API valida autenticación y archivo
3. API sube video original a S3 (`uploads/`)
4. API crea registro en RDS con estado `pending`
5. API envía mensaje a SQS con `video_id` y `video_path`
6. API retorna respuesta al usuario

### 2. Procesamiento de Video

```
SQS → ECS Task (Worker) → S3 (download) → Procesamiento → S3 (processed_videos/) → RDS (update) → SQS (delete)
```

1. Worker recibe mensaje de SQS
2. Worker descarga video de S3 a `/tmp`
3. Worker procesa video:
   - Trim a 30 segundos máximo
   - Resize a 720p (1280x720)
   - Agregar watermark (logo ANB)
4. Worker sube video procesado a S3 (`processed_videos/`)
5. Worker actualiza estado en RDS a `processed`
6. Worker elimina mensaje de SQS
7. Worker limpia archivo temporal

### 3. Consulta de Videos

```
Usuario → ALB → ECS Task (API) → RDS → S3 (URL pública) → Usuario
```

1. Usuario consulta videos (`GET /api/videos` o `/api/public/videos`)
2. API consulta RDS
3. API retorna metadatos con URL pública de S3
4. Usuario accede directamente a S3 para ver video

---

## 🔧 Tecnologías y Servicios

### Servicios AWS Utilizados

| Servicio | Propósito | Beneficio PaaS |
|----------|-----------|----------------|
| **ECS Fargate** | Ejecución de contenedores | Sin gestión de servidores, escalado automático |
| **Application Load Balancer** | Distribución de carga | Alta disponibilidad, health checks automáticos |
| **Amazon RDS** | Base de datos administrada | Backups automáticos, Multi-AZ, mantenimiento automático |
| **Amazon S3** | Almacenamiento de objetos | Alta durabilidad, escalabilidad ilimitada |
| **Amazon SQS** | Mensajería asíncrona | Desacoplamiento, garantía de entrega |
| **Amazon CloudWatch** | Monitoreo y logs | Observabilidad completa, alertas automáticas |
| **Amazon ECR** | Registro de contenedores | Almacenamiento seguro de imágenes Docker |

### Stack Tecnológico

- **Backend**: FastAPI (Python 3.12)
- **Base de Datos**: PostgreSQL 15.x
- **Procesamiento de Video**: MoviePy, FFmpeg
- **Contenedores**: Docker
- **Orquestación**: Amazon ECS (Fargate)
- **Mensajería**: Amazon SQS
- **Almacenamiento**: Amazon S3

---

## 📊 Comparación: IaaS vs PaaS

### Entrega 4 (IaaS) vs Entrega 5 (PaaS)

| Aspecto | Entrega 4 (IaaS) | Entrega 5 (PaaS) |
|---------|-----------------|------------------|
| **Infraestructura** | EC2 Instances (t3.small) | ECS Fargate (Serverless) |
| **Gestión de Servidores** | Manual (AMI, Launch Templates) | Automática (AWS gestiona) |
| **Escalado** | Auto Scaling Groups (ASG) | ECS Service Auto Scaling |
| **Actualizaciones** | Crear nueva AMI, actualizar Launch Template | Actualizar Task Definition, redeploy |
| **Monitoreo** | CloudWatch + logs en instancias | CloudWatch Logs integrado |
| **Costo Base** | ~$260-360/mes | ~$85-190/mes |
| **Complejidad Operacional** | Alta (gestión de AMIs, ASGs, etc.) | Baja (solo Task Definitions) |
| **Tiempo de Despliegue** | 30-60 minutos | 10-20 minutos |
| **Flexibilidad** | Alta (control total) | Media (limitado a opciones de ECS) |

### Beneficios del Modelo PaaS

✅ **Reducción de Complejidad**
- No necesitas gestionar AMIs, Launch Templates, Auto Scaling Groups
- AWS gestiona el aprovisionamiento y mantenimiento de servidores

✅ **Escalado Automático Simplificado**
- ECS Service Auto Scaling es más simple que ASG
- Métricas integradas con CloudWatch

✅ **Actualizaciones Más Rápidas**
- Solo actualizas la imagen Docker y redeployas
- No necesitas crear nuevas AMIs

✅ **Menor Costo Base**
- Fargate cobra solo por recursos usados
- No pagas por instancias detenidas

✅ **Alta Disponibilidad Integrada**
- Fargate distribuye tareas automáticamente en múltiples AZs
- No necesitas configurar manualmente subnets por AZ

### Desventajas del Modelo PaaS

❌ **Menor Control**
- No puedes acceder directamente a los servidores
- Limitado a opciones de configuración de ECS

❌ **Debugging Más Complejo**
- Dependes de logs de CloudWatch
- No puedes SSH a las instancias

❌ **Vendor Lock-in**
- Dependes de servicios específicos de AWS
- Migración a otro proveedor requiere más trabajo

---

## 🔐 Seguridad

### IAM Roles

- **Task Role**: Permisos para que las tareas accedan a SQS, S3, RDS
- **Task Execution Role**: Permisos para que ECS descargue imágenes de ECR y escriba logs a CloudWatch

### Security Groups

- **ALB Security Group**: Permite tráfico HTTP/HTTPS desde internet
- **API Security Group**: Permite tráfico del ALB en puerto 8000
- **Worker Security Group**: Permite tráfico saliente a SQS, S3, RDS
- **RDS Security Group**: Permite tráfico desde API y Worker security groups

### Red

- **VPC**: Red privada aislada
- **Subnets Privadas**: Tareas ECS en subnets privadas (sin IP pública)
- **NAT Gateway**: Para acceso saliente a internet (ECR, S3, SQS)

---

## 📈 Escalabilidad

### Escalado Horizontal

- **API**: Escala de 2 a 5 tareas basado en `ALBRequestCountPerTarget`
- **Workers**: Escala de 1 a 3 tareas basado en profundidad de cola SQS

### Escalado Vertical

- **API**: Puede aumentar CPU/memoria en Task Definition (0.5 vCPU → 1 vCPU, 1 GB → 2 GB)
- **Workers**: Puede aumentar CPU/memoria para procesar videos más rápido

### Límites

- **Fargate**: Hasta 10 vCPU y 30 GB de memoria por tarea
- **ECS Service**: Hasta 10,000 tareas por servicio
- **SQS**: Escalabilidad ilimitada (Standard Queue)

---

## 📝 Checklist de Actividades

### Actividad 1: Capa Web en ECS (20%)
- ✅ ECS Cluster creado
- ✅ Task Definition para API creada
- ✅ ECS Service para API desplegado
- ✅ ALB configurado y funcionando
- ✅ API responde a solicitudes HTTP

### Actividad 2: Capa Worker en ECS (20%)
- ✅ Task Definition para Workers creada
- ✅ ECS Service para Workers desplegado
- ✅ Workers consumen mensajes de SQS
- ✅ Procesamiento de videos funcionando

### Actividad 3: Base de Datos RDS (10%)
- ✅ Instancia RDS configurada (db.t3.micro)
- ✅ Aplicación conectada a RDS
- ✅ Migraciones ejecutadas
- ✅ Datos persisten correctamente

### Actividad 4: Sistema de Mensajería (10%)
- ✅ SQS configurado
- ✅ Aplicación envía mensajes a SQS
- ✅ Workers consumen mensajes de SQS
- ✅ Flujo completo funcionando

### Actividad 5: Almacenamiento S3 (10%)
- ✅ Bucket S3 configurado
- ✅ Aplicación sube videos a S3
- ✅ Videos procesados se guardan en S3
- ✅ URLs públicas funcionando

### Actividad 6: Requerimientos Funcionales (10%)
- ✅ Autenticación funcionando
- ✅ Subida de videos funcionando
- ✅ Procesamiento asíncrono funcionando
- ✅ Consulta de videos funcionando
- ✅ Votación funcionando

---

## 🔗 Referencias

- [Guía de Despliegue PaaS](AWS_PAAS_DEPLOYMENT_GUIDE.md)
- [Plan de Migración IaaS → PaaS](MIGRATION_PLAN_PAAS.md)
- [Documentación AWS ECS](https://docs.aws.amazon.com/ecs/)
- [Documentación AWS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

