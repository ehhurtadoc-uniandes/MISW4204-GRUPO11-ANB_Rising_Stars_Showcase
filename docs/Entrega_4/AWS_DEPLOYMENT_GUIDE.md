# Guía de Despliegue en AWS - Entrega 4: Escalabilidad y Alta Disponibilidad

## 📋 Resumen

Esta guía te llevará paso a paso para implementar **desde cero** una arquitectura escalable y de alta disponibilidad en AWS para el sistema ANB Rising Stars Showcase.

**Características principales:**
- ✅ **Amazon SQS** para mensajería asíncrona entre web y workers
- ✅ **Auto Scaling** para Backend y Workers basado en métricas
- ✅ **Alta Disponibilidad** desplegando en múltiples Availability Zones
- ✅ **CloudWatch** para monitoreo completo del sistema
- ✅ **RDS Multi-AZ** para alta disponibilidad de base de datos
- ✅ **S3** para almacenamiento de videos

---

## ⚠️ IMPORTANTE: Cuentas de Estudiante / Permisos Restringidos

Si estás usando una **cuenta de estudiante** (como voclabs) o una cuenta con permisos restringidos, es posible que no puedas crear ciertos recursos directamente desde la consola.

### 📋 Requisitos de la Entrega 4

Según los requisitos, **DEBES** implementar:
- ✅ **SQS o Kinesis** (20%): Sistema de mensajería asíncrona
- ✅ **Auto Scaling para Workers** (20%): Basado en cola de mensajes
- ✅ **Alta Disponibilidad** (20%): Múltiples Availability Zones

### 🎯 Estrategia si No Puedes Crear SQS

**Opción 1: Solicitar al Administrador (RECOMENDADO)**

Solicita al administrador que cree las colas SQS. Esto es lo más directo y cumple con los requisitos.

**Opción 2: Usar Kinesis como Alternativa**

Si no puedes crear SQS pero puedes crear Kinesis, puedes usar Kinesis Data Streams. Ver sección [Alternativa: Amazon Kinesis](#alternativa-amazon-kinesis).

**Opción 3: Documentar Restricción**

Si no puedes crear ni SQS ni Kinesis, documenta:
1. Qué restricciones encontraste
2. Cómo se implementaría en producción
3. Qué recursos solicitaste al administrador
4. Evidencia de que el código está preparado para usar SQS/Kinesis

**📖 Para más detalles**, consulta la sección [Qué Hacer si No Puedes Crear SQS ni Kinesis](#qué-hacer-si-no-puedes-crear-sqs-ni-kinesis) al final de este documento.

### Recursos que Pueden Requerir Permisos del Administrador

Si recibes errores de `AccessDeniedException`, necesitarás solicitar al administrador que cree estos recursos:

1. **Cola SQS** (`anb-video-processing-queue` y `anb-video-processing-dlq`) - **CRÍTICO para Entrega 4**
2. **IAM Roles y Políticas** (si no puedes crear políticas personalizadas)
3. **VPC/NAT Gateway** (si no tienes permisos de VPC)

### Solución: Solicitar Recursos al Administrador

**Para el Paso 6 (SQS)**, si no puedes crear la cola, solicita al administrador que cree:

1. **Cola Principal**: `anb-video-processing-queue`
   - Tipo: Standard Queue
   - Visibility timeout: 300 segundos
   - Message retention: 14 días
   - Receive message wait time: 20 segundos

2. **Dead Letter Queue**: `anb-video-processing-dlq`
   - Tipo: Standard Queue

3. **Configurar Redrive Policy** en la cola principal:
   - Dead-letter queue: `anb-video-processing-dlq`
   - Maximum receives: 3

4. **Obtener el Queue URL** y proporcionártelo

**Alternativa: Usar AWS CLI**

Si tienes permisos vía AWS CLI pero no desde la consola, puedes intentar:

```bash
# Crear cola principal
aws sqs create-queue \
  --queue-name anb-video-processing-queue \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600,ReceiveMessageWaitTimeSeconds=20 \
  --region us-east-1

# Crear DLQ
aws sqs create-queue \
  --queue-name anb-video-processing-dlq \
  --region us-east-1

# Obtener Queue URL
aws sqs get-queue-url \
  --queue-name anb-video-processing-queue \
  --region us-east-1
```

---

## Arquitectura

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

### Componentes

- **Application Load Balancer (ALB)**: Distribuye tráfico entre instancias backend
- **Auto Scaling Group (Backend)**: Escala automáticamente las instancias de la API
- **RDS PostgreSQL (Multi-AZ)**: Base de datos con alta disponibilidad
- **Amazon SQS**: Cola de mensajes para procesamiento asíncrono de videos
- **S3 Bucket**: Almacenamiento de videos originales y procesados
- **Auto Scaling Group (Workers)**: Escala automáticamente los workers basado en profundidad de cola SQS
- **CloudWatch**: Monitoreo y alertas del sistema

---

## Prerrequisitos

- ✅ Cuenta de AWS activa
- ✅ AWS CLI instalado y configurado (`aws configure`)
- ✅ Acceso a la consola de AWS
- ✅ Conocimiento básico de EC2, RDS, S3, VPC, SQS
- ✅ Docker y Docker Compose instalados (para construir imágenes localmente)
- ✅ Acceso SSH a instancias EC2
- ✅ Git instalado

---

## Configuración Paso a Paso

### Paso 1: VPC y Networking

#### 1.1 Crear VPC

1. Ir a **VPC Dashboard** → **Create VPC**
2. Configuración:
   - **Name tag**: `anb-vpc`
   - **IPv4 CIDR block**: `10.0.0.0/16`
   - **Tenancy**: Default
   - Click **Create VPC**

#### 1.2 Crear Subnets

Crear 3 subnets públicas y 3 privadas en diferentes AZ:

**Subnets Públicas** (para ALB y NAT Gateway):
- `anb-public-subnet-1a`: `10.0.1.0/24` - AZ: `us-east-1a`
- `anb-public-subnet-1b`: `10.0.2.0/24` - AZ: `us-east-1b`
- `anb-public-subnet-1c`: `10.0.3.0/24` - AZ: `us-east-1c`

**Subnets Privadas** (para EC2, RDS, Workers):
- `anb-private-subnet-1a`: `10.0.10.0/24` - AZ: `us-east-1a`
- `anb-private-subnet-1b`: `10.0.11.0/24` - AZ: `us-east-1b`
- `anb-private-subnet-1c`: `10.0.12.0/24` - AZ: `us-east-1c`

**Pasos:**
1. VPC Dashboard → **Subnets** → **Create subnet**
2. Para cada subnet:
   - **VPC**: Seleccionar `anb-vpc`
   - **Subnet name**: Nombre correspondiente
   - **Availability Zone**: AZ correspondiente
   - **IPv4 CIDR block**: CIDR correspondiente
   - Para subnets públicas: Habilitar **Auto-assign public IPv4 address**

#### 1.3 Crear Internet Gateway

1. VPC Dashboard → **Internet Gateways** → **Create internet gateway**
2. **Name tag**: `anb-igw`
3. Click **Create internet gateway**
4. Seleccionar el IGW → **Actions** → **Attach to VPC** → Seleccionar `anb-vpc`

#### 1.4 Crear NAT Gateway

1. VPC Dashboard → **NAT Gateways** → **Create NAT gateway**
2. Configuración:
   - **Subnet**: `anb-public-subnet-1a`
   - **Elastic IP**: Allocate Elastic IP (crear nueva)
   - **Name tag**: `anb-nat-gateway`
   - Click **Create NAT gateway**

**Nota**: El NAT Gateway puede tardar varios minutos en estar disponible.

#### 1.5 Configurar Route Tables

**Route Table Pública:**
1. VPC Dashboard → **Route Tables** → **Create route table**
2. **Name tag**: `anb-public-rt`
3. **VPC**: `anb-vpc`
4. Agregar ruta:
   - **Destination**: `0.0.0.0/0`
   - **Target**: Internet Gateway (`anb-igw`)
5. **Subnet associations** → Asociar las 3 subnets públicas

**Route Table Privada:**
1. Crear otra route table: `anb-private-rt`
2. Agregar ruta:
   - **Destination**: `0.0.0.0/0`
   - **Target**: NAT Gateway (`anb-nat-gateway`)
3. **Subnet associations** → Asociar las 3 subnets privadas

---

### Paso 2: RDS (PostgreSQL)

#### 2.1 Crear Subnet Group

1. **RDS Dashboard** → **Subnet groups** → **Create DB subnet group**
2. Configuración:
   - **Name**: `anb-db-subnet-group`
   - **Description**: Subnet group for ANB RDS
   - **VPC**: `anb-vpc`
   - **Availability Zones**: Seleccionar `us-east-1a`, `us-east-1b`, `us-east-1c`
   - **Subnets**: Seleccionar las 3 subnets privadas
   - Click **Create**

#### 2.2 Crear RDS Instance

1. **RDS Dashboard** → **Databases** → **Create database**
2. Configuración:
   - **Engine type**: PostgreSQL
   - **Version**: PostgreSQL 15.x (o la más reciente)
   - **Template**: Production (o Free tier para pruebas)
   - **DB instance identifier**: `anb-postgres`
   - **Master username**: `anb_admin`
   - **Master password**: [Generar contraseña segura] (guardar en lugar seguro)
   - **DB instance class**: 
     - Producción: `db.t3.medium` o `db.t3.large`
     - Pruebas: `db.t3.micro` (Free tier)
   - **Storage**: 
     - **Storage type**: General Purpose SSD (gp3)
     - **Allocated storage**: 20 GB (mínimo)
     - **Storage autoscaling**: Habilitar (máximo 100 GB)
   - **Connectivity**:
     - **VPC**: `anb-vpc`
     - **Subnet group**: `anb-db-subnet-group`
     - **Public access**: No (solo acceso privado)
     - **VPC security group**: Crear nuevo `anb-rds-sg` (se configurará después)
     - **Availability Zone**: `us-east-1a`
   - **Database authentication**: Password authentication
   - **Database name**: `anb_db`
   - **Backup**: 
     - **Automated backups**: Habilitar
     - **Backup retention period**: 7 días
   - **High availability**: 
     - **Multi-AZ deployment**: Habilitar (para alta disponibilidad)
   - **Monitoring**: Opcional (habilitar Enhanced monitoring si es necesario)
   - **Maintenance**: 
     - **Auto minor version upgrade**: Habilitar
     - **Maintenance window**: Seleccionar ventana preferida
3. Click **Create database**

**⏱️ Tiempo estimado**: 10-15 minutos

#### 2.3 Notas Importantes

- **Anotar el Endpoint** de RDS (ejemplo: `anb-postgres.xxxxx.us-east-1.rds.amazonaws.com`)
- El puerto por defecto es `5432`
- Guardar las credenciales en un lugar seguro
- La instancia Multi-AZ creará automáticamente una réplica en otra AZ

---

### Paso 3: S3 Bucket

#### 3.1 Crear S3 Bucket

1. **S3 Dashboard** → **Create bucket**
2. Configuración:
   - **Bucket name**: `anb-rising-stars-videos-[tu-region]` (debe ser único globalmente)
     - Ejemplo: `anb-rising-stars-videos-east1`
   - **AWS Region**: `us-east-1` (o tu región)
   - **Object Ownership**: ACLs disabled (recomendado)
   - **Block Public Access**: 
     - **Desmarcar** "Block all public access" (aparecerá advertencia)
     - Marcar "I acknowledge..." para confirmar
     - Esto permitirá acceso público de lectura
   - **Bucket Versioning**: Habilitar (recomendado)
   - **Default encryption**: Habilitar (SSE-S3 o SSE-KMS)
   - **Object Lock**: Opcional
3. Click **Create bucket**

#### 3.2 Configurar Bucket Policy para Lectura Pública

**⚠️ IMPORTANTE**: 
- Aún necesitarás credenciales AWS para **subir** (PUT) y **eliminar** (DELETE) videos
- Solo la **lectura** (GET) será pública
- Los usuarios podrán ver los videos sin credenciales

**Pasos para hacer el bucket público para lectura:**

1. **Bucket** → **Permissions** → **Bucket policy** → **Edit**
2. Agregar esta política (reemplazar `anb-rising-starts-videos-east1` con tu bucket name):

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "PublicReadGetObject",
			"Effect": "Allow",
			"Principal": "*",
			"Action": "s3:GetObject",
			"Resource": "arn:aws:s3:::anb-rising-stars-videos-east1/*"
		}
	]
}
```

**Nota**: 
- ✅ Los usuarios pueden ver videos sin credenciales
- ✅ URLs directas a los videos: `https://bucket.s3.region.amazonaws.com/processed_videos/video.mp4`
- ❌ Aún necesitas credenciales para que tu aplicación suba/elimine videos
- ⚠️ Cualquiera con la URL puede ver el video (aceptable si los videos son públicos por diseño)

#### 3.3 Crear Carpetas en el Bucket

Crear las siguientes carpetas (prefixes):
- `uploads/` - Videos originales
- `processed_videos/` - Videos procesados
- `assets/` - Assets estáticos (logo ANB, etc.)

**Pasos:**
1. Abrir el bucket
2. Click **Create folder**
3. Crear cada carpeta mencionada

#### 3.4 Configurar CORS (si es necesario)

Si necesitas acceso desde navegadores web:
1. Bucket → **Permissions** → **Cross-origin resource sharing (CORS)**
2. Agregar configuración:
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000
    }
]
```

---

### Paso 4: Security Groups

#### 4.1 Security Group para RDS (`anb-rds-sg`)

1. **EC2 Dashboard** → **Security Groups** → **Create security group**
2. Configuración:
   - **Name**: `anb-rds-sg`
   - **Description**: Security group for ANB RDS PostgreSQL
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: PostgreSQL
     - **Port**: 5432
     - **Source**: `anb-backend-sg` (se creará después - puedes usar temporalmente el ID del security group)
     - **Type**: PostgreSQL
     - **Port**: 5432
     - **Source**: `anb-worker-sg` (se creará después - puedes usar temporalmente el ID del security group)
   - **Outbound rules**: Default (All traffic)
3. Click **Create security group**

**Nota**: Si aún no has creado los otros security groups, puedes actualizar las reglas después.

#### 4.2 Security Group para Backend (`anb-backend-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-backend-sg`
   - **Description**: Security group for ANB Backend API
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: Custom TCP
     - **Port**: 8000
     - **Source**: `anb-alb-sg` (se creará después)
     - **Type**: SSH
     - **Port**: 22
     - **Source**: Tu IP pública (para acceso SSH)
   - **Outbound rules**:
     - **Type**: All traffic
     - **Destination**: 0.0.0.0/0
3. Click **Create security group**

#### 4.3 Security Group para ALB (`anb-alb-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-alb-sg`
   - **Description**: Security group for ANB Application Load Balancer
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: HTTP
     - **Port**: 80
     - **Source**: 0.0.0.0/0
     - **Type**: HTTPS
     - **Port**: 443
     - **Source**: 0.0.0.0/0
   - **Outbound rules**: Default
3. Click **Create security group**

#### 4.4 Security Group para Worker (`anb-worker-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-worker-sg`
   - **Description**: Security group for ANB SQS Worker
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: SSH
     - **Port**: 22
     - **Source**: Tu IP pública (para acceso SSH)
   - **Outbound rules**:
     - **Type**: All traffic
     - **Destination**: 0.0.0.0/0
3. Click **Create security group**

#### 4.5 Actualizar Security Group de RDS

Ahora que tienes todos los security groups creados, actualiza `anb-rds-sg`:
1. Seleccionar `anb-rds-sg`
2. **Inbound rules** → **Edit inbound rules**
3. Asegurar que las fuentes sean `anb-backend-sg` y `anb-worker-sg`

---

### Paso 5: IAM Roles y Políticas

**⚠️ IMPORTANTE: Si no puedes crear IAM Roles** (cuenta de estudiante con permisos restringidos):

1. **Solicita al administrador** que cree los roles `anb-backend-role` y `anb-worker-role` con las políticas especificadas abajo
2. **Solución temporal**: Usa credenciales AWS en el `.env` (ver sección [Solución Temporal: Usar Credenciales](#solución-temporal-usar-credenciales) al final)
3. **Documenta la restricción** en tu entrega

#### 5.1 Crear IAM Role para Backend

**Si tienes permisos:**
1. **IAM Dashboard** → **Roles** → **Create role**
2. **Trusted entity type**: AWS service
3. **Service**: EC2
4. **Permissions**: Click **Create policy** (JSON tab):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:SendMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl"
            ],
            "Resource": "arn:aws:sqs:*:*:anb-video-processing-queue"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::anb-rising-starts-videos-east1/*",
                "arn:aws:s3:::anb-rising-starts-videos-east1"
            ]
        }
    ]
}
```

5. **Policy name**: `anb-backend-policy`
6. Click **Create policy**
7. Volver a crear role, seleccionar la política `anb-backend-policy`
8. **Role name**: `anb-backend-role`
9. Click **Create role**

#### 5.2 Crear IAM Role para Workers

1. **IAM Dashboard** → **Roles** → **Create role**
2. **Trusted entity type**: AWS service
3. **Service**: EC2
4. **Permissions**: Click **Create policy** (JSON tab):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl"
            ],
            "Resource": "arn:aws:sqs:*:*:anb-video-processing-queue"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::anb-rising-starts-videos-east1/*",
                "arn:aws:s3:::anb-rising-starts-videos-east1"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*"
        }
    ]
}
```

5. **Policy name**: `anb-worker-policy`
6. Click **Create policy**
7. Volver a crear role, seleccionar la política `anb-worker-policy`
8. **Role name**: `anb-worker-role`
9. Click **Create role**

**Si NO tienes permisos para crear roles:**

Solicita al administrador que cree el rol `anb-worker-role` con:
- **Trusted entity**: EC2
- **Policies**: Usar el JSON de arriba (líneas 519-553)

**Mientras tanto**, puedes usar credenciales temporales en el `.env` del worker (ver sección [Solución Temporal: Usar Credenciales](#solución-temporal-usar-credenciales)).

---

### Paso 6: Crear Cola SQS

**⚠️ IMPORTANTE**: SQS se configura ANTES del backend porque el backend necesita el Queue URL.

**⚠️ Si no puedes crear SQS**: Si recibes errores de `AccessDeniedException` porque tu cuenta de estudiante no tiene permisos, consulta la sección [⚠️ IMPORTANTE: Cuentas de Estudiante / Permisos Restringidos](#-importante-cuentas-de-estudiante--permisos-restringidos) al inicio de este documento y la sección [Qué Hacer si No Puedes Crear SQS ni Kinesis](#qué-hacer-si-no-puedes-crear-sqs-ni-kinesis) al final.

#### 6.1 Crear Queue Principal

1. **SQS Dashboard** → **Create queue**
2. Configuración:
   - **Name**: `anb-video-processing-queue`
   - **Type**: Standard Queue
   - **Visibility timeout**: 300 segundos (5 minutos)
   - **Message retention period**: 14 días
   - **Receive message wait time**: 20 segundos (long polling)
   - **Encryption**: Opcional (SSE-SQS o SSE-KMS)
3. Click **Create queue**
4. **Anotar el Queue URL** (ejemplo: `https://sqs.us-east-1.amazonaws.com/123456789/anb-video-processing-queue`)

#### 6.2 Crear Dead Letter Queue (DLQ)

1. **Crear la Dead Letter Queue:**
   - **SQS Dashboard** → **Create queue**
   - **Name**: `anb-video-processing-dlq`
   - **Type**: Standard Queue
   - **Visibility timeout**: 30 segundos (suficiente para DLQ)
   - **Message retention period**: 4 días (o más si quieres investigar errores)
   - **Receive message wait time**: 0 segundos
   - **Encryption**: Opcional (puede ser igual a la cola principal)
   - Click **Create queue**

2. **Configurar Redrive Policy en la Cola Principal:**
   
   **Pasos detallados:**
   
   a. **Ir a la cola principal:**
      - En el **SQS Dashboard**, hacer click en el nombre de la cola `anb-video-processing-queue`
      - Esto te llevará a la página de detalles de la cola
   
   b. **Abrir la configuración de Dead-letter queue:**
      - En la página de detalles de la cola, busca la sección **"Dead-letter queue"** (Cola de mensajes fallidos)
      - Si no la ves inmediatamente, busca en las pestañas o secciones:
        - **"Configuration"** (Configuración)
        - O directamente en el menú lateral de la cola
   
   c. **Editar la configuración:**
      - Click en **"Edit"** (Editar) junto a "Dead-letter queue"
      - O busca el botón **"Configure Dead-letter queue"** (Configurar cola de mensajes fallidos)
   
   d. **Configurar los parámetros:**
      - **"Enable Dead-letter queue"** (Habilitar cola de mensajes fallidos): ✅ Marcar esta casilla
      - **"Dead-letter queue"**: Seleccionar `anb-video-processing-dlq` del dropdown
      - **"Maximum receives"** (Recepción máxima): Ingresar `3`
        - Esto significa que si un mensaje es recibido 3 veces sin ser eliminado, se moverá automáticamente a la DLQ
   
   e. **Guardar:**
      - Click en **"Save"** (Guardar) o **"Save changes"** (Guardar cambios)
   
   **Ubicación alternativa si no encuentras la opción:**
   - También puedes configurarlo desde la pestaña **"Access policy"** (Política de acceso) o **"Configuration"** (Configuración)
   - Busca la sección **"Redrive policy"** o **"Dead-letter queue"**
   - Puede estar en formato JSON que necesitas editar manualmente

3. **Verificar la configuración:**
   - Después de guardar, deberías ver en la página de la cola principal:
     - **"Dead-letter queue"**: `anb-video-processing-dlq`
     - **"Maximum receives"**: `3`

#### 6.3 Verificar Permisos

Los permisos IAM para SQS ya están configurados en el Paso 5. Los roles `anb-backend-role` y `anb-worker-role` tienen los permisos necesarios.

---

### Paso 7: AMI y Launch Template (Backend)

#### 7.1 Preparar Instancia EC2 para AMI

1. **EC2 Dashboard** → **Launch instance**
2. Configuración:
   - **Name**: `anb-backend-ami-builder`
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance type**: `t3.micro` (suficiente para crear AMI)
   - **Key pair**: Crear o seleccionar existente
   - **Network settings**:
     - **VPC**: `anb-vpc`
     - **Subnet**: Cualquier subnet pública (temporal)
     - **Auto-assign public IP**: Enable
     - **Security group**: `anb-backend-sg` (temporalmente permitir SSH desde tu IP)
   - **Configure storage**: 20 GB gp3
   - **IAM instance profile**: `anb-backend-role`
3. Click **Launch instance**

#### 7.2 Conectar a la Instancia y Configurar

```bash
# Conectar via SSH
ssh -i tu-key.pem ubuntu@<IP_PUBLICA>

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clonar repositorio
git clone https://github.com/ehhurtadoc-uniandes/MISW4204-GRUPO11-ANB_Rising_Stars_Showcase.git /opt/anb-api
cd /opt/anb-api

# Crear archivo .env (ver Paso 7.3)
sudo nano /opt/anb-api/.env
```

#### 7.3 Crear Archivo .env para Backend

Crear `/opt/anb-api/.env` con (reemplazar valores con los reales):

```env
# Database (RDS)
DATABASE_URL=postgresql://anb_admin:TU_PASSWORD@RDS_ENDPOINT:5432/anb_db
POSTGRES_HOST=RDS_ENDPOINT
POSTGRES_PORT=5432
POSTGRES_USER=anb_admin
POSTGRES_PASSWORD=TU_PASSWORD
POSTGRES_DB=anb_db

# SQS Configuration (Entrega 4)
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/anb-video-processing-queue
SQS_REGION=us-east-1
SQS_VISIBILITY_TIMEOUT=300
SQS_MAX_RECEIVE_COUNT=3
SQS_WAIT_TIME_SECONDS=20

# JWT Configuration
SECRET_KEY=GENERAR_SECRET_KEY_AQUI
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3 Storage
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-starts-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/

# Environment
ENVIRONMENT=production
DEBUG=False

# File Storage
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100

# ANB Configuration
ANB_LOGO_PATH=/app/assets/anb_logo.png
VIDEO_MAX_DURATION=30
VIDEO_RESOLUTION=720p
```

**Para generar SECRET_KEY:**
```bash
openssl rand -hex 32
```

#### 7.4 Crear Script de Inicio

```bash
sudo nano /opt/anb-api/start-backend.sh
```

Contenido:
```bash
#!/bin/bash
set -e

cd /opt/anb-api

# Esperar a que Docker esté listo
until docker info > /dev/null 2>&1; do
    echo "Waiting for Docker..."
    sleep 2
done

# Detener contenedor existente si existe
docker stop anb-api || true
docker rm anb-api || true

# Construir imagen si no existe
if ! docker images | grep -q "anb-api"; then
    echo "Building Docker image..."
    docker build -t anb-api:latest .
fi

# Ejecutar migraciones
echo "Running database migrations..."
docker run --rm --env-file .env \
    anb-api:latest \
    alembic upgrade head || echo "Migration failed, continuing..."

# Iniciar contenedor de la API
echo "Starting API container..."
docker run -d --name anb-api \
    --env-file .env \
    -p 8000:8000 \
    --restart unless-stopped \
    anb-api:latest \
    uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "API service started successfully!"

# Monitorear el contenedor
while true; do
    if ! docker ps | grep -q "anb-api"; then
        echo "Container anb-api stopped unexpectedly"
        exit 1
    fi
    sleep 10
done
```

```bash
sudo chmod +x /opt/anb-api/start-backend.sh
```

#### 7.5 Configurar Systemd Service

```bash
sudo nano /etc/systemd/system/anb-api.service
```

Contenido:
```ini
[Unit]
Description=ANB API Service
After=docker.service network-online.target
Requires=docker.service network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/anb-api
ExecStart=/opt/anb-api/start-backend.sh
ExecStop=/usr/bin/docker stop anb-api
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable anb-api
sudo systemctl start anb-api
```

#### 7.6 Verificar que la API Funciona

```bash
# Ver logs
sudo journalctl -u anb-api -f

# Verificar que el contenedor esté corriendo
docker ps

# Probar la API (desde la instancia)
curl http://localhost:8000/docs
```

#### 7.7 Crear AMI desde la Instancia

1. **EC2 Dashboard** → Seleccionar la instancia
2. **Actions** → **Image and templates** → **Create image**
3. **Image name**: `anb-backend-ami-v1`
4. **Description**: ANB Backend API with SQS support
5. Click **Create image**
6. Esperar a que termine (10-15 minutos)

#### 7.8 Crear Launch Template

1. **EC2 Dashboard** → **Launch Templates** → **Create launch template**
2. Configuración:
   - **Name**: `anb-backend-launch-template`
   - **AMI**: Seleccionar `anb-backend-ami-v1`
   - **Instance type**: `t3.small` o `t3.medium`
   - **Key pair**: Tu key pair
   - **Network settings**:
     - **Subnet**: No incluir (se configurará en ASG)
     - **Security groups**: `anb-backend-sg`
   - **Storage**: 20 GB gp3
   - **IAM instance profile**: `anb-backend-role`
3. Click **Create launch template**

---

### Paso 8: Auto Scaling Group (Backend)

#### 8.1 Crear Target Group

1. **EC2 Dashboard** → **Target Groups** → **Create target group**
2. Configuración:
   - **Target type**: Instances
   - **Name**: `anb-backend-tg`
   - **Protocol**: HTTP
   - **Port**: 8000
   - **VPC**: `anb-vpc`
   - **Health checks**:
     - **Health check protocol**: HTTP
     - **Health check path**: `/health` o `/docs`
     - **Healthy threshold**: 2
     - **Unhealthy threshold**: 3
     - **Timeout**: 5
     - **Interval**: 30
3. Click **Create target group**

#### 8.2 Crear Auto Scaling Group

1. **EC2 Dashboard** → **Auto Scaling Groups** → **Create Auto Scaling group**
2. Configuración:
   - **Name**: `anb-backend-asg`
   - **Launch template**: `anb-backend-launch-template`
   - **VPC**: `anb-vpc`
   - **Subnets**: Seleccionar las 3 subnets privadas (múltiples AZs para alta disponibilidad)
   - **Load balancing**:
     - **Attach to an existing load balancer**: Yes
     - **Target group**: `anb-backend-tg`
     - **Health check type**: ELB
     - **Health check grace period**: 300 segundos
   - **Group size**:
     - **Desired capacity**: 2
     - **Minimum capacity**: 2
     - **Maximum capacity**: 5
   - **Scaling policies**: Se configurarán después (ver Paso 8.3)
3. Click **Create Auto Scaling group**

#### 8.3 Configurar Políticas de Escalamiento para Backend

**Opción 1: Target Tracking con RequestCountPerTarget (RECOMENDADO)**

Esta métrica es mejor que CPU porque escala basado en la carga real de requests por instancia.

1. En el ASG `anb-backend-asg` → **Dynamic scaling policies** → **Create dynamic scaling policy**
2. Configuración:
   - **Policy type**: `Target tracking scaling`
   - **Scaling policy name**: `alb-request-count-tracking`
   - **Metric type**: `Custom CloudWatch metric`
   
3. **Configurar el JSON de métrica personalizada:**
   
   ```json
   {
     "CustomizedMetricSpecification": {
       "MetricName": "RequestCountPerTarget",
       "Namespace": "AWS/ApplicationELB",
       "Statistic": "Average",
       "Dimensions": [
         {
           "Name": "TargetGroup",
           "Value": "targetgroup/anb-backend-tg/XXXXX"
         },
         {
           "Name": "LoadBalancer",
           "Value": "app/anb-alb/XXXXX"
         }
       ]
     }
   }
   ```
   
   **Nota**: Reemplaza `XXXXX` con los IDs reales de tu Target Group y Load Balancer. Puedes encontrarlos en:
   - **Target Group**: EC2 → Target Groups → `anb-backend-tg` → Copiar el ARN completo
   - **Load Balancer**: EC2 → Load Balancers → `anb-alb` → Copiar el ARN completo
   
   O usa solo el nombre del Target Group si prefieres:
   
   ```json
   {
     "CustomizedMetricSpecification": {
       "MetricName": "RequestCountPerTarget",
       "Namespace": "AWS/ApplicationELB",
       "Statistic": "Average",
       "Dimensions": [
         {
           "Name": "TargetGroup",
           "Value": "targetgroup/anb-backend-tg/XXXXX"
         }
       ]
     }
   }
   ```

4. **Target value**: `100` requests por minuto por instancia
   - Esto significa que Auto Scaling intentará mantener aproximadamente 100 requests/minuto por instancia
   - Si hay más requests por instancia, escalará hacia arriba
   - Si hay menos requests por instancia, escalará hacia abajo

5. **Instance warm-up**: `300` segundos (5 minutos)

6. Click **Create**

**Opción 2: Target Tracking con CPU (Alternativa más simple)**

Si prefieres usar CPU (más simple pero menos preciso):

1. **Policy type**: `Target tracking scaling`
2. **Metric type**: `Average CPU utilization`
3. **Target value**: `70%`
4. Click **Create**

**Opción 3: Step Scaling con CloudWatch Alarms**

Similar a como configuraste los workers, puedes crear alarms basados en:
- `RequestCount` del ALB (total de requests)
- `TargetResponseTime` (tiempo de respuesta)
- `HTTPCode_Target_5XX_Count` (errores)

Y crear políticas de Step Scaling que respondan a estos alarms.

---

### Paso 9: Application Load Balancer

#### 9.1 Crear Application Load Balancer

1. **EC2 Dashboard** → **Load Balancers** → **Create Load Balancer**
2. Seleccionar **Application Load Balancer**
3. Configuración:
   - **Name**: `anb-alb`
   - **Scheme**: Internet-facing
   - **IP address type**: IPv4
   - **VPC**: `anb-vpc`
   - **Mappings**: 
     - Seleccionar las 3 AZs
     - Para cada AZ, seleccionar una subnet pública
   - **Security groups**: `anb-alb-sg`
   - **Listeners and routing**:
     - **Protocol**: HTTP
     - **Port**: 80
     - **Default action**: Forward to `anb-backend-tg`
4. Click **Create load balancer**

**⏱️ Tiempo estimado**: 2-5 minutos

#### 9.2 Obtener DNS del ALB

1. Seleccionar el ALB
2. Copiar el **DNS name** (ej: `anb-alb-123456789.us-east-1.elb.amazonaws.com`)
3. Probar acceso: `http://anb-alb-123456789.us-east-1.elb.amazonaws.com/docs`

---

### Paso 10: AMI y Launch Template (Workers)

#### 10.1 Preparar Instancia EC2 para AMI de Workers

1. **EC2 Dashboard** → **Launch instance**
2. Configuración:
   - **Name**: `anb-worker-ami-builder`
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance type**: `t3.small` (2 vCPU, 2 GiB RAM según especificaciones)
   - **Key pair**: Tu key pair
   - **Network settings**:
     - **VPC**: `anb-vpc`
     - **Subnet**: Cualquier subnet privada
     - **Auto-assign public IP**: Enable (temporal para configuración)
     - **Security group**: `anb-worker-sg`
   - **Configure storage**: 30 GiB gp3 (según especificaciones)
   - **IAM instance profile**: `anb-worker-role`
   - **Advanced details**:
     - **User data**: Ver contenido de `scripts/aws/worker-sqs-user-data.sh` (copiar y pegar)
3. Click **Launch instance**

#### 10.2 Conectar y Configurar Worker

```bash
# Conectar via SSH
ssh -i tu-key.pem ubuntu@<IP_PUBLICA>

# Editar .env con valores reales
sudo nano /opt/anb-worker/.env
```

Asegurar que el `.env` tenga:
- `SQS_QUEUE_URL` configurado correctamente (del Paso 6)
- RDS endpoint correcto (del Paso 2)
- S3 bucket name correcto (del Paso 3)
- Credenciales AWS (o usar IAM Role - recomendado)

#### 10.3 Verificar Worker

```bash
# Ver logs del servicio
sudo journalctl -u anb-worker-sqs -f

# Verificar que el contenedor esté corriendo
docker ps

# Ver logs del contenedor
docker logs anb-worker-sqs
```

#### 10.4 Crear AMI desde la Instancia

1. **EC2 Dashboard** → Seleccionar la instancia worker
2. **Actions** → **Image and templates** → **Create image**
3. **Image name**: `anb-worker-ami-v1`
4. **Description**: ANB SQS Worker
5. Click **Create image**
6. Esperar a que termine (10-15 minutos)

#### 10.5 Crear Launch Template para Workers

1. **EC2 Dashboard** → **Launch Templates** → **Create launch template**
2. Configuración:
   - **Name**: `anb-worker-launch-template`
   - **AMI**: Seleccionar `anb-worker-ami-v1`
   - **Instance type**: `t3.small` (2 vCPU, 2 GiB RAM)
   - **Key pair**: Tu key pair
   - **Network settings**:
     - **Subnet**: No incluir (se configurará en ASG)
     - **Security groups**: `anb-worker-sg`
   - **Storage**: 30 GiB gp3
   - **IAM instance profile**: `anb-worker-role`
3. Click **Create launch template**

---

### Paso 11: Auto Scaling Group para Workers

#### 11.1 Crear Auto Scaling Group

1. **EC2 Dashboard** → **Auto Scaling Groups** → **Create Auto Scaling group**
2. Configuración:
   - **Name**: `anb-worker-asg`
   - **Launch template**: `anb-worker-launch-template`
   - **VPC**: `anb-vpc`
   - **Subnets**: Seleccionar **múltiples subnets privadas en diferentes AZs** (mínimo 2 AZs para alta disponibilidad)
   - **Load balancing**: No (workers no necesitan load balancer)
   - **Group size**:
     - **Desired capacity**: 1
     - **Minimum capacity**: 1
     - **Maximum capacity**: 3
   - **Scaling policies**: Ver siguiente sección
3. Click **Create Auto Scaling group**

#### 11.2 Configurar Políticas de Escalamiento

**Target Tracking Policy** (Recomendado):

1. En el ASG → **Dynamic scaling policies** → **Create dynamic scaling policy**
2. Configuración:
   - **Policy type**: `Target tracking scaling` (Escalado de seguimiento de destino)
   - **Scaling policy name**: `sqs-queue-depth-tracking` (o el nombre que prefieras)
   - **Metric type**: `Custom CloudWatch metric` (Métrica personalizada de CloudWatch)
   
3. **Configurar el JSON de métrica personalizada:**
   
   En el campo **"JSON de métrica personalizada"** (Custom metric JSON), reemplaza el contenido con este JSON:
   
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
   
   **Explicación de los campos:**
   - `MetricName`: `ApproximateNumberOfMessagesVisible` - Número de mensajes visibles en la cola
   - `Namespace`: `AWS/SQS` - Namespace de CloudWatch para SQS
   - `Statistic`: `Average` - Usar el promedio de mensajes
   - `Dimensions`: Especifica la cola SQS por nombre
     - `Name`: `QueueName` - Nombre de la dimensión
     - `Value`: `anb-video-processing-queue` - Nombre de tu cola SQS

4. **Configurar el valor de destino:**
   - **Target value**: `10`
     - Esto significa que Auto Scaling intentará mantener aproximadamente 10 mensajes visibles por instancia worker
     - Si hay más de 10 mensajes por instancia, escalará hacia arriba
     - Si hay menos de 10 mensajes por instancia, escalará hacia abajo

5. **Configurar tiempos de preparación:**
   - **Instance warm-up** (Preparación de la instancia): `300` segundos (5 minutos)
     - Tiempo que espera antes de considerar que una nueva instancia está lista

6. Click **Create** (Crear)

**Nota**: Si tu cola SQS está en una región diferente o necesitas usar el ARN completo, puedes usar esta alternativa en el JSON:

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

Si necesitas usar el ARN completo de la cola, puedes usar:

```json
{
  "CustomizedMetricSpecification": {
    "MetricName": "ApproximateNumberOfMessagesVisible",
    "Namespace": "AWS/SQS",
    "Statistic": "Average",
    "Dimensions": [
      {
        "Name": "QueueName",
        "Value": "arn:aws:sqs:us-east-1:ACCOUNT_ID:anb-video-processing-queue"
      }
    ]
  }
}
```

**Recomendación**: Usa solo el nombre de la cola (`anb-video-processing-queue`) en la mayoría de los casos, ya que AWS lo resuelve automáticamente.

**Alternativa: Step Scaling**:

1. Crear CloudWatch alarms primero (ver Paso 12)
2. En el ASG → **Dynamic scaling policies** → **Create dynamic scaling policy**
3. **Policy type**: Step scaling
4. **Alarm**: Seleccionar alarm creado
5. **Scale-out**: Agregar 1 instancia cuando mensajes > 20
6. **Scale-in**: Remover 1 instancia cuando mensajes < 5

---

### Paso 12: Configurar CloudWatch

#### 12.1 Crear CloudWatch Alarms para Auto Scaling

**Alarm para Scale-Out** (Escalar hacia arriba):

1. **CloudWatch Dashboard** → **Alarms** → **Create alarm**

2. **Paso 1: Seleccionar la métrica**
   - Click en el botón azul **"Seleccione una métrica"** (Select a metric)
   - En la página de selección de métricas, busca en el panel izquierdo:
     - **"All metrics"** (Todas las métricas) o **"Browse"** (Explorar)
   - En la lista de servicios, busca y haz click en **"SQS"** (Simple Queue Service)
   - Dentro de SQS, verás diferentes métricas. Busca y selecciona:
     - **"Queue Metrics"** (Métricas de cola)
     - O directamente busca la métrica: **"ApproximateNumberOfMessagesVisible"**
   - En la lista de colas, verás varias opciones. **IMPORTANTE**: Selecciona SOLO esta métrica:
     - ✅ **`anb-video-processing-queue`** con métrica **`ApproximateNumberOfMessagesVisible`**
     - ❌ **NO** selecciones `ApproximateNumberOfMessagesVisibleInQuietGroups` (esta es diferente)
   - Haz click en la fila que corresponde a `anb-video-processing-queue` → `ApproximateNumberOfMessagesVisible`
   - Verás que se marca con un check (✓) y se resalta en azul
   - Haz click en **"Seleccionar una métrica"** (Select a metric) en la parte inferior derecha
   
   **Diferencia entre las métricas:**
   - `ApproximateNumberOfMessagesVisible`: Número total de mensajes visibles en la cola ✅ **USA ESTA**
   - `ApproximateNumberOfMessagesVisibleInQuietGroups`: Solo mensajes en grupos "quiet" ❌ No usar para auto-scaling

3. **Paso 1 (continuación): Configurar la condición**
   - Una vez seleccionada la métrica, verás un gráfico de la métrica
   - En la sección **"Conditions"** (Condiciones) o **"Whenever"** (Siempre que):
     - **"is"**: Seleccionar **"Greater"** (Mayor que) o **">"**
     - **"than"**: Ingresar `20`
     - **"for"**: `1` datapoint(s) out of `1`
     - Esto significa: "Cuando el número de mensajes visibles sea mayor que 20"

4. **Paso 2: Configurar la acción**
   
   a. **Activador de estado de alarma** (Alarm state trigger):
      - Debe estar seleccionado **"En modo alarma"** (In alarm state) ✅
      - Esto significa que la acción se ejecutará cuando el alarm entre en estado de alarma
   
   b. **Agregar acción de Auto Scaling:**
      - Haz click en el botón azul **"Agregar acción de Auto Scaling"** (Add Auto Scaling action)
      - Se abrirá un formulario o modal para configurar la acción
   
   c. **Configurar la acción de Auto Scaling:**
      
      **Paso 1: Seleccionar el grupo**
      - **"Tipo de recurso"** (Resource type): Debe estar seleccionado **"Grupo de EC2 Auto Scaling"** ✅
      - **"Seleccione un grupo"** (Select a group): 
        - Abre el dropdown y selecciona `anb-worker-asg`
        - Si no aparece, usa el buscador para encontrarlo
      
      **Paso 2: Seleccionar la acción**
      - **"Realice la siguiente acción..."** (Perform the following action...):
        - Abre el dropdown **"Seleccione una acción"** (Select an action)
        - **⚠️ PROBLEMA COMÚN**: Si el dropdown está vacío o dice "Solo están disponibles las acciones del grupo de Auto Scaling seleccionado", significa que el ASG no tiene políticas de escalado configuradas
      
      **Solución si no aparecen acciones:**
      
      **Opción A: Crear una política de Step Scaling primero (RECOMENDADO)**
      1. Ve a **EC2 Console** → **Auto Scaling Groups** → Selecciona `anb-worker-asg`
      2. Ve a la pestaña **"Dynamic scaling policies"** (Políticas de escalado dinámico)
      3. Click en **"Create dynamic scaling policy"**
      4. Configura:
         - **Policy type**: `Step scaling`
         - **Policy name**: `scale-up-policy`
         - **Alarm**: Selecciona el alarm que estás creando (o créalo después y vuelve)
         - **Scaling adjustments**:
           - **When**: `Greater than 20`
           - **Then**: `Add 1 capacity unit` (o `Add 1 instance`)
      5. Guarda la política
      6. Vuelve a CloudWatch y ahora deberías ver la política en el dropdown
      
      **Opción B: Usar Target Tracking (MÁS SIMPLE - ya lo configuraste en Paso 11.2)**
      - Si ya configuraste Target Tracking en el Paso 11.2, **NO necesitas crear estos alarms manualmente**
      - Target Tracking crea automáticamente los alarms necesarios
      - Puedes saltarte este paso y usar solo Target Tracking
      
      **Opción C: Crear política simple desde CloudWatch**
      - Si el dropdown sigue vacío, puedes intentar crear una política directamente desde aquí
      - Busca un botón como **"Create scaling policy"** o **"Crear política de escalado"**
      - O simplemente continúa sin seleccionar una acción y AWS creará una política simple automáticamente
   
   d. **Guardar la acción:**
      - Haz click en **"Add"** (Agregar) o **"Save"** (Guardar) para confirmar la acción
   
   **Nota**: No necesitas configurar notificaciones SNS para que funcione el auto-scaling, pero puedes agregarlas si quieres recibir emails cuando se escale.

5. **Paso 3: Agregar detalles**
   - **Alarm name**: `anb-worker-scale-up`
   - **Alarm description**: `Scale up workers when queue depth > 20 messages`
   - Click **"Next"** (Siguiente)

6. **Paso 4: Revisar y crear**
   - Revisa la configuración
   - Click **"Create alarm"** (Crear alarma)

**Alarm para Scale-In** (Escalar hacia abajo):

1. Repite los pasos anteriores, pero con estas diferencias:

2. **Métrica**: La misma (`ApproximateNumberOfMessagesVisible` de `anb-video-processing-queue`)

3. **Condición**:
   - **"is"**: Seleccionar **"Less"** (Menor que) o **"<"**
   - **"than"**: Ingresar `5`
   - Esto significa: "Cuando el número de mensajes visibles sea menor que 5"

4. **Acción**:
   - **Auto Scaling group**: `anb-worker-asg`
   - **"Remove capacity"**: `1` instance
   - **"When alarm triggers"**: `Remove 1 instance`

5. **Alarm name**: `anb-worker-scale-down`
6. **Alarm description**: `Scale down workers when queue depth < 5 messages`

**Nota**: Si no encuentras la métrica de SQS:
- Asegúrate de que la cola SQS ya esté creada y haya tenido actividad
- Las métricas de SQS pueden tardar unos minutos en aparecer después de crear la cola
- Si no aparece, intenta buscar directamente por el nombre de la cola en el buscador de métricas

**Alternativa rápida**: Si ya tienes una política de Target Tracking configurada (Paso 11.2), los alarms se crean automáticamente y no necesitas crear estos alarms manualmente. Los alarms manuales son útiles si usas Step Scaling en lugar de Target Tracking.

#### 12.2 Crear Dashboard de CloudWatch

1. **CloudWatch Dashboard** → **Create dashboard**
2. **Dashboard name**: `anb-system-dashboard`
3. Agregar widgets para:
   - SQS Queue Depth (`ApproximateNumberOfMessagesVisible`)
   - Worker Count (ASG `DesiredCapacity`)
   - API Request Count (ALB `RequestCount`)
   - Error Rate (ALB `HTTPCode_Target_5XX_Count`)
   - Processing Time (métrica personalizada si la implementas)

---

### Paso 13: Configuración Final y Verificación

#### 13.1 Verificar Alta Disponibilidad

1. **Backend ASG**: 
   - Verificar que esté en múltiples AZs
   - EC2 Dashboard → Auto Scaling Groups → `anb-backend-asg` → Verificar subnets
2. **Workers ASG**: 
   - Verificar que esté en múltiples AZs
   - EC2 Dashboard → Auto Scaling Groups → `anb-worker-asg` → Verificar subnets
3. **RDS**: 
   - Verificar que Multi-AZ esté habilitado
   - RDS Dashboard → Seleccionar instancia → Verificar "Multi-AZ" = Yes

#### 13.2 Pruebas End-to-End

1. **Subir un video desde la API**:
   ```bash
   # Obtener token de autenticación primero
   curl -X POST http://ALB_DNS/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"usuario@example.com","password":"password"}'
   
   # Subir video
   curl -X POST http://ALB_DNS/api/videos/upload \
     -H "Authorization: Bearer TOKEN" \
     -F "title=Test Video" \
     -F "video_file=@test.mp4"
   ```

2. **Verificar mensaje en SQS**:
   ```bash
   aws sqs get-queue-attributes \
     --queue-url SQS_QUEUE_URL \
     --attribute-names ApproximateNumberOfMessages
   ```

3. **Verificar video en S3**:
   ```bash
   aws s3 ls s3://anb-rising-starts-videos-east1/uploads/
   ```

4. **Esperar procesamiento** (1-2 minutos)

5. **Verificar video procesado en S3**:
   ```bash
   aws s3 ls s3://anb-rising-starts-videos-east1/processed_videos/
   ```

6. **Verificar URL pública**:
   - Consultar video desde API: `GET /api/videos/{video_id}`
   - Verificar que `processed_url` sea una URL pública de S3

#### 13.3 Probar Escalamiento

1. Subir múltiples videos para llenar la cola (10-20 videos)
2. Verificar en CloudWatch que `ApproximateNumberOfMessagesVisible` aumente
3. Verificar que el ASG agregue workers automáticamente
4. Esperar a que se procesen los videos
5. Verificar que el ASG remueva workers automáticamente cuando la cola esté vacía

---

## Resumen de Pasos

1. **VPC y Networking** - Red privada con subnets públicas y privadas
2. **RDS (PostgreSQL)** - Base de datos Multi-AZ
3. **S3 Bucket** - Almacenamiento de videos
4. **Security Groups** - Reglas de firewall
5. **IAM Roles** - Permisos para SQS y S3
6. **SQS** - Cola de mensajes (configurada ANTES del backend)
7. **AMI y Launch Template Backend** - Imagen y template para API
8. **Auto Scaling Group Backend** - Escalamiento automático de API
9. **Application Load Balancer** - Balanceador de carga
10. **AMI y Launch Template Workers** - Imagen y template para workers
11. **Auto Scaling Group Workers** - Escalamiento automático de workers
12. **CloudWatch** - Monitoreo y alertas
13. **Verificación** - Pruebas end-to-end

---

## Troubleshooting

### Workers no escalan

1. Verificar que los CloudWatch alarms estén configurados
2. Verificar que el ASG tenga las políticas de escalamiento
3. Verificar métricas de SQS en CloudWatch
4. Verificar que los IAM roles tengan permisos para CloudWatch

### Mensajes se quedan en cola

1. Verificar que los workers estén corriendo: `aws ec2 describe-instances --filters "Name=tag:Name,Values=anb-worker*"`
2. Verificar permisos IAM del rol `anb-worker-role`
3. Verificar logs de workers: `docker logs anb-worker-sqs` (desde instancia)
4. Verificar que el SQS_QUEUE_URL esté correcto en el `.env`

### Alta disponibilidad no funciona

1. Verificar que las subnets estén en diferentes AZs
2. Verificar que el ASG tenga instancias en múltiples AZs
3. Probar fallo de una instancia y verificar que el sistema continúe funcionando

### API no responde

1. Verificar que las instancias del Target Group estén "Healthy"
2. Verificar que el Security Group del ALB permita tráfico HTTP (puerto 80)
3. Verificar logs de la API: `sudo journalctl -u anb-api -f` (desde instancia)

---

## Costos Estimados (Mensual)

- **VPC/NAT Gateway**: ~$32/mes (NAT Gateway)
- **RDS (db.t3.medium Multi-AZ)**: ~$150/mes
- **EC2 Backend (t3.small x 2-5)**: ~$30-75/mes
- **EC2 Workers (t3.small x 1-3)**: ~$15-45/mes
- **ALB**: ~$16/mes
- **S3**: ~$5-20/mes (dependiendo del almacenamiento)
- **SQS**: ~$0.40 por millón de requests
- **CloudWatch**: ~$10-20/mes
- **Total estimado**: ~$260-360/mes

**Nota**: Los costos pueden variar significativamente según el uso. Considera usar Free Tier donde sea posible para desarrollo/pruebas.

---

## Referencias

- **[Guía de Despliegue Entrega 3](../Entrega_3/AWS_DEPLOYMENT_GUIDE.md)** - Documentación base (referencia histórica)
- **[Plan de Migración](MIGRATION_PLAN.md)** - Si necesitas migrar desde Entrega 3
- **[Guía de Migración SQS](SQS_MIGRATION_GUIDE.md)** - Detalles de migración a SQS

---

## Notas Finales

- Esta guía asume que estás implementando desde cero. Si ya tienes componentes de la Entrega 3, puedes adaptar los pasos.
- Todos los valores de ejemplo (endpoints, nombres, etc.) deben ser reemplazados con tus valores reales.
- Guarda todas las credenciales y endpoints en un lugar seguro.
- Prueba cada componente antes de pasar al siguiente paso.
- Considera usar AWS Systems Manager Parameter Store o Secrets Manager para almacenar credenciales de forma segura.

---

## Alternativa: Amazon Kinesis

Si no puedes crear SQS pero tienes permisos para Kinesis, puedes usar **Amazon Kinesis Data Streams** como alternativa. Los requisitos de la Entrega 4 permiten usar **SQS o Kinesis**.

### Ventajas de Kinesis

- ✅ Permite ordenamiento de mensajes
- ✅ Mejor para streams de datos en tiempo real
- ✅ Puede tener más permisos en cuentas de estudiante

### Desventajas de Kinesis

- ❌ Más complejo de configurar
- ❌ Requiere shards (más costoso)
- ❌ El código actual está diseñado para SQS

### Implementación con Kinesis

Si decides usar Kinesis, necesitarás:

1. **Crear Kinesis Data Stream**:
   ```bash
   aws kinesis create-stream \
     --stream-name anb-video-processing-stream \
     --shard-count 1 \
     --region us-east-1
   ```

2. **Modificar el código**:
   - Actualizar `app/services/sqs_service.py` para usar Kinesis
   - Actualizar `app/workers/sqs_worker.py` para consumir de Kinesis
   - Actualizar `app/api/videos.py` para enviar a Kinesis

3. **Configurar Auto Scaling**:
   - Usar métricas de Kinesis (`IncomingRecords`, `IteratorAgeMilliseconds`)
   - Configurar alarms en CloudWatch

**Nota**: Esta guía se enfoca en SQS porque es más simple y el código ya está implementado. Si necesitas usar Kinesis, puedes adaptar los pasos.

---

## Qué Hacer si No Puedes Crear SQS ni Kinesis

Si no puedes crear ni SQS ni Kinesis, sigue estos pasos:

### 1. Documentar la Restricción

Crea un documento (por ejemplo, `docs/Entrega_4/RESTRICCIONES_CUENTA_ESTUDIANTE.md`) explicando:

```markdown
# Restricciones de Cuenta de Estudiante - Entrega 4

## Problema Encontrado

Mi cuenta de estudiante (voclabs) no tiene permisos para crear recursos SQS.
Error recibido: `AccessDeniedException: User is not authorized to perform: sqs:createqueue`

## Recursos Solicitados al Administrador

1. Cola SQS: `anb-video-processing-queue`
2. Dead Letter Queue: `anb-video-processing-dlq`
3. IAM Roles: `anb-backend-role` y `anb-worker-role`

## Estado Actual

- ✅ Código implementado para usar SQS
- ✅ Workers preparados para consumir de SQS
- ✅ Backend preparado para enviar a SQS
- ⏳ Esperando creación de recursos por administrador

## Implementación en Producción

En un entorno de producción, estos recursos se crearían mediante:
- Infrastructure as Code (Terraform/CloudFormation)
- Permisos IAM apropiados
- Automatización completa del despliegue
```

### 2. Evidenciar que el Código Está Listo

Aunque no puedas crear SQS, puedes demostrar que:

- ✅ El código del backend envía mensajes a SQS (`app/api/videos.py`)
- ✅ El código del worker consume de SQS (`app/workers/sqs_worker.py`)
- ✅ El servicio SQS está implementado (`app/services/sqs_service.py`)
- ✅ La configuración está lista (`app/core/config.py`)

### 3. Probar Localmente (si es posible)

Si tienes acceso a una cuenta AWS de prueba o puedes usar LocalStack:

```bash
# Instalar LocalStack
pip install localstack

# Iniciar LocalStack
localstack start

# Crear cola SQS en LocalStack
aws --endpoint-url=http://localhost:4566 sqs create-queue \
  --queue-name anb-video-processing-queue

# Probar el código localmente con LocalStack
```

### 4. Solicitar al Administrador

Usa el template de email del Paso 6.4 para solicitar los recursos. Incluye:

- **Urgencia**: Explica que es un requisito de la entrega
- **Especificaciones técnicas**: Proporciona todos los detalles
- **Timeline**: Solicita un timeline para la creación

### 5. Plan de Contingencia

Si el administrador no puede crear los recursos a tiempo:

1. **Documenta todo**: Qué intentaste, qué errores recibiste, qué solicitaste
2. **Muestra el código**: Demuestra que el código está implementado y listo
3. **Explica el diseño**: Documenta cómo funcionaría en producción
4. **Alternativa temporal**: Si es posible, usa Redis/Celery temporalmente y documenta que es una solución temporal hasta tener SQS

### 6. Para la Entrega

En tu documentación de entrega, incluye:

- ✅ **Diseño de la arquitectura**: Muestra cómo SQS se integra
- ✅ **Código implementado**: Muestra que el código está listo para SQS
- ✅ **Configuración**: Muestra la configuración de SQS en `.env` y scripts
- ✅ **Documentación de restricciones**: Explica qué restricciones encontraste
- ✅ **Plan de implementación**: Cómo se implementaría en producción

**Nota**: Los profesores entienden las restricciones de cuentas de estudiante. Lo importante es demostrar que:
1. Entiendes cómo funciona SQS
2. Has implementado el código correctamente
3. Has solicitado los recursos necesarios
4. Sabes cómo se implementaría en producción

---

## Solución Temporal: Usar Credenciales

Si no puedes crear IAM Roles y necesitas que el sistema funcione **ahora mismo**, puedes usar credenciales AWS temporales en el `.env`:

### ⚠️ ADVERTENCIA DE SEGURIDAD

- **NO es recomendado para producción**
- Las credenciales temporales expiran (típicamente 1 hora)
- Debes renovarlas manualmente
- **Solo para desarrollo/pruebas**

### Cómo Obtener Credenciales Temporales

1. **Desde la consola de AWS:**
   - Click en tu nombre de usuario (arriba derecha)
   - **"Command line or programmatic access"**
   - Copia los valores de `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, y `AWS_SESSION_TOKEN`

2. **O desde AWS CLI:**
   ```bash
   aws sts get-session-token
   ```

### Configurar en el Worker

En `scripts/aws/worker-sqs-user-data.sh`, descomenta y actualiza las credenciales:

```bash
# AWS Credentials (TEMPORAL - solo si no puedes usar IAM Role)
AWS_ACCESS_KEY_ID=TU_ACCESS_KEY_AQUI
AWS_SECRET_ACCESS_KEY=TU_SECRET_KEY_AQUI
AWS_SESSION_TOKEN=TU_SESSION_TOKEN_AQUI
```

**Nota**: El código ya está preparado para usar credenciales si están disponibles, o IAM Role si no hay credenciales (ver `app/services/sqs_service.py`).

### Configurar en el Backend

En `scripts/aws/backend-user-data.sh`, descomenta y actualiza las credenciales de la misma manera.

### Renovar Credenciales

Las credenciales temporales expiran (típicamente después de 1 hora). Cuando expiren:

#### Opción 1: Script Helper (Recomendado)

El proyecto incluye un script helper para actualizar credenciales fácilmente:

```bash
# En la instancia EC2 del worker
cd /opt/anb-worker
sudo ./scripts/aws/update-worker-credentials.sh \
  ASIA5GE6GSAWJ3OEGRON \
  tqUUtKrCMTluoy0hJwaIAUeVsfcp3Cy2uJhwfpS1 \
  IQoJb3JpZ2luX2VjEK7...
```

Luego reinicia el contenedor:
```bash
sudo docker restart anb-worker-sqs
```

#### Opción 2: Manual

1. **Obtén nuevas credenciales** desde la consola de AWS
2. **Edita el `.env`** en la instancia:
   ```bash
   sudo nano /opt/anb-worker/.env
   ```
3. **Actualiza las líneas:**
   ```bash
   AWS_ACCESS_KEY_ID=nueva_access_key
   AWS_SECRET_ACCESS_KEY=nueva_secret_key
   AWS_SESSION_TOKEN=nuevo_session_token
   ```
4. **Reinicia el servicio:**
   ```bash
   # En el worker
   sudo systemctl restart anb-worker-sqs
   # O reinicia el contenedor directamente
   sudo docker restart anb-worker-sqs
   
   # En el backend
   sudo systemctl restart anb-api
   ```

#### Manejo Automático de Errores

El código ahora detecta automáticamente cuando las credenciales expiran (`InvalidClientTokenId`) e intenta recrear el cliente. Sin embargo, **si las credenciales han expirado, necesitas actualizar el `.env` y reiniciar el contenedor** para que el código pueda leer las nuevas credenciales.

Verás en los logs mensajes como:
```
WARNING: Detected credential error (InvalidClientTokenId), attempting to recreate client...
WARNING: NOTE: If credentials have expired, you need to:
WARNING: 1. Update the .env file on the EC2 instance with new credentials
WARNING: 2. Restart the worker container: docker restart anb-worker-sqs
```

### Solicitar IAM Roles al Administrador

Mientras usas credenciales temporales, **solicita al administrador** que cree los roles IAM. Una vez creados:

1. Asigna el IAM Role a las instancias EC2
2. Elimina las credenciales del `.env`
3. Reinicia los servicios

El código detectará automáticamente que no hay credenciales y usará el IAM Role.
