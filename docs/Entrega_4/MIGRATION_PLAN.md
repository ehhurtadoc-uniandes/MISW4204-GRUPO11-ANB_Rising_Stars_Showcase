# Plan de Migración - Entrega 4: Escalabilidad y Alta Disponibilidad

## Objetivos

1. **Migrar de Celery/Redis a Amazon SQS** (20%)
2. **Implementar Auto Scaling para Workers** (20%)
3. **Configurar Alta Disponibilidad en múltiples AZs** (20%)
4. **Mantener todos los requerimientos funcionales** (10%)

## Especificaciones de Hardware

- **EC2 Instances**: 2 vCPU, 2 GiB RAM, 30 GiB almacenamiento
- **RDS**: Base de datos relacional (ya configurado)
- **S3**: Almacenamiento de videos (ya configurado)
- **CloudWatch**: Monitoreo (a configurar)
- **Auto Scaling**: Para capa web (ya configurado) y workers (a implementar)
- **Load Balancer**: ALB (ya configurado)

## Fase 1: Migración a Amazon SQS

### Cambios en el Código

#### 1.1 Backend (API)
- **Archivo**: `app/api/videos.py`
  - Reemplazar `celery_app.send_task()` con `boto3.client('sqs').send_message()`
  - Enviar mensaje JSON con `video_id` y `video_path` a la cola SQS

#### 1.2 Worker
- **Nuevo archivo**: `app/workers/sqs_worker.py`
  - Consumir mensajes de SQS usando `boto3.client('sqs')`
  - Procesar mensajes con la lógica existente de `process_video_task`
  - Eliminar mensaje de SQS después de procesar exitosamente
  - Implementar manejo de errores y reintentos

#### 1.3 Configuración
- **Archivo**: `app/core/config.py`
  - Agregar configuración para SQS:
    - `sqs_queue_url`
    - `sqs_region`
    - `sqs_visibility_timeout`
    - `sqs_max_receive_count`

### Estructura del Mensaje SQS

```json
{
  "video_id": "uuid-string",
  "video_path": "s3://bucket/path/to/video.mp4",
  "task_id": "uuid-string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Fase 2: Auto Scaling para Workers

### 2.1 Crear Launch Template para Workers

- **AMI**: Basada en la AMI del worker actual
- **Instance Type**: `t3.small` o `t3.medium` (2 vCPU, 2-4 GiB RAM)
- **Storage**: 30 GiB gp3
- **User Data**: Script para iniciar worker SQS
- **Security Group**: `anb-worker-sg`
- **IAM Role**: Permisos para SQS y S3

### 2.2 Crear Auto Scaling Group

- **Name**: `anb-worker-asg`
- **Launch Template**: Worker launch template
- **VPC**: `anb-vpc`
- **Subnets**: Múltiples subnets privadas en diferentes AZs
- **Desired Capacity**: 1
- **Min Capacity**: 1
- **Max Capacity**: 3
- **Health Check**: EC2 (o personalizado basado en CloudWatch)

### 2.3 Políticas de Escalamiento

#### Escalamiento Basado en SQS Queue Depth

**Target Tracking Policy**:
- **Métrica**: `ApproximateNumberOfMessagesVisible` en la cola SQS
- **Target Value**: 10 mensajes por worker
- **Escalamiento**: Agregar worker cuando hay > 10 mensajes por worker
- **Desescalamiento**: Remover worker cuando hay < 5 mensajes por worker

**CloudWatch Alarm**:
- **Alarm Name**: `anb-worker-scale-up`
- **Métrica**: `ApproximateNumberOfMessagesVisible`
- **Condición**: `> 20` mensajes
- **Acción**: Agregar 1 worker

- **Alarm Name**: `anb-worker-scale-down`
- **Métrica**: `ApproximateNumberOfMessagesVisible`
- **Condición**: `< 5` mensajes
- **Acción**: Remover 1 worker

### 2.4 CloudWatch Métricas

- **Queue Depth**: Número de mensajes en cola
- **Worker Count**: Número de instancias activas
- **Processing Time**: Tiempo promedio de procesamiento
- **Error Rate**: Tasa de errores en procesamiento

## Fase 3: Alta Disponibilidad

### 3.1 Backend (Ya Implementado - Verificar)

- **Auto Scaling Group**: Debe estar en múltiples AZs
- **Load Balancer**: ALB con health checks
- **Verificar**: Que las subnets estén en al menos 2 AZs diferentes

### 3.2 Workers (A Implementar)

- **Auto Scaling Group**: Desplegar en múltiples AZs
- **Subnets**: Seleccionar subnets privadas en diferentes AZs
- **Health Checks**: Configurar health checks para workers

### 3.3 RDS (Ya Configurado)

- **Multi-AZ**: Ya configurado en Entrega 3

### 3.4 SQS

- **Queue**: SQS Standard Queue (alta disponibilidad por defecto)
- **Dead Letter Queue**: Configurar DLQ para mensajes fallidos

## Fase 4: Configuración de CloudWatch

### 4.1 Métricas Personalizadas

- **Worker Processing Time**: Tiempo de procesamiento por video
- **Worker Throughput**: Videos procesados por minuto
- **Queue Depth**: Mensajes pendientes en SQS
- **Error Rate**: Tasa de errores

### 4.2 Dashboards

- **Dashboard Principal**: Métricas de sistema completo
- **Dashboard Workers**: Métricas específicas de workers
- **Dashboard API**: Métricas de la API

### 4.3 Alarms

- **High Queue Depth**: Alerta cuando hay muchos mensajes pendientes
- **Worker Failure**: Alerta cuando un worker falla
- **API Errors**: Alerta cuando hay errores en la API

## Archivos a Modificar/Crear

### Modificar
1. `app/api/videos.py` - Cambiar de Celery a SQS
2. `app/core/config.py` - Agregar configuración SQS
3. `app/workers/video_processor.py` - Adaptar para SQS (o crear nuevo)
4. `requirements.txt` - Agregar `boto3` (ya debería estar)

### Crear
1. `app/workers/sqs_worker.py` - Worker que consume de SQS
2. `scripts/aws/worker-sqs-user-data.sh` - User data script para workers
3. `docs/Entrega_4/AWS_DEPLOYMENT_GUIDE.md` - Documentación actualizada
4. `docs/Entrega_4/SQS_MIGRATION.md` - Guía de migración detallada

## Orden de Implementación

1. ✅ Crear cola SQS en AWS
2. ✅ Modificar backend para enviar a SQS
3. ✅ Crear worker SQS
4. ✅ Probar localmente
5. ✅ Crear Launch Template para workers
6. ✅ Crear Auto Scaling Group para workers
7. ✅ Configurar CloudWatch alarms y métricas
8. ✅ Verificar alta disponibilidad
9. ✅ Documentar cambios
10. ✅ Pruebas de carga

## Notas Importantes

- **Backward Compatibility**: Mantener código de Celery comentado durante transición
- **Testing**: Probar exhaustivamente antes de desplegar
- **Rollback Plan**: Tener plan para volver a Celery si es necesario
- **Monitoring**: Configurar alertas antes de desplegar
- **Costs**: SQS tiene costos por mensaje, considerar en presupuesto

