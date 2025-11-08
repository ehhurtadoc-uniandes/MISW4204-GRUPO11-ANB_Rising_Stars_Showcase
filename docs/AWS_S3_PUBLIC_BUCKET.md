# Configuración S3: Bucket Público vs Privado

## Resumen Rápido

### Opción 1: Bucket Público para Lectura (Simple) ✅

**Ventajas**:
- ✅ No necesitas credenciales para que los usuarios vean videos
- ✅ URLs directas a los videos (sin URLs presignadas)
- ✅ Más simple de configurar

**Desventajas**:
- ❌ Aún necesitas credenciales para subir videos (PUT/POST)
- ❌ Los videos son accesibles públicamente (cualquiera con la URL puede verlos)
- ⚠️ Menos seguro (aunque solo lectura)

**Configuración**:
1. Crear bucket
2. Desbloquear acceso público
3. Agregar bucket policy para lectura pública
4. Configurar credenciales solo para escritura

### Opción 2: Bucket Privado (Recomendado) 🔒

**Ventajas**:
- ✅ Más seguro (acceso controlado)
- ✅ URLs presignadas con expiración
- ✅ Control total sobre quién puede acceder

**Desventajas**:
- ❌ Necesitas credenciales para todo (lectura y escritura)
- ❌ Más complejo de configurar

**Configuración**:
1. Crear bucket
2. Mantener bloqueado el acceso público
3. Configurar credenciales para lectura y escritura
4. Usar URLs presignadas en el código

---

## Configuración Detallada: Bucket Público

### Paso 1: Crear Bucket

1. **S3 Dashboard** → **Create bucket**
2. **Bucket name**: `anb-rising-stars-videos-us-east-1`
3. **Block Public Access**: Desmarcar (aparecerá advertencia)
4. Marcar **I acknowledge...**
5. Click **Create bucket**

### Paso 2: Configurar Bucket Policy

1. **Bucket** → **Permissions** → **Bucket policy** → **Edit**
2. Agregar esta política:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadProcessedVideos",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::anb-rising-stars-videos-us-east-1/processed_videos/*"
        }
    ]
}
```

**Nota**: Si quieres hacer TODOS los objetos públicos (no recomendado):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::anb-rising-stars-videos-us-east-1/*"
        }
    ]
}
```

### Paso 3: Configurar Credenciales (Solo para Escritura)

Aún necesitas credenciales AWS para que tu aplicación pueda:
- Subir videos (PUT)
- Eliminar videos (DELETE)
- Listar objetos (LIST)

**Permisos mínimos necesarios**:
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
                "arn:aws:s3:::anb-rising-stars-videos-us-east-1/*",
                "arn:aws:s3:::anb-rising-stars-videos-us-east-1"
            ]
        }
    ]
}
```

**Nota**: No necesitas `s3:GetObject` porque el bucket es público.

### Paso 4: Actualizar Código (Opcional)

Si el bucket es público, puedes modificar `get_file_path` para devolver URLs directas en lugar de presignadas:

```python
def get_file_path(self, filename: str, directory: str) -> str:
    """Get S3 file URL"""
    if directory == 'processed_videos':
        # Si el bucket es público, devolver URL directa
        key = f"{self.processed_prefix}{filename}"
        return f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{key}"
    else:
        # Para uploads, usar URL presignada (privado)
        key = self._get_s3_key(filename, directory)
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=3600
        )
        return url
```

---

## Comparación de Opciones

| Aspecto | Bucket Público | Bucket Privado |
|---------|----------------|----------------|
| **Lectura de videos** | Pública (sin credenciales) | Requiere credenciales/URL presignada |
| **Escritura de videos** | Requiere credenciales | Requiere credenciales |
| **Seguridad** | Media (cualquiera con URL puede ver) | Alta (control total) |
| **Complejidad** | Baja | Media |
| **Costos** | Igual | Igual |
| **URLs** | Directas (`https://bucket.s3...`) | Presignadas (expiran) |

---

## Recomendación

**Para desarrollo/pruebas**: Bucket público es más simple y rápido.

**Para producción**: Considera bucket privado con URLs presignadas para mayor seguridad.

**Híbrido**: Puedes hacer solo `processed_videos/` público y mantener `uploads/` privado.

---

## Notas Importantes

1. **Aún necesitas credenciales**: Incluso con bucket público, necesitas credenciales para subir/eliminar videos.

2. **Seguridad**: Hacer el bucket público significa que cualquiera con la URL puede acceder al video. Si los videos son públicos por diseño (como en tu caso), esto está bien.

3. **CORS**: Si quieres acceder desde navegadores web, configura CORS en el bucket.

4. **Costos**: No hay diferencia de costos entre bucket público y privado.

5. **URLs directas**: Con bucket público, puedes usar URLs directas como:
   ```
   https://anb-rising-stars-videos-us-east-1.s3.us-east-1.amazonaws.com/processed_videos/video.mp4
   ```




