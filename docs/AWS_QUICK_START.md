# AWS Quick Start Guide - ANB Rising Stars Showcase

## 🚀 Inicio Rápido

Esta es una guía rápida para comenzar con el despliegue en AWS. Para instrucciones detalladas, consulta la [Guía Completa de Despliegue](AWS_DEPLOYMENT_GUIDE.md).

## 📋 Checklist de Recursos AWS

Necesitarás configurar los siguientes recursos en AWS:

### 1. Networking
- [ ] VPC con CIDR `10.0.0.0/16`
- [ ] 3 Subnets públicas (para ALB)
- [ ] 3 Subnets privadas (para EC2, RDS, ElastiCache)
- [ ] Internet Gateway
- [ ] NAT Gateway
- [ ] Route Tables

### 2. Base de Datos
- [ ] RDS PostgreSQL 15.x
- [ ] Subnet Group para RDS
- [ ] Security Group para RDS

### 3. Cache y Message Broker
- [ ] EC2 Redis (t3.small o t3.micro)
- [ ] Security Group para Redis

### 4. Almacenamiento
- [ ] S3 Bucket para videos
- [ ] Carpetas: `uploads/`, `processed_videos/`, `assets/`

### 5. Seguridad
- [ ] Security Groups:
  - [ ] `anb-alb-sg` (HTTP/HTTPS público)
  - [ ] `anb-backend-sg` (puerto 8000 desde ALB)
  - [ ] `anb-worker-sg` (SSH desde tu IP)
  - [ ] `anb-rds-sg` (puerto 5432 desde backend/worker)
  - [ ] `anb-redis-sg` (puerto 6379 desde backend/worker)
- [ ] Credenciales AWS (si no puedes crear IAM roles):
  - [ ] Obtener Access Key ID y Secret Access Key
  - [ ] Configurar en variables de entorno

### 6. Backend (Auto Scaling)
- [ ] AMI para Backend
- [ ] Launch Template
- [ ] Target Group
- [ ] Auto Scaling Group (2-5 instancias)

### 7. Load Balancer
- [ ] Application Load Balancer (ALB)
- [ ] Listener HTTP (puerto 80)
- [ ] Listener HTTPS (puerto 443, opcional)

### 8. Worker
- [ ] Instancia EC2 para Worker (t3.medium o t3.large)

## ⚡ Pasos Rápidos

### Paso 1: Crear VPC y Networking
```bash
# Seguir guía completa: Paso 1
# Tiempo estimado: 30 minutos
```

### Paso 2: Crear RDS
```bash
# Seguir guía completa: Paso 2
# Tiempo estimado: 20 minutos
# Anotar: RDS_ENDPOINT
```

### Paso 3: Crear EC2 Redis
```bash
# Seguir guía completa: Paso 3
# Tiempo estimado: 20 minutos
# Anotar: REDIS_PRIVATE_IP (IP privada de la instancia)
```

### Paso 4: Crear S3 Bucket
```bash
# Seguir guía completa: Paso 4
# Tiempo estimado: 10 minutos
# Anotar: S3_BUCKET_NAME
```

### Paso 5: Configurar Seguridad
```bash
# Seguir guía completa: Pasos 5 y 6
# Tiempo estimado: 30 minutos
```

### Paso 6: Crear AMI y Launch Template
```bash
# Seguir guía completa: Paso 7
# Tiempo estimado: 1 hora
```

### Paso 7: Crear Auto Scaling Group y ALB
```bash
# Seguir guía completa: Pasos 8 y 9
# Tiempo estimado: 30 minutos
# Anotar: ALB_DNS_NAME
```

### Paso 8: Crear Worker
```bash
# Seguir guía completa: Paso 10
# Tiempo estimado: 30 minutos
```

### Paso 9: Configurar Variables de Entorno
```bash
# Usar script: scripts/aws/setup-env.sh
cd scripts/aws
chmod +x setup-env.sh
./setup-env.sh
```

### Paso 10: Probar
```bash
# Verificar health check
curl http://[ALB_DNS_NAME]/health

# Verificar API docs
open http://[ALB_DNS_NAME]/docs
```

## 📝 Variables de Entorno Críticas

Asegúrate de configurar estas variables en tus instancias EC2:

```env
# Database
DATABASE_URL=postgresql://anb_admin:[PASSWORD]@[RDS_ENDPOINT]:5432/anb_db
POSTGRES_HOST=[RDS_ENDPOINT]

# Redis - Use EC2 Redis private IP
REDIS_URL=redis://[REDIS_PRIVATE_IP]:6379/0
CELERY_BROKER_URL=redis://[REDIS_PRIVATE_IP]:6379/0

# S3
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-stars-videos-us-east-1

# AWS Credentials (required if not using IAM roles)
# IMPORTANTE: No commitees estas credenciales al repositorio
AWS_ACCESS_KEY_ID=[TU_ACCESS_KEY_ID]
AWS_SECRET_ACCESS_KEY=[TU_SECRET_ACCESS_KEY]

# Security
SECRET_KEY=[GENERATE_SECURE_KEY]
ENVIRONMENT=production
DEBUG=False
```

## 🔧 Scripts Disponibles

### Generar archivos .env
```bash
cd scripts/aws
chmod +x setup-env.sh
./setup-env.sh
```

### User-data scripts
- `scripts/aws/backend-user-data.sh` - Para Launch Template del backend
- `scripts/aws/worker-user-data.sh` - Para instancia EC2 del worker

## ⏱️ Tiempo Total Estimado

- **Configuración inicial**: 3-4 horas
- **Primera vez**: 4-5 horas (con aprendizaje)
- **Re-despliegue**: 1-2 horas

## 💰 Costos Estimados

- **RDS (db.t3.medium)**: ~$50-70/mes
- **EC2 Redis (t3.small)**: ~$15-20/mes
- **EC2 Backend (t3.medium x 2)**: ~$60/mes
- **EC2 Worker (t3.medium)**: ~$30/mes
- **ALB**: ~$20/mes
- **S3 Storage**: ~$2-3/mes
- **NAT Gateway**: ~$32/mes
- **Total**: ~$234-277/mes

## 📚 Recursos Adicionales

- [Guía Completa de Despliegue](AWS_DEPLOYMENT_GUIDE.md)
- [Scripts de AWS](scripts/aws/README.md)
- [Documentación AWS RDS](https://docs.aws.amazon.com/rds/)
- [Documentación AWS EC2](https://docs.aws.amazon.com/ec2/)
- [Documentación AWS ALB](https://docs.aws.amazon.com/elasticloadbalancing/)

## 🆘 Problemas Comunes

### Health check falla
- Verificar que la app esté en puerto 8000
- Verificar security groups
- Verificar que el endpoint `/health` exista

### No puede conectar a RDS
- Verificar security groups
- Verificar que esté en la misma VPC
- Verificar credenciales

### Worker no procesa tareas
- Verificar conexión a Redis (EC2 Redis)
- Verificar que Redis esté corriendo: `ssh redis && redis-cli ping`
- Verificar logs del worker
- Verificar que el worker esté escuchando la cola correcta
- Verificar que el worker tenga la IP privada correcta de Redis

## ✅ Verificación Final

Antes de considerar el despliegue completo:

- [ ] Health check pasa en el ALB
- [ ] Puedes registrar usuarios
- [ ] Puedes subir videos
- [ ] Los videos se procesan correctamente
- [ ] Los videos procesados están en S3
- [ ] Los logs están disponibles
- [ ] El auto scaling funciona
- [ ] Las alertas están configuradas

---

**¡Listo!** Tu aplicación debería estar desplegada en AWS. 🎉

