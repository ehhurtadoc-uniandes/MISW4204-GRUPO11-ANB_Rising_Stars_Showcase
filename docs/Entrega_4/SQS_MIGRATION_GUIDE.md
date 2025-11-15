# Guía de Migración: Celery/Redis a Amazon SQS

## Resumen

Esta guía describe cómo migrar el sistema de procesamiento de videos de Celery/Redis a Amazon SQS para cumplir con los requisitos de la Entrega 4.

## Cambios Principales

### Antes (Entrega 3)
- **Backend**: Envía tareas a Celery usando `celery_app.send_task()`
- **Worker**: Consume tareas de Redis usando Celery workers
- **Broker**: Redis en EC2
- **Escalabilidad**: Manual (escalar instancias EC2 manualmente)

### Después (Entrega 4)
- **Backend**: Envía mensajes a SQS usando `boto3.client('sqs')`
- **Worker**: Consume mensajes de SQS usando polling
- **Broker**: Amazon SQS (managed service)
- **Escalabilidad**: Automática con Auto Scaling Group basado en métricas de SQS

## Pasos de Migración

### 1. Crear Cola SQS en AWS

1. Ir a **SQS Dashboard** → **Create queue**
2. Configuración:
   - **Name**: `anb-video-processing-queue`
   - **Type**: Standard Queue (para alta disponibilidad)
   - **Visibility timeout**: 300 segundos (5 minutos)
   - **Message retention period**: 14 días
   - **Receive message wait time**: 20 segundos (long polling)
3. Click **Create queue**
4. **Anotar el Queue URL** (ej: `https://sqs.us-east-1.amazonaws.com/123456789/anb-video-processing-queue`)

### 2. Crear Dead Letter Queue (Opcional pero Recomendado)

1. Crear otra cola: `anb-video-processing-dlq`
2. Configurar la cola principal para enviar mensajes fallidos a DLQ:
   - **Redrive policy**: Habilitar
   - **Dead-letter queue**: Seleccionar `anb-video-processing-dlq`
   - **Maximum receives**: 3 (después de 3 intentos, va a DLQ)

### 3. Actualizar Configuración del Backend

Agregar variables de entorno en el archivo `.env` de las instancias EC2 del backend:

```env
# SQS Configuration (Entrega 4)
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/anb-video-processing-queue
SQS_REGION=us-east-1
SQS_VISIBILITY_TIMEOUT=300
SQS_MAX_RECEIVE_COUNT=3
SQS_WAIT_TIME_SECONDS=20
```

### 4. Actualizar Código del Backend

El código ya está actualizado en `app/api/videos.py`:
- Usa `get_sqs_service()` para enviar mensajes a SQS
- Mantiene fallback a Celery si SQS no está configurado (backward compatibility)

### 5. Crear Worker SQS

El nuevo worker está en `app/workers/sqs_worker.py`:
- Consume mensajes de SQS usando long polling
- Procesa videos con la misma lógica que el worker Celery
- Elimina mensajes de SQS después de procesar exitosamente

### 6. Desplegar Workers con Auto Scaling

Ver sección "Auto Scaling para Workers" en `AWS_DEPLOYMENT_GUIDE.md`.

## Estructura del Mensaje SQS

```json
{
  "video_id": "uuid-string",
  "video_path": "s3://bucket/path/to/video.mp4",
  "task_id": "uuid-string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Ventajas de SQS sobre Celery/Redis

1. **Managed Service**: No necesitas mantener Redis
2. **Alta Disponibilidad**: SQS está disponible en múltiples AZs automáticamente
3. **Auto Scaling**: Fácil integrar con Auto Scaling Groups basado en métricas de cola
4. **Dead Letter Queue**: Manejo automático de mensajes fallidos
5. **Monitoreo**: CloudWatch métricas integradas
6. **Costo**: Pay-per-use, más económico para cargas variables

## Backward Compatibility

El código mantiene compatibilidad con Celery:
- Si `SQS_QUEUE_URL` no está configurado, usa Celery como fallback
- Permite migración gradual sin downtime

## Pruebas

### Probar Backend

```bash
# Subir un video
curl -X POST http://ALB_DNS/api/videos/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "title=Test Video" \
  -F "video_file=@test.mp4"
```

Verificar que el mensaje se envía a SQS:
- Ir a SQS Dashboard → Ver mensajes en la cola

### Probar Worker

```bash
# Ejecutar worker manualmente
python -m app.workers.sqs_worker
```

Verificar que:
- El worker recibe mensajes de SQS
- Procesa los videos correctamente
- Elimina mensajes después de procesar

## Troubleshooting

### El backend no envía mensajes a SQS

1. Verificar que `SQS_QUEUE_URL` esté configurado
2. Verificar permisos IAM (el rol EC2 necesita `sqs:SendMessage`)
3. Verificar logs del backend: `docker logs anb-api`

### El worker no recibe mensajes

1. Verificar que `SQS_QUEUE_URL` esté configurado
2. Verificar permisos IAM (el rol EC2 necesita `sqs:ReceiveMessage`, `sqs:DeleteMessage`)
3. Verificar logs del worker: `docker logs anb-worker-sqs`
4. Verificar que haya mensajes en la cola SQS

### Mensajes se quedan en la cola

1. Verificar que el worker esté corriendo
2. Verificar que el worker tenga permisos para eliminar mensajes
3. Verificar logs del worker para errores

## Rollback Plan

Si necesitas volver a Celery:

1. Remover `SQS_QUEUE_URL` del `.env`
2. Asegurar que `CELERY_BROKER_URL` esté configurado
3. Reiniciar instancias del backend
4. El código automáticamente usará Celery como fallback

