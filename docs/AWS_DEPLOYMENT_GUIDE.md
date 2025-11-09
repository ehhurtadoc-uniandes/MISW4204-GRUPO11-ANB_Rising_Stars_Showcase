# Guía de Despliegue en AWS - ANB Rising Stars Showcase

## 📋 Tabla de Contenidos

1. [Prerrequisitos](#prerrequisitos)
2. [Arquitectura AWS](#arquitectura-aws)
3. [Configuración Paso a Paso](#configuración-paso-a-paso)
   - [Paso 1: VPC y Networking](#paso-1-vpc-y-networking)
   - [Paso 2: RDS (PostgreSQL)](#paso-2-rds-postgresql)
   - [Paso 3: EC2 Redis](#paso-3-ec2-redis)
   - [Paso 4: S3 Bucket](#paso-4-s3-bucket)
   - [Paso 5: Security Groups](#paso-5-security-groups)
   - [Paso 6: IAM Roles y Políticas](#paso-6-iam-roles-y-políticas)
   - [Paso 7: AMI y Launch Template (Backend)](#paso-7-ami-y-launch-template-backend)
   - [Paso 8: Auto Scaling Group (Backend)](#paso-8-auto-scaling-group-backend)
   - [Paso 9: Application Load Balancer](#paso-9-application-load-balancer)
   - [Paso 10: EC2 Worker](#paso-10-ec2-worker)
   - [Paso 11: Configuración de la Aplicación](#paso-11-configuración-de-la-aplicación)
4. [Verificación y Testing](#verificación-y-testing)
5. [Monitoreo y Troubleshooting](#monitoreo-y-troubleshooting)
6. [Costos Estimados](#costos-estimados)

---

## Prerrequisitos

- ✅ Cuenta de AWS activa
- ✅ AWS CLI instalado y configurado (`aws configure`)
- ✅ Acceso a la consola de AWS
- ✅ Conocimiento básico de EC2, RDS, S3, VPC
- ✅ Docker y Docker Compose instalados (para construir imágenes)
- ✅ Acceso SSH a instancias EC2

---

## Arquitectura AWS

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │    Balancer (ALB)    │
              └──────────┬────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  EC2    │     │  EC2    │     │  EC2    │
   │ Backend │     │ Backend │     │ Backend │
   │ (ASG)   │     │ (ASG)   │     │ (ASG)   │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │                │
        └───────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   EC2    │   │   S3    │
   │PostgreSQL│    │  Redis   │   │ Bucket  │
   └─────────┘    └──────────┘   └─────────┘
        │               │               
        │               │               
        ▼               ▼               
   ┌─────────┐    ┌──────────┐
   │   EC2   │    │   EC2    │
   │ Worker  │    │ Worker   │
   └─────────┘    └──────────┘
```

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

**Subnets Privadas** (para EC2, RDS, Redis):
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
   - **Monitoring**: Opcional (habilitar Enhanced monitoring si es necesario)
   - **Maintenance**: 
     - **Auto minor version upgrade**: Habilitar
     - **Maintenance window**: Seleccionar ventana preferida
3. Click **Create database**

#### 2.3 Notas Importantes

- **Anotar el Endpoint** de RDS (ejemplo: `anb-postgres.xxxxx.us-east-1.rds.amazonaws.com`)
- El puerto por defecto es `5432`
- Guardar las credenciales en un lugar seguro

---

### Paso 3: EC2 Redis

**Nota**: Según tu arquitectura, Redis va en una instancia EC2 separada. Esto es más económico que ElastiCache y funciona bien para la mayoría de casos.

#### 3.1 Crear Instancia EC2 para Redis

1. **EC2 Dashboard** → **Launch instance**
2. Configuración:
   - **Name**: `anb-redis`
   - **AMI**: Amazon Linux 2023 o Ubuntu Server 22.04 LTS
   - **Instance type**: 
     - Producción: `t3.small` o `t3.medium`
     - Pruebas: `t3.micro` (Free tier)
   - **Key pair**: Crear o seleccionar existente (para acceso SSH)
   - **Network settings**:
     - **VPC**: `anb-vpc`
     - **Subnet**: Cualquier subnet privada (ej: `anb-private-subnet-1a`)
     - **Auto-assign public IP**: Disable (o Enable si necesitas acceso SSH)
     - **Security group**: Crear nuevo `anb-redis-sg` (se configurará después)
   - **Configure storage**: 
     - 20 GB gp3 (suficiente para Redis)
   - **Advanced details**:
     - **User data**: Ver script abajo
3. Click **Launch instance**

#### 3.2 User Data Script para Redis

**Para Ubuntu (recomendado):**
```bash
#!/bin/bash
set -e

# Actualizar sistema
apt update && apt upgrade -y

# Instalar Redis
apt install redis-server -y

# Configurar Redis
cat > /etc/redis/redis.conf << EOF
# Redis configuration file
# Network
bind 0.0.0.0 ::1
port 6379
protected-mode no
tcp-backlog 511
timeout 0
tcp-keepalive 300

# General
daemonize no
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Replication
# replicaof <masterip> <masterport>

# Security
# requirepass foobared

# AOF
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Lazy freeing
lazyfree-lazy-eviction no
lazyfree-lazy-expire no
lazyfree-lazy-server-del no
replica-lazy-flush no

# Threaded I/O
io-threads 4
io-threads-do-reads no
EOF

# Crear directorio de logs
sudo mkdir -p /var/log/redis
sudo chown redis:redis /var/log/redis
sudo chmod 755 /var/log/redis

# Iniciar y habilitar Redis
systemctl restart redis-server
systemctl enable redis-server

# Verificar que Redis esté corriendo
sleep 2
redis-cli ping
# Debe responder: PONG
```

**Para Amazon Linux:**
```bash
#!/bin/bash
set -e

# Actualizar sistema
yum update -y

# Instalar Redis
yum install redis -y

# Configurar Redis
cat > /etc/redis.conf << EOF
# Bind a todas las interfaces (dentro de la VPC)
bind 0.0.0.0

# Puerto por defecto
port 6379

# Protección con contraseña (opcional pero recomendado)
# requirepass [TU_PASSWORD_AQUI]

# Persistencia
save 900 1
save 300 10
save 60 10000

# AOF (Append Only File)
appendonly yes
appendfsync everysec

# Logs
loglevel notice
logfile /var/log/redis/redis-server.log
EOF

# Crear directorio de logs
mkdir -p /var/log/redis
chown redis:redis /var/log/redis

# Iniciar y habilitar Redis
systemctl start redis
systemctl enable redis

# Verificar que Redis esté corriendo
redis-cli ping
# Debe responder: PONG
```

#### 3.3 Configurar Redis para Persistencia

Después de lanzar la instancia, conéctate vía SSH y configura:

```bash
# Conectar a la instancia
ssh -i tu-key.pem ec2-user@<IP_PRIVADA_REDIS>

# Editar configuración de Redis
sudo nano /etc/redis.conf

# Verificar que Redis esté corriendo
redis-cli ping

# Obtener IP privada de la instancia
hostname -I
```

#### 3.4 Notas Importantes

- **Anotar la IP Privada** de la instancia Redis (ej: `10.0.10.50`)
- El puerto es `6379`
- Para conectar desde EC2, usar el formato: `redis://<IP_PRIVADA>:6379/0`
- Redis debe estar en la misma VPC que las demás instancias
- Considera usar un Elastic IP si necesitas una IP fija

---

### Paso 4: S3 Bucket

#### 4.1 Crear S3 Bucket

1. **S3 Dashboard** → **Create bucket**
2. Configuración:
   - **Bucket name**: `anb-rising-stars-videos-[tu-region]` (debe ser único globalmente)
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

#### 4.1.1 Configurar Bucket Policy para Lectura Pública

**⚠️ IMPORTANTE**: 
- Aún necesitarás credenciales AWS para **subir** (PUT) y **eliminar** (DELETE) videos
- Solo la **lectura** (GET) será pública
- Los usuarios podrán ver los videos sin credenciales

**Pasos para hacer el bucket público para lectura:**

1. **Bucket** → **Permissions** → **Bucket policy** → **Edit**
2. Agregar esta política (permite lectura pública de todo el bucket):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::anb-rising-starts-videos-east1/*"
        }
    ]
}
```

**Nota**: 
- ✅ Los usuarios pueden ver videos sin credenciales
- ✅ URLs directas a los videos: `https://bucket.s3.region.amazonaws.com/processed_videos/video.mp4`
- ❌ Aún necesitas credenciales para que tu aplicación suba/elimine videos
- ⚠️ Cualquiera con la URL puede ver el video (aceptable si los videos son públicos por diseño)

#### 4.2 Crear Carpetas en el Bucket

Crear las siguientes carpetas (prefixes):
- `uploads/` - Videos originales
- `processed_videos/` - Videos procesados
- `assets/` - Assets estáticos (logo ANB, etc.)

**Pasos:**
1. Abrir el bucket
2. Click **Create folder**
3. Crear cada carpeta mencionada

#### 4.3 Configurar CORS (si es necesario)

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

### Paso 5: Security Groups

#### 5.1 Security Group para RDS (`anb-rds-sg`)

1. **EC2 Dashboard** → **Security Groups** → **Create security group**
2. Configuración:
   - **Name**: `anb-rds-sg`
   - **Description**: Security group for ANB RDS PostgreSQL
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: PostgreSQL
     - **Port**: 5432
     - **Source**: `anb-backend-sg` (se creará después)
   - **Outbound rules**: Default (All traffic)
3. Click **Create security group**

#### 5.2 Security Group para Redis (`anb-redis-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-redis-sg`
   - **Description**: Security group for ANB Redis EC2
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: Custom TCP
     - **Port**: 6379
     - **Source**: `anb-backend-sg`
     - **Type**: Custom TCP
     - **Port**: 6379
     - **Source**: `anb-worker-sg`
     - **Type**: SSH
     - **Port**: 22
     - **Source**: Tu IP pública (para acceso SSH)
   - **Outbound rules**: Default
3. Click **Create security group**

#### 5.3 Security Group para Backend (`anb-backend-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-backend-sg`
   - **Description**: Security group for ANB Backend API
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: Custom TCP
     - **Port**: 8000
     - **Source**: `anb-alb-sg` (se creará después)
   - **Outbound rules**:
     - **Type**: All traffic
     - **Destination**: 0.0.0.0/0
3. Click **Create security group**

#### 5.4 Security Group para ALB (`anb-alb-sg`)

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

#### 5.5 Security Group para Worker (`anb-worker-sg`)

1. Crear nuevo security group
2. Configuración:
   - **Name**: `anb-worker-sg`
   - **Description**: Security group for ANB Celery Worker
   - **VPC**: `anb-vpc`
   - **Inbound rules**:
     - **Type**: SSH
     - **Port**: 22
     - **Source**: Tu IP pública (para acceso SSH)
   - **Outbound rules**:
     - **Type**: All traffic
     - **Destination**: 0.0.0.0/0
3. Click **Create security group**

#### 5.6 Actualizar Security Groups Existentes

**Actualizar `anb-rds-sg`:**
- Agregar regla para permitir acceso desde `anb-worker-sg` (puerto 5432)

**Nota**: `anb-redis-sg` ya debe tener acceso desde `anb-worker-sg` si configuraste correctamente el paso 5.2

---

### Paso 6: Configurar Credenciales AWS para S3 (Solo Escritura)

**Nota**: Como el bucket es público para lectura, solo necesitas credenciales para **subir** (PUT) y **eliminar** (DELETE) videos. No necesitas permisos de lectura (GET).

#### 6.1 Opción: Usar Credenciales Existentes

Si ya tienes credenciales AWS con permisos S3, puedes usarlas directamente.

**⚠️ IMPORTANTE**: 
- **NUNCA** commitees credenciales en el código
- Guarda las credenciales en variables de entorno (archivo `.env`)
- Usa credenciales con permisos mínimos (solo escritura en S3)

#### 6.2 Permisos Mínimos Necesarios (Solo Escritura)

Como el bucket es público, solo necesitas permisos para escribir:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::anb-rising-stars-videos-*/*",
                "arn:aws:s3:::anb-rising-stars-videos-*"
            ]
        }
    ]
}
```

**Nota**: No necesitas `s3:GetObject` porque el bucket es público.

#### 6.3 Configurar Variables de Entorno

Las credenciales se configurarán en las variables de entorno de las instancias EC2:

```env
# AWS Credentials (solo para escritura en S3)
AWS_ACCESS_KEY_ID=[TU_ACCESS_KEY_ID]
AWS_SECRET_ACCESS_KEY=[TU_SECRET_ACCESS_KEY]
```

**Obtener credenciales**:
- Si tienes AWS CLI configurado: `aws configure list`
- Si puedes crear usuarios IAM: Crear usuario con política mínima de escritura
- Si no: Usar credenciales existentes con permisos S3

---

### Paso 7: AMI y Launch Template (Backend)

#### 7.1 Preparar Instancia EC2 para AMI

1. **EC2 Dashboard** → **Launch instance**
2. Configuración:
   - **Name**: `anb-backend-ami-builder`
   - **AMI**: Amazon Linux 2023 o Ubuntu Server 22.04 LTS
   - **Instance type**: `t3.micro` (suficiente para crear AMI)
   - **Key pair**: Crear o seleccionar existente
   - **Network settings**:
     - **VPC**: `anb-vpc`
     - **Subnet**: Cualquier subnet pública (temporal)
     - **Auto-assign public IP**: Enable
     - **Security group**: `anb-backend-sg` (temporalmente permitir SSH desde tu IP)
   - **Configure storage**: 20 GB gp3
   - **IAM instance profile**: (Opcional - dejar vacío si no tienes permisos)
3. Click **Launch instance**

#### 7.2 Conectar a la Instancia y Configurar

```bash
# Conectar via SSH a tu instancia EC2
ssh -i tu-key.pem ec2-user@<IP_PUBLICA>

# Actualizar sistema
sudo yum update -y  # Amazon Linux
# o
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Instalar Docker
sudo yum install docker -y  # Amazon Linux
# o
sudo apt install docker.io -y  # Ubuntu
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clonar repositorio
git clone https://github.com/ehhurtadoc-uniandes/MISW4204-GRUPO11-ANB_Rising_Stars_Showcase.git /opt/anb-api
cd /opt/anb-api

# ============================================
# PASO IMPORTANTE: Crear archivo .env
# ============================================
# El archivo .env va DENTRO de la instancia EC2
# Ruta: /opt/anb-api/.env
sudo vim /opt/anb-api/.env
```

**Contenido del archivo `.env` (con tus valores reales):**

**⚠️ IMPORTANTE - Generar SECRET_KEY primero:**
```bash
# En Linux/Mac o Git Bash en Windows:
openssl rand -hex 32

# O en PowerShell (Windows):
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# O usar Python:
python -c "import secrets; print(secrets.token_hex(32))"
```

**Ejemplo de SECRET_KEY generada:** `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2`

**Ahora crea el archivo `.env` con estos valores:**

```env
# Database (RDS)
DATABASE_URL=postgresql://anb_user:anb_password@anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com:5432/anbdb
POSTGRES_HOST=anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=anb_user
POSTGRES_PASSWORD=anb_password
POSTGRES_DB=anbdb

# Redis (EC2 Redis - IP privada)
REDIS_URL=redis://10.0.131.51:6379/0
CELERY_BROKER_URL=redis://10.0.131.51:6379/0
CELERY_RESULT_BACKEND=redis://10.0.131.51:6379/0

# JWT Configuration
SECRET_KEY=6da78a1c9d50ebc82c4022c07994f21e7618dd73d9fca80fb2ef7f74c42adea2
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3 Storage (bucket público para lectura)
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-starts-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/

# AWS Credentials (solo para escritura - bucket es público para lectura)
# IMPORTANTE: Reemplazar con tus credenciales reales
# IMPORTANTE: No commitees estas credenciales al repositorio
# NOTA: Si las credenciales empiezan con "ASIA", son temporales y requieren AWS_SESSION_TOKEN
AWS_ACCESS_KEY_ID=REEMPLAZAR_CON_TU_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=REEMPLAZAR_CON_TU_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN=REEMPLAZAR_CON_TU_SESSION_TOKEN_SI_LAS_CREDENCIALES_SON_TEMPORALES

# Environment
ENVIRONMENT=production
DEBUG=False

# File Storage (fallback local)
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100

# ANB Configuration
ANB_LOGO_PATH=/app/assets/anb_logo.png
VIDEO_MAX_DURATION=30
VIDEO_RESOLUTION=720p
```

**Pasos para crear el archivo:**
1. Genera el SECRET_KEY usando uno de los comandos de arriba
2. Copia el contenido del template de arriba
3. Reemplaza `REEMPLAZAR_CON_TU_SECRET_KEY_GENERADA` con el SECRET_KEY que generaste
4. Reemplaza `[TU_ACCESS_KEY_ID]` y `[TU_SECRET_ACCESS_KEY]` con tus credenciales AWS
5. Guarda el archivo en `/opt/anb-api/.env`

#### 7.3 Crear Script de Inicio

```bash
# Crear script de inicio
sudo nano /opt/anb-api/start-backend.sh
```

**Contenido del script:**
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

# Ejecutar migraciones (contenedor temporal que se elimina después)
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
```

```bash
sudo chmod +x /opt/anb-api/start-backend.sh
```

#### 7.4 Configurar Systemd Service (Para que la app inicie automáticamente)

**¿Qué es systemd?**
- Es el sistema de servicios de Linux
- Permite que tu aplicación inicie automáticamente cuando la instancia se reinicia
- El archivo va en: `/etc/systemd/system/anb-api.service`

**Pasos:**

```bash
# Crear el archivo de servicio systemd
sudo nano /etc/systemd/system/anb-api.service
```

**Contenido del archivo** (copia y pega esto):
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

**Guardar y activar el servicio:**
```bash
# Recargar systemd para que reconozca el nuevo servicio
sudo systemctl daemon-reload

# Habilitar el servicio para que inicie automáticamente
sudo systemctl enable anb-api

# Iniciar el servicio ahora
sudo systemctl start anb-api

# Verificar que esté corriendo
sudo systemctl status anb-api
```

**Resumen de ubicaciones:**
- ✅ Archivo `.env`: `/opt/anb-api/.env` (dentro de la instancia EC2)
- ✅ Archivo systemd: `/etc/systemd/system/anb-api.service` (dentro de la instancia EC2)
- ✅ Código de la app: `/opt/anb-api/` (dentro de la instancia EC2)

#### 7.5 Crear AMI desde la Instancia

1. **EC2 Dashboard** → Seleccionar la instancia
2. **Actions** → **Image and templates** → **Create image**
3. Configuración:
   - **Image name**: `anb-backend-ami-v1`
   - **Image description**: AMI for ANB Backend API
   - **No reboot**: Desmarcar (recomendado)
4. Click **Create image**
5. Esperar a que el proceso termine (puede tomar 10-15 minutos)

#### 7.6 Crear Launch Template

1. **EC2 Dashboard** → **Launch Templates** → **Create launch template**
2. Configuración:
   - **Name**: `anb-backend-launch-template`
   - **Template version description**: Initial version
   - **AMI**: Seleccionar la AMI creada (`anb-backend-ami-v1`)
   - **Instance type**: `t3.medium` o `t3.small` (ajustar según necesidad)
   - **Key pair**: Tu key pair
   - **Network settings**:
     - **Subnet**: No incluir (se configurará en ASG)
     - **Security groups**: `anb-backend-sg`
   - **Storage**: 20 GB gp3
   - **IAM instance profile**: (Opcional - dejar vacío si no tienes permisos)
   - **Advanced details**:
     - **User data**: Script opcional si necesitas configuración adicional
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
     - **Advanced health check settings**: Ajustar según necesidad
3. Click **Next**
4. **Registrar destinos (Paso 2)**: 
   - ⚠️ **NO selecciones ninguna instancia** (deja el Target Group vacío)
   - El AMI builder NO debe registrarse aquí
   - Las instancias del Auto Scaling Group se registrarán automáticamente cuando se lancen
   - Click **Next** o **Skip**
5. Revisar y click **Create target group**

#### 8.2 Crear Auto Scaling Group

1. **EC2 Dashboard** → **Auto Scaling Groups** → **Create Auto Scaling group**
2. Configuración:
   - **Name**: `anb-backend-asg`
   - **Launch template**: `anb-backend-launch-template`
   - **Version**: Latest
   - Click **Next**
   - **VPC**: `anb-vpc`
   - **Subnets**: Seleccionar las 3 subnets privadas
   - Click **Next**
   - **Load balancing**:
     - **Attach to an existing load balancer**: Yes
     - **Target group**: `anb-backend-tg`
     - **Health check type**: ELB
     - **Health check grace period**: 300 segundos
   - Click **Next**
   - **Group size**:
     - **Desired capacity**: 2
     - **Minimum capacity**: 2
     - **Maximum capacity**: 5
   - Click **Next**
   - **Scaling policies**:
     - **Target tracking scaling policy**:
       - **Metric type**: Average CPU utilization
       - **Target value**: 70%
     - Agregar otra política para memoria si es necesario
   - Click **Next**
   - **Add notifications**: Opcional (SNS para alertas)
   - Click **Next**
   - **Tags**: Agregar tags si es necesario
   - Click **Next**
   - Revisar y click **Create Auto Scaling group**

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
   - Click **Next**
   - **Listeners and routing**:
     - **Protocol**: HTTP
     - **Port**: 80
     - **Default action**: Forward to `anb-backend-tg`
   - Click **Next**
   - Revisar y click **Create load balancer**

#### 9.2 Configurar Listener HTTPS (Opcional pero Recomendado)

**⚠️ Requisito previo:** Para usar HTTPS necesitas un certificado SSL. Para obtener un certificado en ACM necesitas un **dominio válido** (ej: `example.com`, `www.example.com`). Si no tienes un dominio propio, puedes omitir este paso y usar solo HTTP.

**Si tienes un dominio:**

1. **Obtener certificado SSL en ACM:**
   - Ve a **AWS Certificate Manager** → **Request certificate**
   - **Domain name**: Ingresa tu dominio completo (ej: `anbstartvideos.com` o `www.anbstartvideos.com`)
   - **Validation method**: DNS validation (recomendado) o Email validation
   - Click **Request**
   - Si elegiste DNS validation, agrega los registros CNAME que te proporciona ACM a tu DNS
   - Espera a que el certificado se valide (puede tomar unos minutos)

2. **Agregar listener HTTPS al ALB:**
   - En la consola de EC2, selecciona tu ALB (`anb-alb`)
   - Ve a la pestaña **"Agentes de escucha y reglas"** (Listeners and rules)
   - Click en el botón azul **"Agregar agente de escucha"** (Add listener)
   - Configuración:
     - **Protocolo (Protocol)**: ⚠️ **Cambia de "HTTP" a "HTTPS"** en el dropdown
     - **Puerto (Port)**: 443
     - **Acción predeterminada (Default action)**: Forward to `anb-backend-tg`
     - **Default SSL certificate**: Selecciona el certificado que creaste en ACM
   - Click **Add** para crear el listener

**Si NO tienes un dominio:**
- Puedes dejar solo el listener HTTP (puerto 80) por ahora
- El ALB funcionará correctamente con HTTP
- Puedes agregar HTTPS después cuando tengas un dominio y certificado

#### 9.3 Obtener DNS del ALB

1. Seleccionar el ALB
2. Copiar el **DNS name** (ej: `anb-alb-123456789.us-east-1.elb.amazonaws.com`)
3. Este será el endpoint público de tu aplicación

#### 9.4 Acceder a Swagger/OpenAPI Documentation

Una vez que el ALB esté configurado y las instancias estén saludables, puedes acceder a la documentación de la API:

**Swagger UI (Interfaz interactiva):**
```
http://<ALB-DNS>/docs
```
Ejemplo: `http://anb-alb-123456789.us-east-1.elb.amazonaws.com/docs`

**ReDoc (Documentación alternativa):**
```
http://<ALB-DNS>/redoc
```

**OpenAPI Schema (JSON):**
```
http://<ALB-DNS>/openapi.json
```

**Nota:** Swagger está habilitado en producción por defecto. Si no puedes acceder:
- Verifica que las instancias del Target Group estén "Healthy"
- Verifica que el Security Group del ALB permita tráfico HTTP (puerto 80) desde tu IP
- Verifica que el Target Group esté configurado correctamente (puerto 8000)

---

### Paso 10: EC2 Worker

#### 10.1 Crear Instancia EC2 para Worker

1. **EC2 Dashboard** → **Launch instance**
2. Configuración:
   - **Name**: `anb-worker`
   - **AMI**: Amazon Linux 2023 o Ubuntu Server 22.04 LTS
   - **Instance type**: `t3.medium` o `t3.large` (para procesamiento de video)
   - **Key pair**: Tu key pair
   - **Network settings**:
     - **VPC**: `anb-vpc`
     - **Subnet**: Cualquier subnet privada
     - **Auto-assign public IP**: Disable (o Enable si necesitas acceso SSH)
     - **Security group**: `anb-worker-sg`
   - **Configure storage**: 
     - 30-50 GB gp3 (para almacenamiento temporal de videos)
   - **IAM instance profile**: (Opcional - dejar vacío si no tienes permisos)
   - **Advanced details**:
     - **User data**: Ver script abajo
3. Click **Launch instance**

#### 10.2 User Data Script para Worker

```bash
#!/bin/bash
set -e

# Detect OS and set user
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        OS_USER="ubuntu"
        PACKAGE_MANAGER="apt"
    elif [[ "$ID" == "amzn" ]]; then
        OS_USER="ec2-user"
        PACKAGE_MANAGER="yum"
    else
        OS_USER="ubuntu"
        PACKAGE_MANAGER="apt"
    fi
else
    OS_USER="ubuntu"
    PACKAGE_MANAGER="apt"
fi

echo "Detected OS user: $OS_USER"

# Update system and install Docker based on OS
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    apt update && apt upgrade -y
    apt install docker.io git -y
    systemctl start docker
    systemctl enable docker
elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
    yum update -y
    yum install docker git -y
    systemctl start docker
    systemctl enable docker
fi

# Add user to docker group
usermod -aG docker $OS_USER

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Crear directorio de aplicación
mkdir -p /opt/anb-worker
cd /opt/anb-worker

# Clonar repositorio (ajustar URL)
git clone https://github.com/ehhurtadoc-uniandes/MISW4204-GRUPO11-ANB_Rising_Stars_Showcase.git .

# Crear archivo .env
cat > .env << EOF
# Database (RDS)
DATABASE_URL=postgresql://anb_user:anb_password@anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com:5432/anbdb
POSTGRES_HOST=anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=anb_user
POSTGRES_PASSWORD=anb_password
POSTGRES_DB=anbdb

# Redis (EC2 Redis - IP privada)
REDIS_URL=redis://10.0.135.240:6379/0
CELERY_BROKER_URL=redis://10.0.135.240:6379/0
CELERY_RESULT_BACKEND=redis://10.0.135.240:6379/0

# JWT Configuration
SECRET_KEY=6da78a1c9d50ebc82c4022c07994f21e7618dd73d9fca80fb2ef7f74c42adea2
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3 Storage (bucket público para lectura)
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-starts-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/

# AWS Credentials (solo para escritura - bucket es público para lectura)
# NOTA: Si las credenciales empiezan con "ASIA", son temporales y requieren AWS_SESSION_TOKEN
AWS_ACCESS_KEY_ID=a
AWS_SECRET_ACCESS_KEY=a
AWS_SESSION_TOKEN=a


# Environment
ENVIRONMENT=production
DEBUG=False

# File Storage (fallback local)
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100

# ANB Configuration
ANB_LOGO_PATH=/app/assets/anb_logo.png
VIDEO_MAX_DURATION=30
VIDEO_RESOLUTION=720p
EOF

# Crear script de inicio del worker
cat > start-worker.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

cd /opt/anb-worker

# Esperar a que Docker esté listo
until docker info > /dev/null 2>&1; do
    echo "Waiting for Docker..."
    sleep 2
done

# Detener contenedor existente si existe
docker stop anb-worker || true
docker rm anb-worker || true

# Construir imagen si no existe
if ! docker images | grep -q "anb-worker"; then
    echo "Building Docker image..."
    docker build -t anb-worker:latest .
fi

# Ejecutar worker
echo "Starting worker container..."
docker run -d --name anb-worker \
  --env-file .env \
  --restart unless-stopped \
  anb-worker:latest \
  celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --queues=video_queue

echo "Worker service started successfully!"

# Monitorear el contenedor para que systemd no lo detenga
while true; do
    if ! docker ps | grep -q "anb-worker"; then
        echo "Container anb-worker stopped unexpectedly"
        exit 1
    fi
    sleep 10
done
EOFSCRIPT

chmod +x start-worker.sh

# Crear servicio systemd para auto-restart
cat > /etc/systemd/system/anb-worker.service << 'EOFSERVICE'
[Unit]
Description=ANB Worker Service
After=docker.service network-online.target
Requires=docker.service network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/anb-worker
ExecStart=/opt/anb-worker/start-worker.sh
ExecStop=/usr/bin/docker stop anb-worker
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

systemctl daemon-reload
systemctl enable anb-worker
systemctl start anb-worker
```

#### 10.3 Conectar y Configurar Manualmente (si es necesario)

```bash
# Si la instancia no tiene IP pública, usar bastion host o VPN
# O habilitar temporalmente IP pública

# Conectar via SSH
ssh -i tu-key.pem ec2-user@<IP_PRIVADA>

# Editar .env con valores reales
sudo nano /opt/anb-worker/.env

# Reiniciar worker
sudo systemctl restart anb-worker

# Ver logs
sudo journalctl -u anb-worker -f
# o
sudo docker logs anb-worker -f
```

---

### Paso 11: Configuración de la Aplicación

#### 11.1 Actualizar Configuración para S3

Necesitas modificar el código para usar S3 en lugar de almacenamiento local. Ver sección de [Integración con S3](#integración-con-s3) más abajo.

#### 11.2 Variables de Entorno Críticas

Asegúrate de que todas las instancias EC2 tengan las siguientes variables configuradas correctamente:

```env
# Database (RDS)
DATABASE_URL=postgresql://anb_user:anb_password@anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com:5432/anbdb
POSTGRES_HOST=anb-db.c4lgkryqdvqm.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=anb_user
POSTGRES_PASSWORD=anb_password
POSTGRES_DB=anbdb

# Redis (EC2 Redis - IP privada)
REDIS_URL=redis://10.0.150.236:6379/0
CELERY_BROKER_URL=redis://10.0.150.236:6379/0
CELERY_RESULT_BACKEND=redis://10.0.150.236:6379/0

# JWT Configuration
SECRET_KEY=37d992755f862decf49e12892a928e4e71bf545cbcc17b8dc68e300ce9bcf786
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3 Storage (bucket público para lectura)
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-starts-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/

# AWS Credentials (solo para escritura - bucket es público para lectura)
AWS_ACCESS_KEY_ID=REEMPLAZAR_CON_TU_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=REEMPLAZAR_CON_TU_SECRET_ACCESS_KEY

# Environment
ENVIRONMENT=production
DEBUG=False

# File Storage (fallback local)
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100

# ANB Configuration
ANB_LOGO_PATH=/app/assets/anb_logo.png
VIDEO_MAX_DURATION=30
VIDEO_RESOLUTION=720p
```

#### 11.3 Ejecutar Migraciones de Base de Datos

```bash
# Conectar a una instancia EC2 del backend
ssh -i tu-key.pem ec2-user@<IP_INSTANCIA>

# Ejecutar migraciones
cd /opt/anb-api
docker exec -it anb-api alembic upgrade head
```

---

## Integración con S3

El código ya está preparado para usar S3. Con el bucket público para lectura, el código puede usar URLs directas en lugar de presignadas.

**Cómo funciona con bucket público**:
- Para **leer** videos: URLs directas (no necesitas credenciales)
- Para **subir** videos: Aún necesitas credenciales (PUT requiere autenticación)
- Para **eliminar** videos: Aún necesitas credenciales (DELETE requiere autenticación)

**Nota**: El código en `app/services/file_storage.py` ya está configurado para usar S3 cuando `STORAGE_TYPE=cloud`. Si el bucket es público, puedes modificar `get_file_path` para devolver URLs directas:

```python
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import os

class S3FileStorage(FileStorageInterface):
    """S3 storage implementation"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket_name = settings.s3_bucket_name
        self.upload_prefix = settings.s3_upload_prefix
        self.processed_prefix = settings.s3_processed_prefix
    
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        """Save file to S3"""
        if directory == 'uploads':
            key = f"{self.upload_prefix}{filename}"
        elif directory == 'processed_videos':
            key = f"{self.processed_prefix}{filename}"
        else:
            key = f"{directory}/{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data
            )
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            raise Exception(f"Error uploading to S3: {str(e)}")
    
    def get_file_path(self, filename: str, directory: str) -> str:
        """Get S3 file URL"""
        if directory == 'uploads':
            key = f"{self.upload_prefix}{filename}"
        else:
            key = f"{self.processed_prefix}{filename}"
        
        # Generar URL presignada (válida por 1 hora)
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=3600
            )
            return url
        except ClientError as e:
            raise Exception(f"Error generating S3 URL: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            # Extraer key del path
            if file_path.startswith('s3://'):
                key = file_path.replace(f's3://{self.bucket_name}/', '')
            else:
                key = file_path
            
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            if file_path.startswith('s3://'):
                key = file_path.replace(f's3://{self.bucket_name}/', '')
            else:
                key = file_path
            
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
```

Actualizar `app/services/file_storage.py` para usar S3 cuando `STORAGE_TYPE=cloud`.

---

## Verificación y Testing

### 1. Verificar Health Checks

```bash
# Verificar ALB health
curl http://[ALB_DNS_NAME]/health

# Verificar directamente una instancia backend
curl http://[PRIVATE_IP_INSTANCE]:8000/health
```

### 2. Verificar Conexión a RDS

```bash
# Desde una instancia EC2
psql -h [RDS_ENDPOINT] -U anb_admin -d anb_db
```

### 3. Verificar Conexión a Redis

```bash
# Desde una instancia EC2
redis-cli -h [REDIS_PRIVATE_IP] -p 6379
PING
# Debe responder: PONG
```

### 4. Verificar S3

```bash
# Desde una instancia EC2
aws s3 ls s3://anb-rising-stars-videos-us-east-1/
```

### 5. Probar Endpoints de la API

```bash
# Registro de usuario
curl -X POST http://[ALB_DNS_NAME]/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# Login
curl -X POST http://[ALB_DNS_NAME]/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass123"}'
```

---

## Monitoreo y Troubleshooting

### CloudWatch Logs

1. **EC2 Dashboard** → **Instances** → Seleccionar instancia
2. **Monitoring** tab → Ver métricas
3. Configurar CloudWatch Logs Agent en las instancias para logs centralizados

### Verificar Logs de la Aplicación

```bash
# Backend
ssh -i tu-key.pem ec2-user@<IP>
sudo docker logs anb-api -f

# Worker
ssh -i tu-key.pem ec2-user@<IP_WORKER>
sudo docker logs anb-worker -f
```

### Problemas Comunes

**1. Instancias no pasan health check (Request timed out / Unhealthy)**

**Síntomas:**
- Target Group muestra instancias como "Unhealthy"
- Status details: "Request timed out"
- Health check falla

**Causas comunes y soluciones:**

a) **Target Group configurado con puerto incorrecto:**
   - ⚠️ **Problema**: Target Group está en puerto 80, pero la app está en puerto 8000
   - **Solución**: 
     1. Ve a **EC2 Dashboard** → **Target Groups** → Selecciona `anb-backend-tg`
     2. Click en **Attributes** tab → **Edit**
     3. Cambia el **Port** de 80 a **8000**
     4. Guarda los cambios
     5. Espera unos minutos para que los health checks se actualicen

b) **Security Group no permite tráfico desde ALB:**
   - Verificar que `anb-backend-sg` permita tráfico en puerto 8000 desde `anb-alb-sg`
   - Regla necesaria: Inbound TCP 8000 desde Security Group `anb-alb-sg`

c) **Aplicación no está corriendo:**
   - SSH a la instancia: `ssh -i key.pem ubuntu@<IP>`
   - Verificar contenedor: `docker ps`
   - Verificar logs: `docker logs anb-api`
   - Verificar servicio: `systemctl status anb-api`

d) **Health check path incorrecto:**
   - Verificar que el endpoint `/health` exista en la aplicación
   - O cambiar el health check path a `/docs` o `/` en el Target Group

e) **Aplicación no está escuchando en 0.0.0.0:**
   - Verificar que uvicorn esté configurado con `--host 0.0.0.0`
   - Verificar el script `start-backend.sh` en `/opt/anb-api/`

**2. No puede conectar a RDS**
- Verificar security group de RDS
- Verificar que la instancia esté en la misma VPC
- Verificar credenciales

**3. Worker no procesa tareas**
- Verificar conexión a Redis
- Verificar que el worker esté escuchando la cola correcta
- Verificar logs del worker

---

## Costos Estimados (Mensual)

**Nota**: Estos son estimados aproximados. Los costos reales dependen del uso.

- **RDS (db.t3.medium)**: ~$50-70/mes
- **EC2 Redis (t3.small)**: ~$15-20/mes
- **EC2 Backend (t3.medium x 2)**: ~$60/mes
- **EC2 Worker (t3.medium)**: ~$30/mes
- **ALB**: ~$20/mes
- **S3 Storage (100GB)**: ~$2-3/mes
- **Data Transfer**: Variable
- **NAT Gateway**: ~$32/mes + data transfer

**Total estimado**: ~$209-235/mes (sin considerar data transfer y uso variable)

---

## Próximos Pasos

1. ✅ Configurar dominio personalizado con Route 53
2. ✅ Configurar SSL/TLS con ACM
3. ✅ Implementar backup automático de RDS
4. ✅ Configurar CloudWatch Alarms
5. ✅ Implementar CI/CD con CodePipeline
6. ✅ Configurar WAF para seguridad adicional
7. ✅ Implementar CloudFront para CDN

---

## Recursos Adicionales

- [Documentación AWS RDS](https://docs.aws.amazon.com/rds/)
- [Documentación AWS EC2](https://docs.aws.amazon.com/ec2/)
- [Documentación AWS ALB](https://docs.aws.amazon.com/elasticloadbalancing/)
- [Documentación AWS Auto Scaling](https://docs.aws.amazon.com/autoscaling/)

