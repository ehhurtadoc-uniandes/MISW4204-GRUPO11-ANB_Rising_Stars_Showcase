# Verificación del Flujo de Procesamiento de Videos

## Checklist de Verificación

### ✅ 1. Worker está funcionando
```bash
# En la instancia EC2 del worker
systemctl status anb-worker-sqs
docker ps | grep anb-worker-sqs
docker logs -f anb-worker-sqs
```

**Deberías ver:**
- Servicio activo y corriendo
- Contenedor Docker funcionando
- Logs sin errores de credenciales
- Mensaje: "Starting SQS worker..."
- Mensaje: "SQS Queue URL: https://sqs.us-east-1.amazonaws.com/..."

### ✅ 2. Backend puede enviar mensajes a SQS

**Verificar que el backend tenga:**
1. SQS_QUEUE_URL configurado en `.env`
2. Credenciales AWS configuradas (si no usa IAM Role)

```bash
# En la instancia EC2 del backend
cat /opt/anb-backend/.env | grep SQS
cat /opt/anb-backend/.env | grep AWS_ACCESS_KEY_ID
```

**Si las credenciales están comentadas y no tienes IAM Role:**
- Descomenta las credenciales en `backend-user-data.sh` o actualiza el `.env` manualmente
- Reinicia el backend: `sudo systemctl restart anb-api`

### ✅ 3. SQS Queue existe y está accesible

```bash
# Verificar que la cola existe (desde cualquier instancia con credenciales)
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/906569879596/anb-video-processing-queue \
  --attribute-names All
```

### ✅ 4. Prueba End-to-End

1. **Sube un video desde el frontend/API:**
   ```bash
   curl -X POST "http://TU_ALB_DNS/api/videos/upload" \
     -H "Authorization: Bearer TU_TOKEN" \
     -F "title=Test Video" \
     -F "video_file=@test_video.mp4"
   ```

2. **Verifica que el mensaje llegó a SQS:**
   ```bash
   # En el worker, deberías ver en los logs:
   docker logs -f anb-worker-sqs
   # Busca: "Received 1 message(s) from SQS"
   ```

3. **Verifica que el video se está procesando:**
   ```bash
   # En los logs del worker:
   # Deberías ver: "Processing video <video_id>"
   # Luego: "Video <video_id> processed successfully"
   ```

4. **Verifica el estado en la base de datos:**
   ```sql
   SELECT id, title, status, processed_path FROM videos ORDER BY created_at DESC LIMIT 5;
   ```

## Problemas Comunes y Soluciones

### ❌ Error: "SQS queue URL not configured"
**Solución:** Verifica que `SQS_QUEUE_URL` esté en el `.env` del backend y worker.

### ❌ Error: "Unable to locate credentials" o "InvalidClientTokenId"
**Solución:** 
- Verifica credenciales en `.env`
- Usa `update-worker-credentials.sh` para actualizar
- Reinicia el contenedor/servicio

### ❌ Error: "SignatureDoesNotMatch"
**Solución:**
- Usa `verify-credentials.sh` para diagnosticar
- Usa `update-worker-credentials.sh` para corregir formato

### ❌ El video se sube pero no se procesa
**Verifica:**
1. El worker está corriendo: `docker ps | grep anb-worker-sqs`
2. El worker puede recibir mensajes: revisa logs del worker
3. El backend puede enviar mensajes: revisa logs del backend
4. La cola SQS tiene mensajes: `aws sqs get-queue-attributes --queue-url ...`

### ❌ El video se procesa pero falla
**Verifica:**
1. El worker tiene acceso a S3 (para descargar el video original)
2. El worker tiene espacio en disco: `df -h`
3. El worker tiene las dependencias instaladas (moviepy, PIL, etc.)
4. Revisa los logs completos del worker para ver el error específico

## Comandos Útiles

### Ver mensajes en la cola SQS
```bash
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/906569879596/anb-video-processing-queue \
  --max-number-of-messages 10
```

### Ver métricas de la cola
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/906569879596/anb-video-processing-queue \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

### Reiniciar servicios
```bash
# Worker
sudo systemctl restart anb-worker-sqs
# O directamente:
sudo docker restart anb-worker-sqs

# Backend
sudo systemctl restart anb-api
```

### Ver logs en tiempo real
```bash
# Worker
docker logs -f anb-worker-sqs

# Backend
docker logs -f anb-api
# O
journalctl -u anb-api -f
```

