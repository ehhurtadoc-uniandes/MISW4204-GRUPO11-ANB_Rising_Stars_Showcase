# Fix: S3 404 Error al Descargar Videos

## Problema
El worker recibe mensajes de SQS correctamente, pero falla al descargar videos de S3 con error 404.

**Error en logs:**
```
ERROR: Error downloading from S3: 404 - Not Found
S3 path: s3://anb-rising-stars-videos-east1/uploads/51a6a2c4-3ec9-4e9e-b530-460635240a26.mp4
Bucket: anb-rising-starts-videos-east1
Key: s3://anb-rising-stars-videos-east1/uploads/51a6a2c4-3ec9-4e9e-b530-460635240a26.mp4
```

## Causas Posibles

### 1. Bucket No Existe
El bucket `anb-rising-starts-videos-east1` o `anb-rising-stars-videos-east1` no existe.

**Solución:**
```bash
# Verificar qué buckets existen
aws s3 ls | grep anb

# Si no existe, crearlo
aws s3 mb s3://anb-rising-starts-videos-east1 --region us-east-1
```

### 2. Video No Fue Subido Correctamente
El video no se subió a S3 cuando se hizo el upload desde el backend.

**Verificar:**
```bash
# Listar videos en el bucket
aws s3 ls s3://anb-rising-starts-videos-east1/uploads/

# Si está vacío, el problema es en el upload del backend
```

### 3. Inconsistencia en Nombre del Bucket
El backend está guardando con un nombre de bucket y el worker está buscando con otro.

**Verificar configuración:**
```bash
# En el backend
cat /opt/anb-backend/.env | grep S3_BUCKET_NAME

# En el worker
cat /opt/anb-worker/.env | grep S3_BUCKET_NAME

# Deben ser EXACTAMENTE iguales
```

### 4. Key Incorrecta
El código estaba extrayendo mal la key del path S3 (ya corregido en el código).

## Solución Paso a Paso

### Paso 1: Verificar que el Bucket Existe

```bash
# Desde cualquier instancia EC2 con credenciales
aws s3 ls s3://anb-rising-starts-videos-east1/

# Si da error "NoSuchBucket", el bucket no existe
# Si lista archivos, el bucket existe
```

### Paso 2: Verificar Videos en el Bucket

```bash
# Listar videos subidos
aws s3 ls s3://anb-rising-starts-videos-east1/uploads/ --recursive

# Si está vacío, el problema es que el backend no está subiendo videos
```

### Paso 3: Verificar Configuración del Backend

El backend debe tener:
1. S3_BUCKET_NAME configurado correctamente
2. Credenciales AWS válidas
3. Permisos para escribir en S3

```bash
# En la instancia del backend
cat /opt/anb-backend/.env | grep -E "S3_BUCKET_NAME|AWS_ACCESS_KEY_ID|STORAGE_TYPE"

# Debe mostrar:
# STORAGE_TYPE=cloud
# S3_BUCKET_NAME=anb-rising-starts-videos-east1
# AWS_ACCESS_KEY_ID=...
```

### Paso 4: Probar Upload Manual

```bash
# Desde el backend, probar subir un archivo de prueba
echo "test" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://anb-rising-starts-videos-east1/uploads/test.txt

# Si funciona, el backend tiene acceso
# Si falla, verificar credenciales y permisos
```

### Paso 5: Verificar que el Video se Subió

Cuando subes un video desde el frontend:

1. Revisa los logs del backend:
   ```bash
   docker logs anb-api | grep -i "s3\|upload"
   ```

2. Deberías ver:
   ```
   INFO: Video uploaded to S3: s3://anb-rising-starts-videos-east1/uploads/...
   ```

3. Verifica en S3:
   ```bash
   aws s3 ls s3://anb-rising-starts-videos-east1/uploads/ | grep <video_id>
   ```

## Verificación Rápida

### Checklist

- [ ] Bucket existe: `aws s3 ls s3://anb-rising-starts-videos-east1/`
- [ ] Backend tiene S3_BUCKET_NAME configurado
- [ ] Backend tiene credenciales AWS válidas
- [ ] Backend puede escribir en S3 (probar upload manual)
- [ ] Worker tiene el mismo S3_BUCKET_NAME que el backend
- [ ] Worker tiene credenciales AWS válidas
- [ ] Worker puede leer de S3 (probar download manual)
- [ ] El video existe en S3 después del upload

### Comandos de Diagnóstico

```bash
# 1. Verificar bucket
aws s3 ls s3://anb-rising-starts-videos-east1/

# 2. Listar videos subidos
aws s3 ls s3://anb-rising-starts-videos-east1/uploads/ --recursive

# 3. Verificar configuración backend
ssh backend-instance
cat /opt/anb-backend/.env | grep S3

# 4. Verificar configuración worker
ssh worker-instance
cat /opt/anb-worker/.env | grep S3

# 5. Probar acceso desde backend
aws s3 cp /tmp/test.txt s3://anb-rising-starts-videos-east1/uploads/test.txt

# 6. Probar acceso desde worker
aws s3 cp s3://anb-rising-starts-videos-east1/uploads/test.txt /tmp/test-download.txt
```

## Solución Más Común

**99% de los casos**: El bucket no existe o el video no se subió correctamente.

**Solución**:
1. Crear el bucket si no existe
2. Verificar que el backend está subiendo videos (revisar logs)
3. Verificar que el video existe en S3 antes de que el worker intente procesarlo

