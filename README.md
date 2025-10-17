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
- **Plan de Análisis de Capacidad**: [capacity-planning/plan_de_pruebas.md](capacity-planning/plan_de_pruebas.md)
- **Colecciones Postman**: [collections/](collections/)
- **API Documentation**: http://localhost:8000/docs (cuando la aplicación esté ejecutándose)

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
docker-compose up --build

# La aplicación estará disponible en http://localhost
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

### Ejecutar Pruebas Unitarias
```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar con cobertura
pytest --cov=app tests/

# Ejecutar pruebas específicas
pytest tests/test_auth.py
```

### Ejecutar Pruebas de API (Postman)
```bash
# Instalar Newman (CLI de Postman)
npm install -g newman

# Ejecutar colección de pruebas
newman run collections/anb-api.postman_collection.json \
  -e collections/postman_environment.json
```

## CI/CD Pipeline

El proyecto incluye un pipeline de CI/CD con GitHub Actions que:
- Ejecuta pruebas unitarias
- Construye la aplicación
- Ejecuta análisis de calidad con SonarQube
- Valida la construcción de contenedores Docker

## Documentación Adicional

- [Entrega 1 - Documentación Completa](docs/Entrega_1/)
- [Análisis de Capacidad](capacity-planning/plan_de_pruebas.md)
- [Video de Sustentación](sustentacion/Entrega_1/)

## Licencia

Este proyecto es desarrollado como parte del curso MISW4204 - Desarrollo de Software en la Nube, Universidad de los Andes.