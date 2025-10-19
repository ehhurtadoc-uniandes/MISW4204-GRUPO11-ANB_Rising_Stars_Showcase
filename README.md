# ANB Rising Stars Showcase

## Información del Equipo

**Grupo 11 - Team ANB**
- Integrante 1 - [correo1@uniandes.edu.co] - [Rol en el proyecto]
- Integrante 2 - [correo2@uniandes.edu.co] - [Rol en el proyecto]
- Integrante 3 - [correo3@uniandes.edu.co] - [Rol en el proyecto]

*Por favor, actualice esta sección con la información real del equipo antes de la entrega.*

## Video de Sustentación

El video de sustentación para la Entrega 1 estará disponible en: [sustentacion/Entrega_1/](sustentacion/Entrega_1/)

## Enlaces Importantes

- **Documentación Completa**: [docs/Entrega_1/README.md](docs/Entrega_1/README.md)
- **Plan de Análisis de Capacidad**: [capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)
- **Colecciones Postman**: [collections/](collections/)
- **API Documentation**: http://localhost:8000/docs (cuando la aplicación esté ejecutándose)
- **Video de Sustentación**: [sustentacion/Entrega_1/](sustentacion/Entrega_1/)

## Descripción del Proyecto

Plataforma web escalable para la gestión del programa Rising Stars Showcase de la Asociación Nacional de Baloncesto (ANB), que permite a jóvenes jugadores subir videos de sus habilidades para ser evaluados y votados por el público y jurado especializado.

## Tecnologías Utilizadas

- **Backend**: Python 3.13 + FastAPI 0.118
- **Base de Datos**: PostgreSQL
- **Procesamiento Asíncrono**: Celery + Redis
- **Proxy Reverso**: Nginx
- **Servidor WSGI**: Uvicorn
- **Contenedores**: Docker + Docker Compose
- **OS Base**: Ubuntu Server 24.04 LTS

## Arquitectura del Sistema

El sistema está compuesto por los siguientes componentes:
- API REST (FastAPI)
- Workers de procesamiento asíncrono (Celery)
- Broker de mensajes (Redis)
- Base de datos (PostgreSQL)
- Proxy reverso (Nginx)
- Almacenamiento de archivos (sistema de archivos local)

## Instalación y Despliegue

### Prerrequisitos
- Docker y Docker Compose
- Python 3.13+ (para desarrollo local)
- Ubuntu Server 24.04 LTS (recomendado)

### Despliegue con Docker
```bash
# Clonar el repositorio
git clone <repository-url>
cd MISW4204-GRUPO11-ANB_Rising_Stars_Showcase

# Construir y ejecutar los servicios
docker-compose up --build -d

# La aplicación estará disponible en:
# - API: http://localhost:8000
# - Nginx: http://localhost
# - Flower (Celery): http://localhost:5555
# - Swagger UI: http://localhost:8000/docs
```

### Comandos de Gestión

```bash
# Levantar todos los servicios
docker-compose up -d

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (limpieza completa)
docker-compose down -v --remove-orphans

# Reconstruir desde cero
docker-compose down -v --remove-orphans
docker system prune -a --volumes -f
docker-compose up --build -d
```

### Desarrollo Local
```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar migraciones
alembic upgrade head

# Ejecutar la aplicación
uvicorn app.main:app --reload
```

## API Documentation

La documentación interactiva de la API está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estructura del Proyecto

```
├── app/                    # Código fuente de la aplicación
│   ├── api/               # Endpoints de la API REST
│   ├── core/              # Configuración y utilidades
│   ├── models/            # Modelos de base de datos
│   ├── schemas/           # Schemas de Pydantic
│   ├── services/          # Lógica de negocio
│   └── workers/           # Workers de Celery
├── docs/                  # Documentación del proyecto
│   └── Entrega_1/        # Documentación específica de la entrega 1
├── collections/           # Colecciones de Postman
├── capacity-planning/     # Análisis de capacidad
├── tests/                 # Pruebas unitarias
├── nginx/                 # Configuración de Nginx
├── docker-compose.yml     # Orquestación de servicios
└── Dockerfile            # Imagen de la aplicación
```

## Funcionalidades Principales

### Gestión de Usuarios
- Registro de jugadores
- Autenticación con JWT
- Gestión de perfiles

### Gestión de Videos
- Carga de videos
- Procesamiento asíncrono (recorte, formato, watermark)
- Consulta y eliminación de videos propios

### Sistema de Votación
- Votación pública por videos
- Ranking dinámico de jugadores
- Control anti-fraude (un voto por usuario por video)

## Pruebas

### Prerrequisitos para Ejecutar Pruebas
```bash
# Instalar dependencias de Python
pip install -r requirements.txt

# Instalar Newman CLI (opcional, para pruebas de API)
npm install -g newman
```

### Ejecutar Pruebas Unitarias
```bash
# Ejecutar todas las pruebas (32 tests)
python -m pytest tests/ -v

# Ejecutar con cobertura de código
python -m pytest tests/ --cov=app --cov-report=term-missing

# Ejecutar pruebas específicas
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_videos.py -v
python -m pytest tests/test_public.py -v
```

**Resultado esperado:**
- ✅ 32 tests pasando
- ✅ 76% cobertura de código
- ✅ Sin errores críticos

### Ejecutar Pruebas de API (Postman)
```bash
# Primero, ejecutar la aplicación
docker-compose up

# En otra terminal, ejecutar las pruebas de Postman
newman run collections/anb-api.postman_collection.json \
  -e collections/postman_environment.json \
  --reporters cli
```

### Verificación Completa del Sistema
```bash
# 1. Verificar que la aplicación esté ejecutándose
curl http://localhost:8000/health

# 2. Ejecutar todas las pruebas unitarias
python -m pytest tests/ -v

# 3. Ejecutar pruebas de API (si la aplicación está corriendo)
newman run collections/anb-api.postman_collection.json \
  -e collections/postman_environment.json
```

### Solución de Problemas Comunes

**Error: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
pip install -r requirements.txt
```

**Error: "could not translate host name 'postgres'"**
- Las pruebas unitarias usan SQLite automáticamente
- Este error solo ocurre si se ejecuta la aplicación sin Docker

**Error: "newman: command not found"**
```bash
npm install -g newman
```

**Error: "Connection refused" en pruebas de Postman**
- Asegúrate de que la aplicación esté ejecutándose: `docker-compose up`
- Verifica que el puerto 8000 esté disponible

## CI/CD Pipeline

El proyecto incluye un pipeline de CI/CD con GitHub Actions que:
- Ejecuta pruebas unitarias
- Construye la aplicación
- Ejecuta análisis de calidad con SonarQube
- Valida la construcción de contenedores Docker

## Análisis de Capacidad (Plan B)

El proyecto incluye un análisis completo de capacidad del worker implementado según los requerimientos del documento de análisis de capacidad.

### Ejecutar Análisis de Capacidad

```bash
# Demo rápido del Plan B (2 minutos)
python capacity-planning/run_plan_b_demo.py

# Análisis completo del Plan B
python capacity-planning/plan_b_executor.py

# Pruebas específicas
python capacity-planning/worker_saturation_test.py --test-type saturation
python capacity-planning/worker_sustained_test.py --test-type sustained
```

### Documentación del Análisis de Capacidad

- **Plan de Pruebas**: [capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)
- **Resultados de Pruebas**: [capacity-planning/](capacity-planning/)
- **Scripts de Prueba**: 
  - `worker_bypass.py` - Bypass de la web para inyección directa
  - `simulated_worker.py` - Worker simulado para procesamiento
  - `plan_b_executor.py` - Ejecutor completo del Plan B

### Métricas del Plan B

- **Throughput máximo**: 45.8 videos/min (50MB, 4 workers)
- **Configuración óptima**: 50MB con 2 workers (32.1 videos/min)
- **Estabilidad**: Sistema estable con CPU < 90%, Memory < 85%
- **Bottlenecks identificados**: CPU, memoria e I/O

## Documentación Adicional

- [Entrega 1 - Documentación Completa](docs/Entrega_1/)
- [Análisis de Capacidad](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)
- [Video de Sustentación](sustentacion/Entrega_1/)

## Licencia

Este proyecto es desarrollado como parte del curso MISW4204 - Desarrollo de Software en la Nube, Universidad de los Andes.