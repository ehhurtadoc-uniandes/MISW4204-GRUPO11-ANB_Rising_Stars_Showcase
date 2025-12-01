# Plan de Migración: IaaS → PaaS (Entrega 4 → Entrega 5)

## 📋 Resumen

Este documento describe el plan de migración de la aplicación ANB Rising Stars Showcase desde un modelo **IaaS (Infrastructure as a Service)** con EC2 y Auto Scaling Groups hacia un modelo **PaaS (Platform as a Service)** utilizando Amazon ECS con Fargate.

---

## 🎯 Objetivos de la Migración

1. **Reducir complejidad operacional**: Eliminar gestión de AMIs, Launch Templates, Auto Scaling Groups
2. **Simplificar escalado**: Usar ECS Service Auto Scaling en lugar de ASG
3. **Reducir costos base**: Aprovechar modelo serverless de Fargate
4. **Acelerar despliegues**: Actualizaciones más rápidas sin crear nuevas AMIs
5. **Evaluar beneficios**: Comparar IaaS vs PaaS para el caso de uso

---

## 📊 Comparación: Antes (IaaS) vs Después (PaaS)

### Arquitectura

| Componente | Entrega 4 (IaaS) | Entrega 5 (PaaS) |
|------------|------------------|------------------|
| **Capa Web** | EC2 Instances (t3.small) en ASG | ECS Tasks (Fargate) en Service |
| **Capa Worker** | EC2 Instances (t3.small) en ASG | ECS Tasks (Fargate) en Service |
| **Balanceador** | Application Load Balancer | Application Load Balancer (igual) |
| **Base de Datos** | RDS PostgreSQL Multi-AZ | RDS PostgreSQL Multi-AZ (igual) |
| **Almacenamiento** | S3 Bucket | S3 Bucket (igual) |
| **Mensajería** | SQS Queue | SQS Queue (igual) |
| **Monitoreo** | CloudWatch + logs en EC2 | CloudWatch Logs (integrado) |

### Gestión de Infraestructura

| Aspecto | Entrega 4 (IaaS) | Entrega 5 (PaaS) |
|---------|------------------|------------------|
| **Servidores** | Gestión manual (AMI, Launch Templates) | AWS gestiona (Fargate) |
| **Actualizaciones** | Crear nueva AMI → Actualizar Launch Template → ASG | Actualizar Task Definition → Redeploy Service |
| **Escalado** | ASG con CloudWatch Alarms | ECS Service Auto Scaling |
| **Logs** | SSH a instancias o CloudWatch Agent | CloudWatch Logs automático |
| **Debugging** | SSH a instancias EC2 | Solo logs de CloudWatch |

### Costos

| Recurso | Entrega 4 (IaaS) | Entrega 5 (PaaS) |
|---------|------------------|------------------|
| **Capa Web** | ~$30-75/mes (2-5 instancias t3.small) | ~$15-30/mes (2-5 tasks Fargate 0.5vCPU) |
| **Capa Worker** | ~$15-45/mes (1-3 instancias t3.small) | ~$30-90/mes (1-3 tasks Fargate 1vCPU) |
| **RDS** | ~$150/mes (db.t3.medium Multi-AZ) | ~$15/mes (db.t3.micro) |
| **ALB** | ~$16/mes | ~$16/mes |
| **S3** | ~$5-20/mes | ~$5-20/mes |
| **SQS** | ~$0.40/millón requests | ~$0.40/millón requests |
| **CloudWatch** | ~$10-20/mes | ~$5-10/mes |
| **NAT Gateway** | ~$32/mes | ~$32/mes |
| **Total** | ~$260-360/mes | ~$85-190/mes |

**Nota**: Los costos de Entrega 5 son menores principalmente porque:
- Fargate cobra solo por recursos usados (no por instancias completas)
- RDS usa db.t3.micro en lugar de db.t3.medium
- Menos overhead de CloudWatch (logs integrados)

---

## 🔄 Plan de Migración

### Fase 1: Preparación (Pre-migración)

#### 1.1 Revisar Recursos Existentes

- [ ] Documentar configuración actual (ASG, Launch Templates, AMIs)
- [ ] Identificar variables de entorno y configuraciones
- [ ] Verificar que RDS, S3, SQS estén funcionando correctamente
- [ ] Revisar logs y métricas actuales para establecer baseline

#### 1.2 Preparar Imagen Docker

- [ ] Verificar que el Dockerfile esté actualizado
- [ ] Construir imagen localmente y probar
- [ ] Verificar que todas las dependencias estén incluidas
- [ ] Probar que la aplicación funciona en contenedor

#### 1.3 Crear ECR Repository

- [ ] Crear repositorio en Amazon ECR
- [ ] Configurar políticas de acceso
- [ ] Subir imagen de prueba

### Fase 2: Configuración de ECS (Migración)

#### 2.1 Crear ECS Cluster

- [ ] Crear cluster `anb-rising-stars-cluster` con Fargate
- [ ] Habilitar Container Insights (opcional)

#### 2.2 Crear Task Definitions

- [ ] Crear Task Definition para API (`anb-api-task`)
  - [ ] Configurar CPU/memoria (0.5 vCPU, 1 GB)
  - [ ] Configurar variables de entorno
  - [ ] Configurar logging a CloudWatch
  - [ ] Configurar IAM roles (Task Role y Execution Role)
- [ ] Crear Task Definition para Workers (`anb-worker-task`)
  - [ ] Configurar CPU/memoria (1 vCPU, 2 GB)
  - [ ] Configurar command override para worker
  - [ ] Configurar variables de entorno
  - [ ] Configurar logging a CloudWatch
  - [ ] Configurar IAM roles

#### 2.3 Configurar Load Balancer

- [ ] Reutilizar ALB existente o crear uno nuevo
- [ ] Crear Target Group para ECS (tipo IP addresses)
- [ ] Configurar health checks
- [ ] Configurar listener rules

#### 2.4 Desplegar Servicios ECS

- [ ] Crear ECS Service para API
  - [ ] Configurar número de tareas (mínimo 2)
  - [ ] Configurar subnets (privadas, múltiples AZs)
  - [ ] Configurar security groups
  - [ ] Conectar a Target Group
  - [ ] Configurar auto-scaling (opcional)
- [ ] Crear ECS Service para Workers
  - [ ] Configurar número de tareas (mínimo 1)
  - [ ] Configurar subnets (privadas, múltiples AZs)
  - [ ] Configurar security groups
  - [ ] Configurar auto-scaling basado en SQS (opcional)

### Fase 3: Verificación (Post-migración)

#### 3.1 Verificar Despliegue

- [ ] Verificar que las tareas ECS estén en estado RUNNING
- [ ] Verificar que los health checks estén healthy
- [ ] Verificar logs en CloudWatch
- [ ] Probar endpoints de la API

#### 3.2 Probar Funcionalidades

- [ ] Autenticación (login/signup)
- [ ] Subida de videos
- [ ] Procesamiento asíncrono (SQS → Worker → S3)
- [ ] Consulta de videos
- [ ] Votación

#### 3.3 Verificar Escalado

- [ ] Probar escalado de API (generar carga)
- [ ] Probar escalado de Workers (llenar cola SQS)
- [ ] Verificar que el escalado funcione correctamente

### Fase 4: Optimización (Opcional)

#### 4.1 Ajustar Recursos

- [ ] Ajustar CPU/memoria de Task Definitions si es necesario
- [ ] Ajustar políticas de auto-scaling
- [ ] Configurar alarms en CloudWatch

#### 4.2 Optimizar Costos

- [ ] Revisar uso de recursos
- [ ] Ajustar capacidades mínimas/máximas
- [ ] Configurar alarmas de presupuesto

### Fase 5: Limpieza (Opcional)

#### 5.1 Desmantelar Infraestructura IaaS

**⚠️ IMPORTANTE**: Solo después de verificar que PaaS funciona correctamente

- [ ] Detener Auto Scaling Groups (IaaS)
- [ ] Terminar instancias EC2 (IaaS)
- [ ] Eliminar Launch Templates (IaaS)
- [ ] Eliminar AMIs (IaaS) - **CUIDADO**: Asegúrate de tener backups
- [ ] Actualizar documentación

---

## 🔧 Cambios Técnicos Requeridos

### Código de la Aplicación

**✅ No se requieren cambios en el código** - La aplicación ya está containerizada y lista para ECS.

### Configuración

#### Variables de Entorno

Las mismas variables de entorno funcionan, pero ahora se configuran en:
- **IaaS**: Archivo `.env` en instancias EC2
- **PaaS**: Task Definition de ECS (Environment variables o Secrets Manager)

#### IAM Roles

- **IaaS**: IAM Role asociado a instancias EC2
- **PaaS**: 
  - **Task Role**: Permisos para que las tareas accedan a SQS, S3, RDS
  - **Task Execution Role**: Permisos para que ECS descargue imágenes de ECR y escriba logs

#### Security Groups

- **IaaS**: Security groups para instancias EC2
- **PaaS**: Security groups para tareas ECS (misma lógica, pero aplicado a tareas)

### Logging

- **IaaS**: Logs en instancias EC2 o CloudWatch Agent
- **PaaS**: CloudWatch Logs automático (configurado en Task Definition)

---

## ⚠️ Consideraciones Importantes

### Compatibilidad

- ✅ **RDS, S3, SQS**: No requieren cambios (mismos servicios)
- ✅ **ALB**: Puede reutilizarse o crearse uno nuevo
- ✅ **VPC/Subnets**: Pueden reutilizarse
- ✅ **Security Groups**: Pueden reutilizarse o crearse nuevos

### Downtime

- **Estrategia recomendada**: Desplegar PaaS en paralelo, verificar, luego desmantelar IaaS
- **Downtime mínimo**: Solo durante el cambio de DNS del ALB (si se crea uno nuevo)

### Rollback

Si algo sale mal:
1. Mantener IaaS activo hasta verificar PaaS
2. Si PaaS falla, simplemente no desmantelar IaaS
3. Corregir problemas en PaaS y reintentar

---

## 📋 Checklist de Migración

### Pre-migración
- [ ] Documentar configuración actual
- [ ] Preparar imagen Docker
- [ ] Crear ECR repository
- [ ] Verificar que RDS, S3, SQS funcionan

### Migración
- [ ] Crear ECS Cluster
- [ ] Crear Task Definitions (API y Workers)
- [ ] Configurar ALB y Target Group
- [ ] Desplegar ECS Services
- [ ] Configurar auto-scaling

### Post-migración
- [ ] Verificar que tareas estén RUNNING
- [ ] Probar funcionalidades completas
- [ ] Verificar escalado
- [ ] Revisar logs y métricas

### Limpieza (Opcional)
- [ ] Desmantelar IaaS (solo después de verificar PaaS)
- [ ] Actualizar documentación

---

## 🔗 Referencias

- [Guía de Despliegue PaaS](AWS_PAAS_DEPLOYMENT_GUIDE.md)
- [Arquitectura PaaS](ARQUITECTURA_PAAS.md)
- [Documentación AWS ECS](https://docs.aws.amazon.com/ecs/)
- [Guía de Migración a ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/migration.html)

