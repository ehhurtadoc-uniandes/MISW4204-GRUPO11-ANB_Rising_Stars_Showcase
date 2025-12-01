# Task Definitions para ECS

Este directorio contiene las definiciones de tareas (Task Definitions) para desplegar la aplicación en Amazon ECS.

## Archivos

- **`anb-api-task.json`**: Task Definition para la capa web (API FastAPI)
- **`anb-worker-task.json`**: Task Definition para la capa de workers (procesamiento de videos)

## Uso

### Opción 1: Usar desde AWS Console

1. Copia el contenido del archivo JSON
2. Ve a **ECS Dashboard** → **Task definitions** → **Create new task definition**
3. Selecciona **Create new task definition with JSON**
4. Pega el contenido del archivo JSON
5. **IMPORTANTE**: Reemplaza los siguientes valores:
   - `ACCOUNT_ID`: Tu Account ID de AWS
   - `RDS_ENDPOINT`: Endpoint de tu instancia RDS
   - `PASSWORD`: Contraseña de RDS
   - `GENERAR_SECRET_KEY_AQUI`: Genera una secret key con `openssl rand -hex 32`
   - `anb-rising-stars-videos-east1`: Nombre de tu bucket S3
   - `LabRole`: Nombre de tu IAM role (puede ser diferente en cuentas de estudiante)

6. Click **Create**

### Opción 2: Usar desde AWS CLI

```bash
# Registrar Task Definition para API
aws ecs register-task-definition \
  --cli-input-json file://anb-api-task.json

# Registrar Task Definition para Workers
aws ecs register-task-definition \
  --cli-input-json file://anb-worker-task.json
```

**Nota**: Asegúrate de reemplazar los valores antes de ejecutar el comando.

## Configuración de Variables de Entorno

Las Task Definitions incluyen variables de entorno necesarias. Si prefieres usar **AWS Secrets Manager** o **Parameter Store** para credenciales sensibles, puedes:

1. Crear secrets en Secrets Manager
2. Reemplazar las variables de entorno por referencias a secrets en la Task Definition:

```json
"secrets": [
  {
    "name": "POSTGRES_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:anb-app-secrets-XXXXX:password::"
  }
]
```

## Personalización

### Recursos (CPU/Memoria)

Puedes ajustar los recursos según tus necesidades:

- **API**: Actualmente 0.5 vCPU, 1 GB RAM
- **Workers**: Actualmente 1 vCPU, 2 GB RAM

Para cambiar, modifica los campos `cpu` y `memory` en el JSON.

### Health Checks

La Task Definition de API incluye un health check. Asegúrate de que tu aplicación responda en `/health`.

Para workers, no se requiere health check ya que son procesos de larga duración.

## Troubleshooting

### Error: "Task role cannot be assumed"

- Verifica que el IAM role (`LabRole` o el que uses) existe
- Verifica que el role tiene el trust policy correcto para ECS

### Error: "Execution role cannot be assumed"

- Verifica que el execution role tiene permisos para:
  - ECR (descargar imágenes)
  - CloudWatch Logs (escribir logs)

### Error: "Cannot pull image"

- Verifica que la imagen existe en ECR
- Verifica que el execution role tiene permisos para ECR
- Verifica que las subnets tienen acceso a internet (NAT Gateway)

