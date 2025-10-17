# Documentación Entrega 1 - ANB Rising Stars Showcase

## Índice

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelo de Datos](#modelo-de-datos)
4. [API REST](#api-rest)
5. [Procesamiento Asíncrono](#procesamiento-asíncrono)
6. [Seguridad](#seguridad)
7. [Despliegue](#despliegue)
8. [Pruebas](#pruebas)
9. [Análisis de Calidad](#análisis-de-calidad)

## Introducción

La plataforma ANB Rising Stars Showcase es una aplicación web escalable desarrollada para gestionar el programa de identificación de talentos emergentes en baloncesto. Permite a jóvenes jugadores subir videos de sus habilidades para ser evaluados y votados por el público y jurado especializado.

### Objetivos

- Democratizar el acceso al proceso de selección de talentos
- Proporcionar una plataforma escalable para cientos de miles de usuarios
- Implementar procesamiento asíncrono de videos
- Garantizar alta disponibilidad y rendimiento

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   FastAPI API   │    │ Celery Workers  │
│  (Proxy Reverso)│◄──►│   (Backend)     │◄──►│ (Procesamiento) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   PostgreSQL    │    │     Redis       │
                        │  (Base de Datos)│    │(Broker/Cache)   │
                        └─────────────────┘    └─────────────────┘
```

### Componentes Principales

1. **Nginx**: Proxy reverso y servidor de archivos estáticos
2. **FastAPI**: API REST principal con autenticación JWT
3. **PostgreSQL**: Base de datos relacional para persistencia
4. **Redis**: Broker de mensajes para Celery y cache
5. **Celery**: Workers para procesamiento asíncrono de videos
6. **Docker**: Contenedorización de todos los servicios

### Flujo de Procesamiento de Videos

```
Usuario → Upload Video → API → Queue Task → Celery Worker → Process Video → Update DB
                         ↓                                        ↓
                    Save to Storage                        Save Processed Video
```

## Modelo de Datos

### Diagrama Entidad-Relación

```
┌─────────────────────┐
│       Users         │
├─────────────────────┤
│ + id (PK)          │
│ + email (UNIQUE)   │
│ + first_name       │
│ + last_name        │
│ + city             │
│ + country          │
│ + hashed_password  │
│ + is_active        │
│ + created_at       │
│ + updated_at       │
└─────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────┐         ┌─────────────────────┐
│       Videos        │         │       Votes         │
├─────────────────────┤         ├─────────────────────┤
│ + id (PK)          │◄────────┤ + id (PK)          │
│ + title            │ 1:N     │ + voter_id (FK)    │
│ + status           │         │ + video_id (FK)    │
│ + original_filename│         │ + created_at       │
│ + original_path    │         └─────────────────────┘
│ + processed_path   │
│ + task_id          │
│ + error_message    │
│ + created_at       │
│ + updated_at       │
│ + processed_at     │
│ + owner_id (FK)    │
└─────────────────────┘
```

### Descripción de Entidades

#### Users
- **Propósito**: Almacena información de jugadores registrados
- **Campos clave**: email único, información personal, contraseña hasheada
- **Relaciones**: 1:N con Videos, 1:N con Votes

#### Videos
- **Propósito**: Gestiona videos subidos y su estado de procesamiento
- **Estados**: uploaded, processing, processed, failed
- **Campos clave**: rutas de archivos, task_id de Celery, timestamps
- **Relaciones**: N:1 con Users, 1:N con Votes

#### Votes
- **Propósito**: Registra votos del público por videos
- **Restricciones**: Un voto por usuario por video (constraint única)
- **Relaciones**: N:1 con Users y Videos

## API REST

### Autenticación

#### POST /api/auth/signup
Registro de nuevos usuarios.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe", 
  "email": "john@example.com",
  "password1": "StrongPass123",
  "password2": "StrongPass123",
  "city": "Bogotá",
  "country": "Colombia"
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "city": "Bogotá", 
  "country": "Colombia",
  "is_active": true,
  "created_at": "2024-10-17T12:00:00Z"
}
```

#### POST /api/auth/login
Autenticación de usuarios.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "StrongPass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

### Gestión de Videos

#### POST /api/videos/upload
Subida de videos con procesamiento asíncrono.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data:**
- `video_file`: Archivo de video (MP4, AVI, MOV, etc.)
- `title`: Título del video

**Response (201):**
```json
{
  "message": "Video subido correctamente. Procesamiento en curso.",
  "task_id": "abc123-def456-ghi789"
}
```

#### GET /api/videos
Lista videos del usuario autenticado.

**Response (200):**
```json
[
  {
    "video_id": "123456",
    "title": "Mi mejor tiro de 3",
    "status": "processed",
    "uploaded_at": "2024-10-17T14:30:00Z",
    "processed_at": "2024-10-17T14:35:00Z",
    "processed_url": "/api/videos/123456/download"
  }
]
```

### Sistema de Votación Pública

#### GET /api/public/videos
Lista videos públicos disponibles para votación.

**Query Parameters:**
- `limit`: Número máximo de resultados (default: 50, max: 100)
- `offset`: Desplazamiento para paginación (default: 0)

#### POST /api/public/videos/{video_id}/vote
Emite voto por un video.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "message": "Voto registrado exitosamente."
}
```

#### GET /api/public/rankings
Obtiene ranking de jugadores por votos.

**Query Parameters:**
- `city`: Filtrar por ciudad (opcional)
- `limit`: Número máximo de resultados (default: 50, max: 100)

**Response (200):**
```json
[
  {
    "position": 1,
    "username": "John Doe",
    "city": "Bogotá",
    "votes": 1530
  }
]
```

## Procesamiento Asíncrono

### Arquitectura Celery

La aplicación utiliza Celery con Redis como broker para el procesamiento asíncrono de videos.

#### Configuración
- **Broker**: Redis (redis://redis:6379/0)
- **Backend**: Redis (mismo que broker)
- **Serializer**: JSON
- **Timezone**: UTC

#### Task: process_video_task

**Responsabilidades:**
1. Recortar video a máximo 30 segundos
2. Ajustar resolución a 720p (16:9)
3. Agregar logo ANB (intro/outro + watermark)
4. Remover audio
5. Guardar video procesado
6. Actualizar estado en base de datos

**Flujo de Ejecución:**
```python
@celery_app.task(bind=True)
def process_video_task(self, video_id: str, video_path: str):
    # 1. Actualizar estado a "processing"
    # 2. Cargar y procesar video con MoviePy
    # 3. Aplicar transformaciones (recorte, resize, watermark)
    # 4. Guardar video procesado
    # 5. Actualizar estado a "processed" o "failed"
```

**Manejo de Errores:**
- Reintentos automáticos (máximo 3)
- Backoff exponencial (60 segundos)
- Logging detallado de errores
- Actualización de estado a "failed" en caso de fallo definitivo

## Seguridad

### Autenticación JWT

#### Configuración
- **Algoritmo**: HS256
- **Tiempo de expiración**: 30 minutos
- **Secret Key**: Configurable via variables de entorno

#### Implementación
```python
def create_access_token(subject: str, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

### Protección de Endpoints

#### Middleware de Autenticación
```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    # Validar token JWT
    # Extraer email del payload
    # Verificar usuario en base de datos
    # Retornar usuario o lanzar excepción
```

#### Endpoints Protegidos
- Todos los endpoints de `/api/videos/*` requieren autenticación
- `/api/public/videos/{video_id}/vote` requiere autenticación
- `/api/public/videos` y `/api/public/rankings` son públicos

### Gestión de Contraseñas

#### Hashing
- **Algoritmo**: bcrypt
- **Rounds**: Default (12)
- **Validación**: Longitud mínima de 8 caracteres

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

## Despliegue

### Contenedorización Docker

#### Dockerfile
```dockerfile
FROM python:3.13-slim

# Dependencias del sistema para video processing
RUN apt-get update && apt-get install -y \
    ffmpeg libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app /app/app
RUN mkdir -p /app/uploads /app/processed_videos

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

**Servicios incluidos:**
1. **postgres**: Base de datos PostgreSQL 15
2. **redis**: Cache y broker Redis 7
3. **api**: Aplicación FastAPI principal
4. **worker**: Workers Celery para procesamiento
5. **flower**: Monitoreo de Celery (opcional)
6. **nginx**: Proxy reverso

#### Configuración de Red
- Red interna: `anb_network`
- Puertos expuestos: 80 (nginx), 8000 (api), 5555 (flower)
- Volúmenes persistentes: postgres_data, redis_data

### Variables de Entorno

```bash
# Base de datos
DATABASE_URL=postgresql://anb_user:anb_password@postgres:5432/anb_db

# JWT
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Archivos
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100
```

### Nginx Configuración

#### Proxy Reverso
```nginx
upstream api {
    server api:8000;
}

server {
    listen 80;
    
    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /processed/ {
        alias /var/www/processed_videos/;
        expires 1d;
    }
}
```

## Pruebas

### Estrategia de Pruebas

#### Tipos de Pruebas
1. **Pruebas Unitarias**: Funciones y servicios individuales
2. **Pruebas de Integración**: Endpoints de API
3. **Pruebas de Seguridad**: Autenticación y autorización

#### Configuración pytest
```ini
[tool:pytest]
testpaths = tests
addopts = 
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
```

### Cobertura de Pruebas

#### Módulos Cubiertos
- **Autenticación**: Registro, login, JWT
- **Videos**: Upload, listado, detalle, eliminación
- **Votación**: Votación pública, rankings
- **Seguridad**: Hashing de contraseñas, tokens
- **Almacenamiento**: Gestión de archivos

#### Métricas Objetivo
- **Cobertura mínima**: 80%
- **Cobertura objetivo**: 90%
- **Líneas cubiertas**: >500 líneas de código

### Ejecución de Pruebas

#### Local
```bash
# Todas las pruebas
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Pruebas específicas
pytest tests/test_auth.py -v
```

#### CI/CD
```bash
# En GitHub Actions
pytest --cov=app --cov-report=xml --cov-report=term-missing
```

## Análisis de Calidad

### Herramientas de Calidad

#### SonarQube
- **Quality Gate**: Configurado para rechazar si falla
- **Métricas monitoreadas**:
  - Bugs: 0 tolerancia
  - Vulnerabilidades: 0 tolerancia
  - Code Smells: <10
  - Cobertura: >80%
  - Duplicación: <3%

#### Linting
```bash
# Flake8 para estilo
flake8 app tests --max-line-length=127

# Black para formateo
black app tests

# isort para imports
isort app tests
```

#### Seguridad
```bash
# Safety para vulnerabilidades
safety check

# Bandit para análisis de seguridad
bandit -r app/
```

### Métricas de Calidad

#### Estándares de Código
- **Máxima complejidad ciclomática**: 10
- **Longitud máxima de línea**: 127 caracteres
- **Convenciones**: PEP 8

#### Documentación
- **Docstrings**: Obligatorios en funciones públicas
- **Comentarios**: Para lógica compleja
- **README**: Completo y actualizado

## Conclusiones

La implementación de la primera entrega del proyecto ANB Rising Stars Showcase cumple con todos los requerimientos establecidos:

1. ✅ **API REST escalable** con todos los endpoints especificados
2. ✅ **Autenticación JWT** segura y robusta
3. ✅ **Procesamiento asíncrono** con Celery y Redis
4. ✅ **Gestión de archivos** con capa de abstracción
5. ✅ **Contenedorización** completa con Docker
6. ✅ **Pruebas unitarias** con cobertura >80%
7. ✅ **CI/CD pipeline** con GitHub Actions
8. ✅ **Análisis de calidad** con SonarQube

### Próximos Pasos (Entrega 2)

1. Migración a servicios de nube (AWS/Azure)
2. Implementación de CDN para videos
3. Escalabilidad horizontal con Kubernetes
4. Monitoreo y observabilidad
5. Optimización de base de datos