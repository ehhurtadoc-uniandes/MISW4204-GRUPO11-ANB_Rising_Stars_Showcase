# Arquitectura de la Aplicación - Entrega 4

## 📋 Resumen Ejecutivo

Este documento describe la arquitectura del sistema ANB Rising Stars Showcase en su versión de la Entrega 4, que implementa escalabilidad y alta disponibilidad en AWS. La arquitectura ha sido diseñada para soportar el procesamiento asíncrono de videos mediante mensajería SQS, auto-scaling de workers basado en la profundidad de la cola, y despliegue en múltiples Availability Zones para garantizar alta disponibilidad.

---

## 🏗️ Modelo de Despliegue

### Diagrama de Arquitectura AWS

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │    Balancer (ALB)   │
              │   (Multi-AZ)        │
              └──────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  EC2    │     │  EC2    │     │  EC2    │
   │ Backend │     │ Backend │     │ Backend │
   │ (ASG)   │     │ (ASG)   │     │ (ASG)   │
   │ AZ-1a   │     │ AZ-1b   │     │ AZ-1c   │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │                │
        └───────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   SQS     │   │   S3    │
   │PostgreSQL│    │  Queue    │   │ Bucket  │
   │ (Multi-AZ)│    │           │   │         │
   └─────────┘    └──────────┘   └─────────┘
        │               │               
        │               │               
        ▼               ▼               
   ┌─────────┐    ┌──────────┐
   │   EC2   │    │   EC2    │
   │ Worker  │    │ Worker   │
   │ (ASG)   │    │ (ASG)    │
   │ AZ-1a   │    │ AZ-1b    │
   └─────────┘    └──────────┘
```

### Descripción de la Arquitectura de Despliegue

La arquitectura está diseñada para alta disponibilidad y escalabilidad horizontal:

1. **Capa de Entrada (Internet-facing)**
   - **Application Load Balancer (ALB)**: Distribuye el tráfico HTTP/HTTPS entre múltiples instancias backend
   - **Multi-AZ**: Desplegado en múltiples Availability Zones para alta disponibilidad
   - **Health Checks**: Monitorea el estado de las instancias backend

2. **Capa de Aplicación (Backend)**
   - **Auto Scaling Group (Backend)**: Grupo de instancias EC2 que ejecutan la API FastAPI
   - **Escalamiento Automático**: Basado en métricas de CPU o RequestCountPerTarget del ALB
   - **Multi-AZ**: Instancias desplegadas en mínimo 2 Availability Zones
   - **Capacidad**: Mínimo 2, máximo 3 instancias

3. **Capa de Procesamiento (Workers)**
   - **Auto Scaling Group (Workers)**: Grupo de instancias EC2 que procesan videos
   - **Escalamiento Automático**: Basado en profundidad de cola SQS (`ApproximateNumberOfMessagesVisible`)
   - **Multi-AZ**: Instancias desplegadas en mínimo 2 Availability Zones
   - **Capacidad**: Mínimo 1, máximo 3 instancias

4. **Capa de Datos**
   - **RDS PostgreSQL (Multi-AZ)**: Base de datos relacional con réplica en otra AZ
   - **Amazon SQS**: Cola de mensajes para comunicación asíncrona entre backend y workers
   - **Amazon S3**: Almacenamiento de videos originales y procesados

5. **Capa de Monitoreo**
   - **Amazon CloudWatch**: Monitoreo de métricas, alarms y dashboards
   - **Auto Scaling Policies**: Políticas de escalamiento basadas en métricas de CloudWatch

---

## 🧩 Modelo de Componentes

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    Capa de Presentación                      │
├─────────────────────────────────────────────────────────────┤
│  Application Load Balancer (ALB)                            │
│  - Distribución de carga                                     │
│  - Health checks                                            │
│  - SSL/TLS termination                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Capa de Aplicación                        │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (EC2 - Auto Scaling)                       │
│  ├── API REST Endpoints                                     │
│  │   ├── /api/auth/* (Autenticación JWT)                   │
│  │   ├── /api/users/* (Gestión de usuarios)                │
│  │   ├── /api/videos/* (Gestión de videos)                 │
│  │   └── /api/public/* (Endpoints públicos)                │
│  ├── Servicios                                              │
│  │   ├── SQSService (Envío de mensajes a SQS)              │
│  │   ├── FileStorageService (S3 upload/download)           │
│  │   └── VideoService (Lógica de negocio)                  │
│  └── Integraciones                                          │
│      ├── PostgreSQL (RDS) - Metadatos                       │
│      ├── SQS - Envío de tareas de procesamiento            │
│      └── S3 - Almacenamiento de videos                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Capa de Mensajería                          │
├─────────────────────────────────────────────────────────────┤
│  Amazon SQS                                                  │
│  ├── anb-video-processing-queue (Cola principal)            │
│  ├── anb-video-processing-dlq (Dead Letter Queue)           │
│  └── Características                                        │
│      ├── Standard Queue                                    │
│      ├── Visibility Timeout: 300s                          │
│      ├── Message Retention: 14 días                        │
│      └── Long Polling: 20s                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                Capa de Procesamiento                         │
├─────────────────────────────────────────────────────────────┤
│  SQS Workers (EC2 - Auto Scaling)                           │
│  ├── Worker Loop                                             │
│  │   ├── Polling de mensajes SQS                           │
│  │   ├── Procesamiento de videos                           │
│  │   └── Eliminación de mensajes                           │
│  ├── Procesamiento de Video                                 │
│  │   ├── Descarga desde S3                                 │
│  │   ├── Recorte a 30 segundos                             │
│  │   ├── Redimensionamiento a 720p                         │
│  │   ├── Adición de watermark ANB                         │
│  │   └── Upload a S3                                       │
│  └── Integraciones                                          │
│      ├── PostgreSQL (RDS) - Actualización de estado       │
│      ├── SQS - Consumo de mensajes                         │
│      └── S3 - Download/Upload de videos                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Capa de Datos                            │
├─────────────────────────────────────────────────────────────┤
│  Amazon RDS PostgreSQL (Multi-AZ)                            │
│  ├── Esquema de Base de Datos                               │
│  │   ├── users (Usuarios)                                  │
│  │   ├── videos (Metadatos de videos)                      │
│  │   ├── votes (Votos)                                      │
│  │   └── rankings (Rankings)                               │
│  └── Características                                        │
│      ├── Multi-AZ deployment                               │
│      ├── Automated backups                                 │
│      └── High availability                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 Capa de Almacenamiento                      │
├─────────────────────────────────────────────────────────────┤
│  Amazon S3 Bucket                                           │
│  ├── uploads/ (Videos originales)                          │
│  ├── processed_videos/ (Videos procesados)                  │
│  └── assets/ (Assets estáticos)                             │
│  └── Características                                        │
│      ├── Public read access                                │
│      ├── Versioning enabled                                 │
│      └── Encryption (SSE-S3)                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Capa de Monitoreo                           │
├─────────────────────────────────────────────────────────────┤
│  Amazon CloudWatch                                          │
│  ├── Métricas                                               │
│  │   ├── SQS Queue Depth                                   │
│  │   ├── EC2 CPU/Memory                                    │
│  │   ├── ALB Request Count                                 │
│  │   └── RDS Performance                                   │
│  ├── Alarms                                                 │
│  │   ├── Worker Scale-Up/Down                              │
│  │   └── Backend Scale-Up/Down                             │
│  └── Dashboards                                             │
│      └── System Overview                                    │
└─────────────────────────────────────────────────────────────┘
```

### Descripción Detallada de Componentes

#### 1. Application Load Balancer (ALB)
- **Tecnología**: AWS Application Load Balancer
- **Función**: Distribuye el tráfico HTTP/HTTPS entre múltiples instancias backend
- **Configuración**:
  - Escucha en puerto 80 (HTTP) y 443 (HTTPS)
  - Health checks en `/health`
  - Target Group apunta a instancias backend en puerto 8000
  - Desplegado en múltiples Availability Zones

#### 2. FastAPI Backend (EC2 - Auto Scaling)
- **Tecnología**: Python 3.13 + FastAPI 0.118 + Uvicorn
- **Función**: API REST que expone endpoints para gestión de usuarios, videos y votación
- **Componentes principales**:
  - **SQSService**: Envía mensajes a SQS cuando se sube un video
  - **FileStorageService**: Maneja upload/download de videos desde/hacia S3
  - **VideoService**: Lógica de negocio para gestión de videos
  - **AuthService**: Autenticación y autorización con JWT
- **Auto Scaling**: Basado en métricas de CPU o RequestCountPerTarget
- **Especificaciones**: 2 vCPU, 2 GiB RAM, 30 GiB almacenamiento

#### 3. Amazon SQS
- **Tecnología**: Amazon Simple Queue Service (Standard Queue)
- **Función**: Sistema de mensajería asíncrona entre backend y workers
- **Configuración**:
  - **Cola Principal**: `anb-video-processing-queue`
    - Visibility Timeout: 300 segundos
    - Message Retention: 14 días
    - Receive Message Wait Time: 20 segundos (long polling)
  - **Dead Letter Queue**: `anb-video-processing-dlq`
    - Maximum Receives: 3
- **Flujo**: Backend envía mensajes → Workers consumen mensajes → Workers eliminan mensajes después de procesar

#### 4. SQS Workers (EC2 - Auto Scaling)
- **Tecnología**: Python 3.13 + Boto3 + MoviePy
- **Función**: Procesamiento asíncrono de videos
- **Flujo de trabajo**:
  1. Polling continuo de mensajes desde SQS
  2. Recepción de mensaje con `video_id` y `video_path`
  3. Descarga de video original desde S3
  4. Procesamiento local:
     - Recorte a 30 segundos
     - Redimensionamiento a 720p
     - Adición de watermark ANB
     - Generación de intro/outro
  5. Upload de video procesado a S3
  6. Actualización de estado en base de datos
  7. Eliminación de mensaje de SQS
- **Auto Scaling**: Basado en `ApproximateNumberOfMessagesVisible` de SQS
- **Especificaciones**: 2 vCPU, 2 GiB RAM, 30 GiB almacenamiento

#### 5. Amazon RDS PostgreSQL
- **Tecnología**: PostgreSQL 15.x
- **Función**: Almacenamiento de datos estructurados
- **Esquema principal**:
  - `users`: Información de usuarios/jugadores
  - `videos`: Metadatos de videos (título, estado, URLs, timestamps)
  - `votes`: Votos de usuarios por videos
  - `rankings`: Rankings calculados
- **Configuración**:
  - Multi-AZ deployment para alta disponibilidad
  - Automated backups (7 días de retención)
  - Instance class: db.t3.medium o superior

#### 6. Amazon S3
- **Tecnología**: Amazon Simple Storage Service
- **Función**: Almacenamiento de objetos (videos)
- **Estructura**:
  - `uploads/`: Videos originales subidos por usuarios
  - `processed_videos/`: Videos procesados listos para visualización
  - `assets/`: Assets estáticos (logo ANB, etc.)
- **Configuración**:
  - Public read access para videos procesados
  - Versioning habilitado
  - Encryption: SSE-S3
  - CORS configurado para acceso desde navegadores

#### 7. Amazon CloudWatch
- **Tecnología**: Amazon CloudWatch
- **Función**: Monitoreo y alertas del sistema
- **Métricas principales**:
  - SQS: `ApproximateNumberOfMessagesVisible` (para auto-scaling de workers)
  - EC2: CPU, Memory, Network
  - ALB: RequestCount, TargetResponseTime, HTTPCode_Target_5XX_Count
  - RDS: CPUUtilization, DatabaseConnections
- **Alarms**:
  - Worker Scale-Up: Cuando mensajes en cola > umbral
  - Worker Scale-Down: Cuando mensajes en cola < umbral
  - Backend Scale-Up/Down: Basado en CPU o RequestCountPerTarget

---

## 🔧 Tecnologías y Servicios Incorporados

### Tecnologías de Desarrollo

#### Backend
- **Python 3.13**: Lenguaje de programación
- **FastAPI 0.118**: Framework web moderno y rápido para APIs REST
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **Pydantic**: Validación de datos y serialización
- **SQLAlchemy**: ORM para interacción con base de datos
- **Alembic**: Migraciones de base de datos
- **Boto3**: SDK de AWS para Python (SQS, S3)

#### Procesamiento de Video
- **MoviePy**: Biblioteca para procesamiento de video
  - Recorte de videos
  - Redimensionamiento
  - Adición de texto/imágenes (watermark)
  - Generación de clips

#### Autenticación
- **JWT (JSON Web Tokens)**: Autenticación stateless
- **Passlib**: Hashing de contraseñas (bcrypt)

### Servicios AWS

#### Compute
- **Amazon EC2**: Instancias virtuales para backend y workers
  - Tipo: `t3.small` (2 vCPU, 2 GiB RAM)
  - Almacenamiento: 30 GiB gp3
  - Auto Scaling Groups para escalamiento automático

#### Networking
- **Amazon VPC**: Red privada virtual
  - Subnets públicas y privadas
  - Internet Gateway para acceso público
  - NAT Gateway para acceso saliente desde subnets privadas
- **Application Load Balancer (ALB)**: Distribución de carga
  - Health checks automáticos
  - SSL/TLS termination
  - Multi-AZ deployment

#### Base de Datos
- **Amazon RDS PostgreSQL**: Base de datos relacional gestionada
  - Multi-AZ deployment para alta disponibilidad
  - Automated backups
  - Punto de restauración (Point-in-time recovery)

#### Almacenamiento
- **Amazon S3**: Almacenamiento de objetos
  - Durabilidad y disponibilidad alta
  - Public read access para videos procesados
  - Versioning y encryption

#### Mensajería
- **Amazon SQS**: Cola de mensajes
  - Standard Queue para alta throughput
  - Dead Letter Queue para manejo de errores
  - Long polling para eficiencia
  - Integración con Auto Scaling

#### Monitoreo
- **Amazon CloudWatch**: Monitoreo y observabilidad
  - Métricas de recursos AWS
  - Alarms para auto-scaling
  - Dashboards para visualización
  - Logs centralizados

#### Seguridad
- **IAM Roles**: Permisos para instancias EC2
  - `anb-backend-role`: Permisos para SQS (SendMessage) y S3 (PutObject)
  - `anb-worker-role`: Permisos para SQS (ReceiveMessage, DeleteMessage) y S3 (GetObject, PutObject)
- **Security Groups**: Firewall a nivel de instancia
  - Reglas de entrada/salida específicas
  - Aislamiento de red

---

## 🔄 Cambios Realizados con Respecto a la Entrega 3

### Resumen de Cambios

La Entrega 4 introduce cambios significativos para mejorar la escalabilidad y alta disponibilidad del sistema:

| Aspecto | Entrega 3 | Entrega 4 | Impacto |
|---------|-----------|-----------|---------|
| **Mensajería** | Celery + Redis (EC2) | Amazon SQS | Mayor escalabilidad, servicio gestionado |
| **Workers** | Instancia EC2 fija | Auto Scaling Group | Escalamiento automático basado en carga |
| **Alta Disponibilidad** | Single AZ | Multi-AZ (mínimo 2) | Mayor resiliencia ante fallos |
| **Monitoreo** | Básico | CloudWatch completo | Mejor observabilidad y auto-scaling |

### Cambios Detallados

#### 1. Migración de Celery/Redis a Amazon SQS (Actividad 4 - 20%)

**Antes (Entrega 3)**:
- **Celery**: Framework de procesamiento asíncrono
- **Redis (EC2)**: Broker de mensajes en instancia EC2 dedicada
- **Flujo**: Backend → Redis → Celery Worker

**Ahora (Entrega 4)**:
- **Amazon SQS**: Servicio de mensajería gestionado por AWS
- **Eliminación de Redis**: Ya no se requiere instancia EC2 para Redis
- **Flujo**: Backend → SQS → SQS Worker

**Beneficios**:
- ✅ Servicio gestionado (no requiere mantenimiento de infraestructura)
- ✅ Escalabilidad automática de la cola
- ✅ Integración nativa con Auto Scaling
- ✅ Dead Letter Queue para manejo de errores
- ✅ Reducción de costos (no requiere instancia EC2 para Redis)

**Cambios en el Código**:
- `app/services/sqs_service.py`: Nuevo servicio para interactuar con SQS
- `app/workers/sqs_worker.py`: Worker que consume de SQS en lugar de Celery
- `app/api/videos.py`: Envía mensajes a SQS en lugar de tareas Celery
- Eliminación de dependencias: `celery`, `redis` (solo para workers)

#### 2. Auto Scaling de Workers (Actividad 3 - 20%)

**Antes (Entrega 3)**:
- **Workers**: Instancia EC2 fija (1 o más instancias manuales)
- **Escalamiento**: Manual (crear/terminar instancias manualmente)
- **Monitoreo**: Básico, sin métricas de cola

**Ahora (Entrega 4)**:
- **Workers**: Auto Scaling Group con capacidad dinámica
- **Escalamiento Automático**: Basado en `ApproximateNumberOfMessagesVisible` de SQS
- **Política**: Target Tracking (mantener ~10 mensajes por instancia)
- **Capacidad**: Mínimo 1, máximo 3 instancias

**Beneficios**:
- ✅ Escalamiento automático según demanda
- ✅ Reducción de costos (escala hacia abajo cuando no hay carga)
- ✅ Mejor utilización de recursos
- ✅ Alta disponibilidad (múltiples workers en diferentes AZs)

**Configuración**:
- Auto Scaling Group: `anb-worker-asg`
- Launch Template: `anb-worker-launch-template`
- Target Tracking Policy: Basada en métrica SQS
- CloudWatch Alarms: Creados automáticamente por Target Tracking

#### 3. Alta Disponibilidad Multi-AZ (Actividad 5 - 20%)

**Antes (Entrega 3)**:
- **Backend**: Posiblemente en single AZ
- **Workers**: Posiblemente en single AZ
- **RDS**: Multi-AZ (ya implementado)

**Ahora (Entrega 4)**:
- **Backend ASG**: Desplegado en mínimo 2 Availability Zones
- **Worker ASG**: Desplegado en mínimo 2 Availability Zones
- **ALB**: Configurado en múltiples AZs
- **RDS**: Multi-AZ (mantenido)

**Beneficios**:
- ✅ Resiliencia ante fallos de una Availability Zone
- ✅ Continuidad de servicio
- ✅ Distribución geográfica de carga
- ✅ Cumplimiento de requisitos de alta disponibilidad

**Configuración**:
- Subnets privadas en múltiples AZs (mínimo 2)
- Auto Scaling Groups configurados para usar múltiples subnets
- ALB configurado en múltiples AZs

#### 4. Monitoreo con CloudWatch (Mejora Continua)

**Antes (Entrega 3)**:
- **Monitoreo**: Básico, posiblemente logs locales
- **Métricas**: Limitadas a instancias EC2
- **Alarms**: No configurados para auto-scaling

**Ahora (Entrega 4)**:
- **CloudWatch**: Monitoreo completo del sistema
- **Métricas**: SQS, EC2, ALB, RDS
- **Alarms**: Configurados para auto-scaling de workers y backend
- **Dashboards**: Visualización de métricas clave

**Beneficios**:
- ✅ Visibilidad completa del sistema
- ✅ Alertas proactivas
- ✅ Métricas para toma de decisiones
- ✅ Integración con Auto Scaling

### Comparativa de Arquitectura

#### Entrega 3
```
Internet → ALB → Backend (ASG) → RDS
                    ↓
                 Redis (EC2) → Worker (EC2 fijo)
                    ↓
                   S3
```

#### Entrega 4
```
Internet → ALB (Multi-AZ) → Backend (ASG, Multi-AZ) → RDS (Multi-AZ)
                    ↓
                  SQS → Workers (ASG, Multi-AZ, Auto-Scaling)
                    ↓
                   S3
```

---

## 📊 Especificaciones Técnicas

### Instancias EC2

Según los requisitos de la entrega, todas las instancias deben cumplir:
- **vCPU**: 2
- **RAM**: 2 GiB
- **Almacenamiento**: 30 GiB

**Tipo de instancia**: `t3.small` (2 vCPU, 2 GiB RAM)

### Capacidad de Auto Scaling

#### Backend ASG
- **Mínimo**: 2 instancias
- **Máximo**: 3 instancias
- **Deseado**: 2 instancias
- **Availability Zones**: Mínimo 2

#### Worker ASG
- **Mínimo**: 1 instancia
- **Máximo**: 3 instancias
- **Deseado**: 1 instancia
- **Availability Zones**: Mínimo 2

### Políticas de Escalamiento

#### Backend
- **Tipo**: Target Tracking
- **Métrica**: `RequestCountPerTarget` (ALB) o `CPUUtilization`
- **Target Value**: 100 requests/min por instancia (o 70% CPU)

#### Workers
- **Tipo**: Target Tracking
- **Métrica**: `ApproximateNumberOfMessagesVisible` (SQS)
- **Target Value**: 10 mensajes por instancia

---

## 🔐 Seguridad

### IAM Roles

#### anb-backend-role
- **Permisos SQS**: `SendMessage`, `GetQueueAttributes`, `GetQueueUrl`
- **Permisos S3**: `PutObject`, `DeleteObject`, `ListBucket`

#### anb-worker-role
- **Permisos SQS**: `ReceiveMessage`, `DeleteMessage`, `GetQueueAttributes`, `GetQueueUrl`
- **Permisos S3**: `GetObject`, `PutObject`, `ListBucket`
- **Permisos CloudWatch**: `PutMetricData`

### Security Groups

- **anb-alb-sg**: Permite HTTP (80) y HTTPS (443) desde Internet
- **anb-backend-sg**: Permite tráfico desde ALB (puerto 8000) y SSH desde IP específica
- **anb-worker-sg**: Permite SSH desde IP específica
- **anb-rds-sg**: Permite PostgreSQL (5432) desde backend y workers

---

## 📈 Flujo de Procesamiento de Videos

### Flujo Completo

1. **Usuario sube video**:
   - Cliente → ALB → Backend (FastAPI)
   - Backend valida autenticación (JWT)
   - Backend sube video a S3 (`uploads/`)
   - Backend crea registro en PostgreSQL
   - Backend envía mensaje a SQS con `video_id` y `video_path`

2. **Worker procesa video**:
   - Worker hace polling de SQS (long polling, 20s)
   - Worker recibe mensaje
   - Worker descarga video desde S3
   - Worker procesa video (MoviePy):
     - Recorte a 30 segundos
     - Redimensionamiento a 720p
     - Adición de watermark ANB
   - Worker sube video procesado a S3 (`processed_videos/`)
   - Worker actualiza estado en PostgreSQL
   - Worker elimina mensaje de SQS

3. **Usuario consulta video**:
   - Cliente → ALB → Backend
   - Backend consulta PostgreSQL
   - Backend retorna URL pública de S3 (`processed_url`)

### Manejo de Errores

- **Dead Letter Queue**: Mensajes que fallan 3 veces se mueven a DLQ
- **Retry Logic**: SQS Visibility Timeout permite reintentos automáticos
- **Error Handling**: Workers registran errores y actualizan estado en BD

---

## 🎯 Cumplimiento de Requisitos de la Entrega 4

### Actividad 3: Auto Scaling de Workers (20%)
- ✅ Auto Scaling Group configurado para workers
- ✅ Política de Target Tracking basada en profundidad de cola SQS
- ✅ Escalamiento automático cuando hay mensajes en cola
- ✅ Reducción automática cuando la cola está vacía

### Actividad 4: SQS/Kinesis (20%)
- ✅ Amazon SQS configurado como sistema de mensajería
- ✅ Backend envía mensajes a SQS cuando se sube un video
- ✅ Workers consumen mensajes de SQS
- ✅ Dead Letter Queue configurada para manejo de errores

### Actividad 5: Alta Disponibilidad (20%)
- ✅ Backend desplegado en mínimo 2 Availability Zones
- ✅ Workers desplegados en mínimo 2 Availability Zones
- ✅ RDS Multi-AZ habilitado
- ✅ ALB configurado en múltiples AZs

### Actividad 6: Requerimientos Funcionales (10%)
- ✅ Autenticación de usuarios funcionando
- ✅ Subida de videos funcionando
- ✅ Procesamiento asíncrono funcionando
- ✅ Consulta de videos funcionando
- ✅ Votación de videos funcionando
- ✅ URLs públicas de videos funcionando

---

## 📚 Referencias

- **Guía de Despliegue**: [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)
- **Plan de Migración**: [MIGRATION_PLAN.md](MIGRATION_PLAN.md)
- **Guía de Migración SQS**: [SQS_MIGRATION_GUIDE.md](SQS_MIGRATION_GUIDE.md)
- **Documentación Entrega 3**: [../Entrega_3/AWS_DEPLOYMENT_GUIDE.md](../Entrega_3/AWS_DEPLOYMENT_GUIDE.md)

---

## 📝 Notas Finales

Esta arquitectura está diseñada para:
- **Escalabilidad**: Auto-scaling automático según demanda
- **Alta Disponibilidad**: Despliegue en múltiples Availability Zones
- **Resiliencia**: Manejo de errores con Dead Letter Queue
- **Observabilidad**: Monitoreo completo con CloudWatch
- **Costo-eficiencia**: Escalamiento hacia abajo cuando no hay carga

La migración de Celery/Redis a SQS permite una arquitectura más escalable y gestionada, mientras que el auto-scaling de workers garantiza que el sistema pueda manejar picos de carga sin intervención manual.

