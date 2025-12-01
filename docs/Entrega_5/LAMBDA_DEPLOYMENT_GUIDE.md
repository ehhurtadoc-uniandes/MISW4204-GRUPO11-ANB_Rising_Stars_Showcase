# Guía de Despliegue con AWS Lambda - Entrega 5

## 📋 Resumen

Esta guía detallada explica cómo desplegar la capa web (API FastAPI) en **AWS Lambda** usando **API Gateway**, cumpliendo con la Actividad 1 de la Entrega 5.

## 🎯 Ventajas de Lambda

- ✅ **Serverless puro**: Sin gestión de servidores
- ✅ **Escalado automático**: Escala de 0 a miles de requests
- ✅ **Pago por uso**: Solo pagas por invocaciones
- ✅ **Alta disponibilidad**: Distribuido automáticamente en múltiples AZs
- ✅ **Sin mantenimiento**: AWS gestiona todo

## ⚠️ Limitaciones

- ⚠️ **Timeout máximo**: 15 minutos
- ⚠️ **Memoria máxima**: 10 GB
- ⚠️ **Tamaño del deployment package**: 50 MB (250 MB descomprimido)
- ⚠️ **Cuentas de estudiante**: Máximo 10 instancias concurrentes

## 🔧 Preparación del Código

### Paso 1: Instalar Mangum

Mangum es un adaptador ASGI para Lambda que permite ejecutar FastAPI en Lambda.

```bash
# Agregar a requirements.txt
echo "mangum>=0.17.0" >> requirements.txt
```

### Paso 2: Crear Lambda Handler

Crea `lambda_handler.py` en la raíz del proyecto:

```python
"""
Lambda handler para FastAPI
"""
from mangum import Mangum
from app.main import app

# Crear handler Lambda
# lifespan="off" porque Lambda no soporta lifespan events
handler = Mangum(app, lifespan="off")
```

### Paso 3: Ajustar Configuración para Lambda

En `app/core/config.py`, asegúrate de que las variables de entorno se carguen correctamente:

```python
# Ya está configurado con pydantic-settings
# No requiere cambios adicionales
```

### Paso 4: Crear Deployment Package

#### Opción A: ZIP File (Recomendado para empezar)

```bash
# Crear directorio temporal
mkdir -p lambda-package
cd lambda-package

# Instalar dependencias
pip install -r ../requirements.txt -t .

# Copiar código de la aplicación
cp -r ../app .
cp ../lambda_handler.py .

# Crear ZIP
zip -r ../lambda-deployment.zip .
cd ..
```

**Verificar tamaño**:
```bash
du -sh lambda-deployment.zip
# Si es > 50 MB, considera usar Lambda Layers o ECR
```

#### Opción B: Lambda Container Image (Para paquetes grandes)

Si tu deployment package es muy grande (>50 MB), usa contenedores:

1. **Crear Dockerfile para Lambda**:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Copiar código
COPY app ${LAMBDA_TASK_ROOT}/app
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Instalar dependencias
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Configurar handler
CMD [ "lambda_handler.handler" ]
```

2. **Construir y subir a ECR**:

```bash
# Autenticar con ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Construir imagen
docker build -t anb-lambda:latest .

# Tag para ECR
docker tag anb-lambda:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-lambda:latest

# Push
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-lambda:latest
```

## 🚀 Despliegue en AWS

### Paso 1: Crear Función Lambda

#### 1.1 Crear Función desde ZIP

1. **Lambda Dashboard** → **Functions** → **Create function**
2. Configuración:
   - **Function name**: `anb-api-lambda`
   - **Runtime**: Python 3.12 (o **Container image** si usas ECR)
   - **Architecture**: x86_64
   - **Execution role**: 
     - Si tienes `LabRole`: Seleccionarlo
     - Si no: **Create a new role with basic Lambda permissions** (luego agregar permisos)
3. Click **Create function**

#### 1.2 Subir Código

**Si usas ZIP**:
1. **Code** → **Upload from** → **.zip file**
2. Sube `lambda-deployment.zip`
3. **Handler**: `lambda_handler.handler`

**Si usas Container Image**:
1. **Code** → **Container image** → **Browse images**
2. Selecciona la imagen de ECR: `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/anb-lambda:latest`
3. Click **Save**

#### 1.3 Configurar Variables de Entorno

**Configuration** → **Environment variables** → **Edit**:

```
DATABASE_URL=postgresql://anb_admin:PASSWORD@RDS_ENDPOINT:5432/anb_db
POSTGRES_HOST=RDS_ENDPOINT
POSTGRES_PORT=5432
POSTGRES_USER=anb_admin
POSTGRES_PASSWORD=PASSWORD
POSTGRES_DB=anb_db
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/anb-video-processing-queue
SQS_REGION=us-east-1
SECRET_KEY=GENERAR_SECRET_KEY_AQUI
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-stars-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/
ENVIRONMENT=production
DEBUG=False
```

#### 1.4 Configurar Timeout y Memoria

**Configuration** → **General configuration** → **Edit**:

- **Timeout**: 30 segundos (máximo 15 minutos)
- **Memory**: 512 MB (ajustar según necesidad, mínimo 128 MB)
- **Ephemeral storage**: 512 MB (mínimo, aumentar si procesas archivos grandes)

### Paso 2: Configurar IAM Role

El role de ejecución necesita permisos para:
- RDS (conectar a la base de datos)
- S3 (subir/descargar videos)
- SQS (enviar mensajes)
- CloudWatch Logs (escribir logs)

**Si usas LabRole**, verifica que tenga estos permisos. Si no, agrega una policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": "arn:aws:rds-db:us-east-1:ACCOUNT_ID:dbuser:DB_INSTANCE_ID/anb_admin"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::anb-rising-stars-videos-east1/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:anb-video-processing-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### Paso 3: Crear API Gateway

#### 3.1 Crear REST API

1. **API Gateway Dashboard** → **APIs** → **Create API**
2. Seleccionar **REST API** → **Build**
3. Configuración:
   - **Protocol**: REST
   - **Create new API**: New API
   - **API name**: `anb-api-gateway`
   - **Endpoint Type**: Regional (o Edge si necesitas distribución global)
4. Click **Create API**

#### 3.2 Crear Resource y Method

1. **Actions** → **Create Resource**
   - **Resource Name**: `{proxy+}`
   - **Resource Path**: `{proxy+}`
   - **Enable API Gateway CORS**: Sí (si necesitas CORS)
2. Click **Create Resource**

3. Con `{proxy+}` seleccionado, **Actions** → **Create Method** → **ANY**
   - **Integration type**: Lambda Function
   - **Lambda Function**: `anb-api-lambda`
   - **Use Lambda Proxy integration**: ✅ Sí (importante para FastAPI)
4. Click **Save** → **OK** (permiso para invocar Lambda)

#### 3.3 Configurar CORS (Opcional)

Si tu frontend necesita CORS:

1. Seleccionar `{proxy+}` → **Actions** → **Enable CORS**
2. Configurar:
   - **Access-Control-Allow-Origin**: `*` (o tu dominio)
   - **Access-Control-Allow-Headers**: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
   - **Access-Control-Allow-Methods**: `GET,POST,PUT,DELETE,OPTIONS`
3. Click **Enable CORS and replace existing CORS headers**

#### 3.4 Desplegar API

1. **Actions** → **Deploy API**
2. Configuración:
   - **Deployment stage**: `prod` (o crear uno nuevo)
   - **Stage name**: `prod`
   - **Stage description**: Production stage
3. Click **Deploy**

**Anota la Invoke URL**: `https://abc123.execute-api.us-east-1.amazonaws.com/prod`

### Paso 4: Probar la API

```bash
# Health check
curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/health

# Documentación
curl https://abc123.execute-api.us-east-1.amazonaws.com/prod/docs

# Login
curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/prod/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@example.com","password":"password"}'
```

## 🔍 Troubleshooting

### Error: "Unable to import module 'lambda_handler'"

- **Causa**: El handler no está en la raíz del ZIP o el nombre es incorrecto
- **Solución**: Verifica que `lambda_handler.py` esté en la raíz del ZIP y el handler sea `lambda_handler.handler`

### Error: "ModuleNotFoundError: No module named 'mangum'"

- **Causa**: Mangum no está en el deployment package
- **Solución**: Asegúrate de instalar dependencias con `pip install -r requirements.txt -t .`

### Error: "Task timed out after 30.00 seconds"

- **Causa**: La función Lambda excedió el timeout
- **Solución**: Aumenta el timeout en **Configuration** → **General configuration** (máximo 15 minutos)

### Error: "Unable to connect to RDS"

- **Causa**: Security Group de RDS no permite tráfico desde Lambda
- **Solución**: 
  1. Lambda ejecuta en VPC si necesitas conectarte a RDS privado
  2. Configura VPC en Lambda: **Configuration** → **VPC** → Agregar subnets y security group
  3. Asegúrate de que el Security Group de RDS permita tráfico desde el Security Group de Lambda

### Error: "CORS header 'Access-Control-Allow-Origin' missing"

- **Causa**: CORS no está configurado en API Gateway
- **Solución**: Habilita CORS en el resource `{proxy+}` (ver Paso 3.3)

## 📊 Monitoreo

### CloudWatch Logs

Los logs de Lambda están en:
- **CloudWatch** → **Log groups** → `/aws/lambda/anb-api-lambda`

### Métricas

- **Invocations**: Número de invocaciones
- **Duration**: Tiempo de ejecución
- **Errors**: Errores
- **Throttles**: Throttling (si excedes límites)

### Configurar Alarms

1. **CloudWatch** → **Alarms** → **Create alarm**
2. Seleccionar métrica: `Errors` o `Duration`
3. Configurar threshold
4. Configurar SNS topic para notificaciones

## 💰 Costos Estimados

- **Primeros 1M requests/mes**: Gratis
- **Requests adicionales**: $0.20 por 1M requests
- **Compute time**: $0.0000166667 por GB-segundo
- **Ejemplo**: 1M requests, 512 MB, 1 segundo promedio = ~$8.50/mes

## 🔗 Referencias

- [Mangum Documentation](https://mangum.io/)
- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [API Gateway + Lambda](https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started-with-lambda.html)

