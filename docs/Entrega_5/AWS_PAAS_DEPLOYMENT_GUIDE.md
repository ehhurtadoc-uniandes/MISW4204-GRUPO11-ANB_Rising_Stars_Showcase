# Guía de Despliegue en PaaS (AWS Lambda/ECS) - Entrega 5

## 📋 Resumen

Esta guía te llevará paso a paso para migrar la aplicación de un modelo IaaS (EC2) a un modelo PaaS utilizando **AWS Lambda** o **Amazon ECS (Fargate)**, cumpliendo con los requisitos de la Entrega 5.

**Requisitos de la Entrega 5:**
- ✅ **Actividad 1 (20%)**: Capa web en Lambda o ECS
- ✅ **Actividad 2 (20%)**: Capa worker en Lambda o ECS
- ✅ **Actividad 3 (10%)**: Base de datos RDS configurada
- ✅ **Actividad 4 (10%)**: Sistema de mensajería (SQS/SNS/Kinesis)
- ✅ **Actividad 5 (10%)**: Almacenamiento S3
- ✅ **Actividad 6 (10%)**: Requerimientos funcionales completos

**Opciones de Despliegue:**
- **Opción A: AWS Lambda** (Recomendada para capa web) - Serverless, sin gestión de servidores
- **Opción B: Amazon ECS Fargate** (Recomendada para workers) - Contenedores sin gestión de servidores

**Servicios AWS utilizados:**
- **AWS Lambda**: Funciones serverless (capa web)
- **Amazon ECS (Fargate)**: Contenedores sin gestión de servidores (workers)
- **Amazon RDS**: Base de datos PostgreSQL administrada
- **Amazon S3**: Almacenamiento de videos
- **Amazon SQS**: Mensajería asíncrona entre web y workers
- **API Gateway**: Punto de entrada para Lambda (capa web)
- **Amazon CloudWatch**: Monitoreo y logs

---

## ⚠️ IMPORTANTE: Cuentas de Estudiante y Permisos Restringidos

Si estás usando una cuenta de estudiante (voclabs) con permisos restringidos:

### Problemas Comunes

1. **No puedes crear ECR Repository**: Si no tienes permisos para crear ECR, usa **Lambda** (no requiere ECR)
2. **LabRole**: Debes usar `LabRole` como rol de ejecución
3. **Límites de Lambda**: Máximo 10 instancias concurrentes en cuentas de estudiante
4. **ECS Service Linked Role**: Si aparece el error "the ECS service linked role could not be assumed", regresa y vuelve a intentar

### Recomendación de Arquitectura (Sin ECR)

**Si NO puedes crear ECR, usa esta arquitectura:**

- **Capa Web**: **AWS Lambda** con API Gateway
  - ✅ No requiere ECR
  - ✅ Deployment package como ZIP (hasta 50 MB)
  - ✅ Serverless puro, sin gestión de servidores
  - ✅ Escalado automático
  - ⚠️ Límite: 10 instancias concurrentes en cuentas de estudiante

- **Capa Worker**: **AWS Lambda** con SQS Trigger
  - ✅ No requiere ECR
  - ✅ Deployment package como ZIP
  - ✅ Trigger automático desde SQS
  - ⚠️ Límite de tiempo: 15 minutos máximo (suficiente para procesar videos)
  - ⚠️ Límite: 10 instancias concurrentes

**Alternativa si necesitas más tiempo para workers:**
- **Capa Worker**: **ECS Fargate con imagen pública de Docker Hub**
  - ✅ No requiere ECR (usa Docker Hub público)
  - ✅ Sin límites de tiempo
  - ⚠️ Requiere permisos para crear ECS Cluster (mínimo)

**Nota sobre ECS Clusters**: ECS Fargate requiere un "cluster" pero es solo un contenedor lógico. No necesitas gestionar servidores EC2, solo creas el cluster y AWS gestiona todo automáticamente.

---

## Arquitectura PaaS

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │    Balancer (ALB)   │
              └──────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │   ECS Cluster (Web Layer)          │
        │   Launch Type: Fargate             │
        │  ┌──────────┐  ┌──────────┐       │
        │  │  Task    │  │  Task    │       │
        │  │  (API)  │  │  (API)  │       │
        │  └──────────┘  └──────────┘       │
        │   Auto Scaling Enabled           │
        └────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   SQS     │   │   S3    │
   │PostgreSQL│    │  Queue    │   │ Bucket  │
   │(db.t3.micro)│    │           │   │         │
   └─────────┘    └──────────┘   └─────────┘
        │                │               
        │                │               
        ▼                ▼               
   ┌────────────────────────────────────┐
   │   ECS Cluster (Worker Layer)      │
   │   Launch Type: Fargate             │
   │  ┌──────────┐  ┌──────────┐       │
   │  │  Task    │  │  Task    │       │
   │  │ (Worker) │  │ (Worker) │       │
   │  └──────────┘  └──────────┘       │
   │   Auto Scaling Enabled            │
   └────────────────────────────────────┘
```

### Componentes

- **ECS Cluster (Web)**: Contenedores FastAPI ejecutándose en Fargate
- **ECS Cluster (Workers)**: Contenedores worker procesando mensajes SQS
- **Application Load Balancer**: Distribuye tráfico a tareas web
- **RDS PostgreSQL**: Base de datos administrada
- **Amazon SQS**: Cola de mensajes para procesamiento asíncrono
- **Amazon S3**: Almacenamiento de videos originales y procesados
- **CloudWatch**: Monitoreo, logs y métricas

---

## Prerrequisitos

- ✅ Cuenta de AWS activa
- ✅ AWS CLI instalado y configurado (`aws configure`)
- ✅ Docker instalado localmente (para construir imágenes)
- ✅ ECR Repository creado (o permisos para crearlo)
- ✅ VPC y subnets configuradas (puedes reutilizar de Entrega 4)
- ✅ RDS, S3, SQS ya configurados (de Entrega 4)

---

## Configuración Paso a Paso

Esta guía ofrece dos opciones:
- **Opción A: Lambda para Web + ECS para Workers** (Recomendada)
- **Opción B: ECS para Web + ECS para Workers**

---

## Opción A: Lambda para Capa Web + Lambda para Workers (Recomendada si NO tienes ECR)

**Esta opción NO requiere ECR** - Ideal para cuentas de estudiante con permisos restringidos.

### Paso 1: Preparar FastAPI para Lambda

FastAPI necesita un adaptador para funcionar con Lambda. Usaremos **Mangum**.

#### 1.1 Instalar Mangum

Agrega `mangum` a `requirements.txt`:

```bash
echo "mangum>=0.17.0" >> requirements.txt
```

#### 1.2 Crear Handler Lambda

Crea un archivo `lambda_handler.py` en la raíz del proyecto:

```python
from mangum import Mangum
from app.main import app

# Crear handler Lambda
handler = Mangum(app, lifespan="off")
```

#### 1.3 Crear Deployment Package

```bash
# Crear directorio para Lambda
mkdir -p lambda-package

# Instalar dependencias en el directorio
pip install -r requirements.txt -t lambda-package/

# Copiar código de la aplicación
cp -r app lambda-package/
cp lambda_handler.py lambda-package/

# Crear ZIP
cd lambda-package
zip -r ../lambda-deployment.zip .
cd ..
```

**Nota**: El ZIP no debe exceder 50 MB (250 MB descomprimido). Si es muy grande, considera usar Lambda Layers o ECR para contenedores.

### Paso 2: Crear Función Lambda

#### 2.1 Crear Función desde ZIP

1. **Lambda Dashboard** → **Functions** → **Create function**
2. Configuración:
   - **Function name**: `anb-api-lambda`
   - **Runtime**: Python 3.12
   - **Architecture**: x86_64
   - **Execution role**: `LabRole` (o crear uno nuevo con permisos para RDS, S3, SQS)
3. Click **Create function**

#### 2.2 Subir Código

1. En la función Lambda, **Code** → **Upload from** → **.zip file**
2. Sube `lambda-deployment.zip`
3. **Handler**: `lambda_handler.handler`

#### 2.3 Configurar Variables de Entorno

En **Configuration** → **Environment variables**, agrega:

```
DATABASE_URL=postgresql://anb_admin:PASSWORD@RDS_ENDPOINT:5432/anb_db
POSTGRES_HOST=RDS_ENDPOINT
POSTGRES_PORT=5432
POSTGRES_USER=anb_admin
POSTGRES_PASSWORD=PASSWORD
POSTGRES_DB=anb_db
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/anb-video-processing-queue
SQS_REGION=us-east-1
SECRET_KEY=TU_SECRET_KEY
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-stars-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/
ENVIRONMENT=production
DEBUG=False
```

#### 2.4 Configurar Timeout y Memoria

- **Timeout**: 30 segundos (máximo 15 minutos, pero para API REST 30s es suficiente)
- **Memory**: 512 MB (ajustar según necesidad)

### Paso 3: Crear API Gateway

#### 3.1 Crear REST API

1. **API Gateway Dashboard** → **APIs** → **Create API**
2. Seleccionar **REST API** → **Build**
3. Configuración:
   - **Protocol**: REST
   - **Create new API**: New API
   - **API name**: `anb-api-gateway`
   - **Endpoint Type**: Regional
4. Click **Create API**

#### 3.2 Crear Resource y Method

1. **Actions** → **Create Resource**
   - **Resource Name**: `{proxy+}`
   - **Resource Path**: `{proxy+}`
   - **Enable API Gateway CORS**: Sí
2. Click **Create Resource**

3. Con el resource `{proxy+}` seleccionado, **Actions** → **Create Method** → **ANY**
   - **Integration type**: Lambda Function
   - **Lambda Function**: `anb-api-lambda`
   - **Use Lambda Proxy integration**: Sí
4. Click **Save** → **OK** (permiso para invocar Lambda)

#### 3.3 Configurar CORS (si es necesario)

1. Seleccionar `{proxy+}` → **Actions** → **Enable CORS**
2. Configurar headers permitidos
3. Click **Enable CORS and replace existing CORS headers**

#### 3.4 Desplegar API

1. **Actions** → **Deploy API**
2. Configuración:
   - **Deployment stage**: `prod` (o crear uno nuevo)
   - **Stage name**: `prod`
3. Click **Deploy**

**Nota**: Anota la **Invoke URL** (ej: `https://abc123.execute-api.us-east-1.amazonaws.com/prod`)

### Paso 4: Configurar Workers en Lambda (SQS Trigger)

#### 4.1 Crear Lambda Handler para Worker

Crea `lambda_worker_handler.py` en la raíz del proyecto:

```python
"""
Lambda handler para SQS Worker
Procesa mensajes de SQS para procesar videos

Nota: Lambda elimina automáticamente los mensajes de SQS si la función
se ejecuta exitosamente. Si la función falla, el mensaje vuelve a la cola.
"""
import json
import logging
from app.workers.sqs_worker import process_video

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Handler Lambda que procesa mensajes de SQS
    
    Args:
        event: Evento de SQS con Records
        context: Contexto de Lambda
        
    Nota: Si la función completa exitosamente, Lambda elimina automáticamente
    los mensajes de SQS. Si falla, los mensajes vuelven a la cola para retry.
    """
    logger.info(f"Received {len(event.get('Records', []))} messages from SQS")
    
    processed_count = 0
    failed_count = 0
    
    for record in event.get('Records', []):
        try:
            # Parsear el body del mensaje SQS
            message_body = json.loads(record['body'])
            video_id = message_body.get('video_id')
            video_path = message_body.get('video_path')
            task_id = message_body.get('task_id', 'unknown')
            
            if not video_id or not video_path:
                logger.error(f"Invalid message format: missing video_id or video_path")
                failed_count += 1
                continue
            
            logger.info(f"Processing video {video_id} (task: {task_id})")
            
            # Procesar el video directamente
            success = process_video(video_id, video_path)
            
            if success:
                processed_count += 1
                logger.info(f"Successfully processed video {video_id}")
            else:
                # Si falla, lanzar excepción para que Lambda no elimine el mensaje
                # y SQS lo reintente automáticamente
                failed_count += 1
                raise Exception(f"Failed to process video {video_id}")
                
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            failed_count += 1
            # Re-lanzar la excepción para que Lambda no elimine el mensaje
            raise
    
    # Si llegamos aquí, todos los mensajes se procesaron exitosamente
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'failed': failed_count,
            'total': len(event.get('Records', []))
        })
    }
```

#### 4.2 Crear Deployment Package para Worker

**Nota**: El archivo `lambda_worker_handler.py` ya está creado en la raíz del proyecto.

```bash
# Crear directorio para Lambda Worker
mkdir -p lambda-worker-package
cd lambda-worker-package

# Instalar dependencias
pip install -r ../requirements.txt -t .

# Copiar código de la aplicación
cp -r ../app .
cp ../lambda_worker_handler.py .

# Crear ZIP
zip -r ../lambda-worker-deployment.zip .
cd ..
```

**Verificar tamaño**:
```bash
du -sh lambda-worker-deployment.zip
# Si es > 50 MB, considera usar Lambda Layers para dependencias grandes
```

#### 4.3 Crear Función Lambda para Worker

1. **Lambda Dashboard** → **Functions** → **Create function**
2. Configuración:
   - **Function name**: `anb-worker-lambda`
   - **Runtime**: Python 3.12
   - **Architecture**: x86_64
   - **Execution role**: `LabRole` (mismo que API)
3. Click **Create function**

#### 4.4 Subir Código y Configurar

1. **Code** → **Upload from** → **.zip file**
2. Sube `lambda-worker-deployment.zip`
3. **Handler**: `lambda_worker_handler.handler`
4. **Configuration** → **General configuration** → **Edit**:
   - **Timeout**: 900 segundos (15 minutos máximo - suficiente para procesar videos)
   - **Memory**: 3008 MB (máximo para procesamiento de video)
   - **Ephemeral storage**: 10240 MB (10 GB para videos temporales)

#### 4.5 Configurar Variables de Entorno

Mismas que la API, excepto que no necesita `SQS_QUEUE_URL` (lo recibe del trigger):

```
DATABASE_URL=postgresql://anb_admin:PASSWORD@RDS_ENDPOINT:5432/anb_db
POSTGRES_HOST=RDS_ENDPOINT
POSTGRES_PORT=5432
POSTGRES_USER=anb_admin
POSTGRES_PASSWORD=PASSWORD
POSTGRES_DB=anb_db
SQS_REGION=us-east-1
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-stars-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/
ENVIRONMENT=production
DEBUG=False
```

#### 4.6 Configurar SQS Trigger

1. **Lambda Function** → **Add trigger**
2. Configuración:
   - **Source**: SQS
   - **SQS queue**: `anb-video-processing-queue`
   - **Batch size**: 1 (procesar un mensaje a la vez)
   - **Batch window**: 0 segundos
3. Click **Add**

**Nota**: Lambda procesará automáticamente los mensajes de SQS. No necesitas polling manual.

---

## Opción B: ECS para Capa Web + ECS para Workers (Requiere ECR)

**⚠️ Esta opción requiere permisos para crear ECR Repository. Si no tienes permisos, usa la Opción A (Lambda).**

### Paso 1: Preparar Imagen Docker y Subir a ECR

#### 1.1 Crear ECR Repository

1. **ECR Dashboard** → **Repositories** → **Create repository**
2. Configuración:
   - **Repository name**: `anb-rising-stars-api`
   - **Visibility**: Private
   - **Tag immutability**: Habilitar (opcional, recomendado)
   - **Scan on push**: Habilitar (opcional, para seguridad)
3. Click **Create repository**

#### 1.2 Autenticar Docker con ECR

```bash
# Obtener token de autenticación
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Reemplazar <ACCOUNT_ID> con tu Account ID de AWS
```

#### 1.3 Construir y Subir Imagen

```bash
# Desde el directorio raíz del proyecto
docker build -t anb-rising-stars-api:latest .

# Tag para ECR
docker tag anb-rising-stars-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-rising-stars-api:latest

# Push a ECR
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-rising-stars-api:latest
```

**Nota**: Anota el URI completo de la imagen (ej: `123456789.dkr.ecr.us-east-1.amazonaws.com/anb-rising-stars-api:latest`)

---

### Paso 2: Crear ECS Cluster

#### 2.1 Crear Cluster

1. **ECS Dashboard** → **Clusters** → **Create cluster**
2. Configuración:
   - **Cluster name**: `anb-rising-stars-cluster`
   - **Infrastructure**: **AWS Fargate** (Serverless)
   - **Container Insights**: Habilitar (opcional, para monitoreo avanzado)
3. Click **Create**

**⏱️ Tiempo estimado**: 1-2 minutos

---

### Paso 3: Crear Task Definitions

#### 3.1 Task Definition para API (Web Layer)

1. **ECS Dashboard** → **Task definitions** → **Create new task definition**
2. Configuración:
   - **Task definition family**: `anb-api-task`
   - **Launch type**: **Fargate**
   - **Operating system/Architecture**: Linux/X86_64
   - **Task size**:
     - **CPU**: 0.5 vCPU (512)
     - **Memory**: 1 GB (1024)
   - **Task role**: `LabRole` (o el rol que tengas disponible)
   - **Task execution role**: `LabRole` (o `ecsTaskExecutionRole` si existe)

3. **Container definitions** → **Add container**:
   - **Container name**: `anb-api`
   - **Image URI**: `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-rising-stars-api:latest`
   - **Port mappings**:
     - **Container port**: `8000`
     - **Protocol**: `TCP`
   - **Environment variables** (agregar todas las necesarias):
     ```
     DATABASE_URL=postgresql://anb_admin:PASSWORD@RDS_ENDPOINT:5432/anb_db
     POSTGRES_HOST=RDS_ENDPOINT
     POSTGRES_PORT=5432
     POSTGRES_USER=anb_admin
     POSTGRES_PASSWORD=PASSWORD
     POSTGRES_DB=anb_db
     SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/anb-video-processing-queue
     SQS_REGION=us-east-1
     SECRET_KEY=TU_SECRET_KEY
     STORAGE_TYPE=cloud
     AWS_REGION=us-east-1
     S3_BUCKET_NAME=anb-rising-stars-videos-east1
     S3_UPLOAD_PREFIX=uploads/
     S3_PROCESSED_PREFIX=processed_videos/
     ENVIRONMENT=production
     DEBUG=False
     ```
   - **Logging**:
     - **Log driver**: `awslogs`
     - **Log group**: `/ecs/anb-api` (se creará automáticamente)
     - **Log stream prefix**: `api`

4. Click **Create**

#### 3.2 Task Definition para Workers

1. **ECS Dashboard** → **Task definitions** → **Create new task definition**
2. Configuración:
   - **Task definition family**: `anb-worker-task`
   - **Launch type**: **Fargate**
   - **Operating system/Architecture**: Linux/X86_64
   - **Task size**:
     - **CPU**: 1 vCPU (1024) - Más CPU para procesamiento de video
     - **Memory**: 2 GB (2048) - Más memoria para MoviePy/FFmpeg
   - **Task role**: `LabRole`
   - **Task execution role**: `LabRole`

3. **Container definitions** → **Add container**:
   - **Container name**: `anb-worker`
   - **Image URI**: `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-rising-stars-api:latest`
   - **Command override**: `python -m app.workers.sqs_worker`
   - **Environment variables** (mismas que API, excepto que no necesita SQS_QUEUE_URL para enviar, solo recibir)
   - **Logging**:
     - **Log driver**: `awslogs`
     - **Log group**: `/ecs/anb-worker`
     - **Log stream prefix**: `worker`

4. Click **Create**

**Nota**: Si prefieres usar **Secrets Manager** o **Parameter Store** para credenciales, puedes configurarlo en lugar de variables de entorno.

---

### Paso 4: Crear Application Load Balancer (si no existe)

Si ya tienes un ALB de la Entrega 4, puedes reutilizarlo. Si no:

1. **EC2 Dashboard** → **Load Balancers** → **Create Load Balancer**
2. Seleccionar **Application Load Balancer**
3. Configuración:
   - **Name**: `anb-alb-paas`
   - **Scheme**: Internet-facing
   - **IP address type**: IPv4
   - **VPC**: Tu VPC
   - **Mappings**: Seleccionar al menos 2 AZs con subnets públicas
   - **Security groups**: `anb-alb-sg` (o crear uno nuevo)
   - **Listeners**: HTTP en puerto 80
   - **Default action**: Crear nuevo target group (se configurará después)
4. Click **Create load balancer**

**⏱️ Tiempo estimado**: 2-5 minutos

---

### Paso 5: Crear Target Group para API

1. **EC2 Dashboard** → **Target Groups** → **Create target group**
2. Configuración:
   - **Target type**: **IP addresses** (para Fargate)
   - **Name**: `anb-api-tg-paas`
   - **Protocol**: HTTP
   - **Port**: 8000
   - **VPC**: Tu VPC
   - **Health checks**:
     - **Health check protocol**: HTTP
     - **Health check path**: `/health`
     - **Healthy threshold**: 2
     - **Unhealthy threshold**: 3
     - **Timeout**: 5
     - **Interval**: 30
3. Click **Create target group**

**Nota**: Los targets (IPs de las tareas) se agregarán automáticamente cuando crees el servicio ECS.

---

### Paso 6: Crear ECS Service para API (Web Layer)

1. **ECS Dashboard** → **Clusters** → `anb-rising-stars-cluster` → **Services** → **Create**
2. Configuración:
   - **Launch type**: **Fargate**
   - **Task definition**: `anb-api-task` (última revisión)
   - **Cluster**: `anb-rising-stars-cluster`
   - **Service name**: `anb-api-service`
   - **Number of tasks**: `2` (para alta disponibilidad)
   - **VPC**: Tu VPC
   - **Subnets**: Seleccionar subnets privadas (al menos 2 AZs)
   - **Security groups**: `anb-backend-sg` (o uno que permita tráfico del ALB en puerto 8000)
   - **Auto-assign public IP**: **DISABLED** (usa NAT Gateway para salida a internet)
   - **Load balancing**:
     - **Load balancer type**: Application Load Balancer
     - **Load balancer name**: `anb-alb-paas`
     - **Target group name**: `anb-api-tg-paas`
     - **Container to load balance**: `anb-api:8000`
   - **Service auto scaling** (opcional, pero recomendado):
     - **Configure Service Auto Scaling**: Habilitar
     - **Min capacity**: 2
     - **Max capacity**: 5
     - **Target tracking scaling policy**:
       - **Metric type**: ALBRequestCountPerTarget
       - **Target value**: 100 requests/minuto por tarea
3. Click **Create**

**⏱️ Tiempo estimado**: 5-10 minutos (para que las tareas estén en estado RUNNING)

---

### Paso 7: Crear ECS Service para Workers

1. **ECS Dashboard** → **Clusters** → `anb-rising-stars-cluster` → **Services** → **Create**
2. Configuración:
   - **Launch type**: **Fargate**
   - **Task definition**: `anb-worker-task` (última revisión)
   - **Cluster**: `anb-rising-stars-cluster`
   - **Service name**: `anb-worker-service`
   - **Number of tasks**: `1` (mínimo)
   - **VPC**: Tu VPC
   - **Subnets**: Seleccionar subnets privadas (al menos 2 AZs)
   - **Security groups**: `anb-worker-sg`
   - **Auto-assign public IP**: **DISABLED**
   - **Load balancing**: **No** (workers no necesitan load balancer)
   - **Service auto scaling** (opcional, pero recomendado):
     - **Configure Service Auto Scaling**: Habilitar
     - **Min capacity**: 1
     - **Max capacity**: 3
     - **Target tracking scaling policy**:
       - **Metric type**: Custom metric
       - **Metric**: `ApproximateNumberOfMessagesVisible` de SQS
       - **Target value**: 10 mensajes por tarea
3. Click **Create**

**⏱️ Tiempo estimado**: 5-10 minutos

---

### Paso 8: Configurar Listener del ALB

1. **EC2 Dashboard** → **Load Balancers** → Seleccionar `anb-alb-paas`
2. **Listeners** → Seleccionar listener HTTP:80 → **View/edit rules**
3. Agregar regla:
   - **Priority**: 100
   - **Conditions**: `Path is /api/*` o `Path is /*` (para todo el tráfico)
   - **Actions**: Forward to `anb-api-tg-paas`

---

### Paso 9: Verificar Despliegue

#### 9.1 Verificar Tareas ECS

1. **ECS Dashboard** → **Clusters** → `anb-rising-stars-cluster` → **Tasks**
2. Verificar que las tareas estén en estado **RUNNING**
3. Verificar que los health checks estén **healthy**

#### 9.2 Verificar Logs

1. **CloudWatch** → **Log groups** → `/ecs/anb-api` y `/ecs/anb-worker`
2. Verificar que no haya errores de conexión a RDS, SQS o S3

#### 9.3 Probar API

```bash
# Obtener DNS del ALB
ALB_DNS=anb-alb-paas-123456789.us-east-1.elb.amazonaws.com

# Health check
curl http://$ALB_DNS/health

# Documentación
curl http://$ALB_DNS/docs
```

#### 9.4 Probar Flujo Completo

1. **Subir video**:
   ```bash
   # Obtener token de autenticación
   TOKEN=$(curl -X POST http://$ALB_DNS/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"usuario@example.com","password":"password"}' | jq -r .access_token)
   
   # Subir video
   curl -X POST http://$ALB_DNS/api/videos/upload \
     -H "Authorization: Bearer $TOKEN" \
     -F "title=Test Video" \
     -F "video_file=@test.mp4"
   ```

2. **Verificar mensaje en SQS**:
   ```bash
   aws sqs get-queue-attributes \
     --queue-url $SQS_QUEUE_URL \
     --attribute-names ApproximateNumberOfMessages
   ```

3. **Verificar logs del worker**:
   - CloudWatch → `/ecs/anb-worker` → Verificar que procese el mensaje

4. **Verificar video procesado en S3**:
   ```bash
   aws s3 ls s3://anb-rising-stars-videos-east1/processed_videos/
   ```

---

## Configuración Avanzada

### Auto Scaling Basado en SQS (Workers)

Para escalar workers basado en profundidad de cola SQS:

1. **ECS Dashboard** → **Clusters** → `anb-rising-stars-cluster` → **Services** → `anb-worker-service`
2. **Auto Scaling** → **Create Auto Scaling policy**
3. Configuración:
   - **Policy type**: Target tracking
   - **Metric**: Custom metric
   - **Metric specification**:
     ```json
     {
       "CustomizedMetricSpecification": {
         "MetricName": "ApproximateNumberOfMessagesVisible",
         "Namespace": "AWS/SQS",
         "Statistic": "Average",
         "Dimensions": [
           {
             "Name": "QueueName",
             "Value": "anb-video-processing-queue"
           }
         ]
       }
     }
     ```
   - **Target value**: 10 (mensajes por tarea)
   - **Scale-in cooldown**: 300 segundos
   - **Scale-out cooldown**: 60 segundos

### Usar Secrets Manager para Credenciales

En lugar de variables de entorno, puedes usar AWS Secrets Manager:

1. **Secrets Manager** → **Store a new secret**
2. Seleccionar **Other type of secret**
3. Agregar pares clave-valor (ej: `DATABASE_URL`, `POSTGRES_PASSWORD`, etc.)
4. **Secret name**: `anb-app-secrets`
5. En la Task Definition, en lugar de Environment variables, usar **Secrets**:
   - **Value from**: `arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:anb-app-secrets-XXXXX`
   - **Key**: `DATABASE_URL` (o el nombre de la clave en el secret)

---

## Troubleshooting

### Las tareas no inician (PENDING)

- **Verificar**: Task execution role tiene permisos para ECR, CloudWatch Logs
- **Verificar**: Subnets tienen NAT Gateway para descargar imagen de ECR
- **Verificar**: Security groups permiten tráfico necesario

### Health checks fallan

- **Verificar**: Target group apunta al puerto correcto (8000)
- **Verificar**: Security group del ALB permite tráfico a las tareas
- **Verificar**: La aplicación responde en `/health`

### Workers no procesan mensajes

- **Verificar**: Task role tiene permisos para SQS (`ReceiveMessage`, `DeleteMessage`)
- **Verificar**: `SQS_QUEUE_URL` está configurado correctamente
- **Verificar**: Logs en CloudWatch para errores específicos

### Errores de conexión a RDS

- **Verificar**: Security group de RDS permite tráfico desde security group de las tareas
- **Verificar**: `DATABASE_URL` está correcto en variables de entorno
- **Verificar**: RDS está en la misma VPC

---

## Checklist de Entrega

### Actividad 1: Capa Web en ECS (20%)
- [ ] ECS Cluster creado
- [ ] Task Definition para API creada
- [ ] ECS Service para API desplegado
- [ ] ALB configurado y funcionando
- [ ] API responde a solicitudes HTTP

### Actividad 2: Capa Worker en ECS (20%)
- [ ] Task Definition para Workers creada
- [ ] ECS Service para Workers desplegado
- [ ] Workers consumen mensajes de SQS
- [ ] Procesamiento de videos funcionando

### Actividad 3: Base de Datos RDS (10%)
- [ ] Instancia RDS configurada (db.t3.micro)
- [ ] Aplicación conectada a RDS
- [ ] Migraciones ejecutadas
- [ ] Datos persisten correctamente

### Actividad 4: Sistema de Mensajería (10%)
- [ ] SQS configurado
- [ ] Aplicación envía mensajes a SQS
- [ ] Workers consumen mensajes de SQS
- [ ] Flujo completo funcionando

### Actividad 5: Almacenamiento S3 (10%)
- [ ] Bucket S3 configurado
- [ ] Aplicación sube videos a S3
- [ ] Videos procesados se guardan en S3
- [ ] URLs públicas funcionando

### Actividad 6: Requerimientos Funcionales (10%)
- [ ] Autenticación funcionando
- [ ] Subida de videos funcionando
- [ ] Procesamiento asíncrono funcionando
- [ ] Consulta de videos funcionando
- [ ] Votación funcionando

---

## Costos Estimados (Mensual)

- **ECS Fargate (API)**: ~$15-30/mes (2-5 tareas, 0.5 vCPU, 1 GB)
- **ECS Fargate (Workers)**: ~$30-90/mes (1-3 tareas, 1 vCPU, 2 GB)
- **RDS (db.t3.micro)**: ~$15/mes
- **ALB**: ~$16/mes
- **S3**: ~$5-20/mes
- **SQS**: ~$0.40 por millón de requests
- **CloudWatch Logs**: ~$5-10/mes
- **Total estimado**: ~$85-190/mes

**Nota**: Detén los servicios cuando no los uses para optimizar costos.

---

## Siguiente Paso

Una vez completado el despliegue, consulta:
- **[Arquitectura PaaS](ARQUITECTURA_PAAS.md)** para entender la arquitectura completa
- **[Plan de Migración](MIGRATION_PLAN_PAAS.md)** para comparar IaaS vs PaaS

