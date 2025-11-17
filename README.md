# ANB Rising Stars Showcase

## Información del Equipo

**Grupo 11 - Team ANB**
- Sergio Fernando Barrera Molano - [sf.barreram1@uniandes.edu.co] - Desarrollador / Cloud Junior
- Harold Andrés Bartolo Moscoso - [h.bartolo@uniandes.edu.co] - Desarrollador / Cloud Junior
- Edwin Hernán Hurtado Cruz - [eh.hurtado@uniandes.edu.co] - Desarrollador / Cloud Junior
- Juan José Restrepo Bonilla - [jj.restrepob1@uniandes.edu.co] - Desarrollador / Cloud Junior

## Video de Sustentación

El video de sustentación para la Entrega 1 esta disponible en: [sustentacion/Entrega_1/](sustentacion/Entrega_1/)

El video de sustentación para la Entrega 2 esta disponible en: [Sustentacion entrega_2](https://uniandes-my.sharepoint.com/:v:/g/personal/sf_barreram1_uniandes_edu_co/ER30KqTZtkROkaRrtZp3ICkBs7q8I5HYmNjdg73uokdplA?e=SlC9Lt)

El vídeo de sustentación para la Entrega 4 está disponible en: [Sustentacion entrega_4](https://uniandes-my.sharepoint.com/:v:/g/personal/sf_barreram1_uniandes_edu_co/IQA6v9ipB7_nQqhKhtSnTbH0ATk_-leyQKNQ-L3UJ4VylF8?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=8ksOr3)

## Enlaces Importantes

- **Documentación Completa**: [docs/Entrega_1/README.md](docs/Entrega_1/README.md)
- **Análisis de Capacidad - Entrega 2**: [capacity-planning/pruebas_de_carga_entrega2.md](capacity-planning/pruebas_de_carga_entrega2.md)
- **Plan de Análisis de Capacidad**: [capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)
- **Colecciones Postman**: [collections/](collections/)
- **API Documentation**: http://localhost:8000/docs (cuando la aplicación esté ejecutándose)
- **Video de Sustentación**: [sustentacion/Entrega_1/](sustentacion/Entrega_1/)
- **Pipeline CI/CD**: [GitHub Actions](https://github.com/your-repo/actions) (ver sección CI/CD más abajo)

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

### Despliegue en AWS

Para desplegar la aplicación en AWS con alta disponibilidad, escalabilidad y seguridad, consulta la **Guía Completa de Despliegue en AWS**:

📖 **[Guía de Despliegue en AWS - Entrega 3](docs/Entrega_3/AWS_DEPLOYMENT_GUIDE.md)**

📐 **[Diagrama de Arquitectura AWS](docs/Entrega_3/Arquitectura.drawio.pdf)** - Diagrama visual de la arquitectura completa del sistema en AWS

La guía incluye instrucciones paso a paso para configurar:
- ✅ VPC y Networking
- ✅ RDS (PostgreSQL)
- ✅ EC2 Redis
- ✅ S3 Bucket (usado por Backend y Worker)
- ✅ Application Load Balancer (ALB)
- ✅ Auto Scaling Group (Backend)
- ✅ EC2 Worker
- ✅ Security Groups y IAM Roles
- ✅ Integración con S3
- ✅ Scripts de automatización de despliegue

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

El proyecto incluye un análisis completo de capacidad del worker implementado según los requerimientos del documento de análisis de capacidad. **Ver [Análisis de Capacidad - Entrega 2](capacity-planning/pruebas_de_carga_entrega2.md) para el reporte completo ejecutado en AWS EC2.**

### Ejecutar Análisis de Capacidad

#### 🚀 Demo Rápido (Recomendado para empezar)
```bash
# Demo del Plan B - 2 minutos
python capacity-planning/run_plan_b_demo.py
```

**Resultado esperado:**
```
======================================================================
DEMO DEL PLAN B - ANÁLISIS DE CAPACIDAD DEL WORKER
======================================================================
Estado del demo: completed
Componentes probados: 3
Componentes exitosos: 3
Componentes fallidos: 0

==================================================
MÉTRICAS CLAVE
==================================================
Throughput del worker: 30.0 jobs/min
Trabajos procesados: 1
Throughput máximo: 4.8 videos/min
Punto de saturación: 500 trabajos
Estabilidad: Estable
Tasa de errores: 0.00%

==================================================
RECOMENDACIONES
==================================================
1. Throughput máximo: 4.8 videos/min
2. Sistema estable en configuración de prueba

======================================================================
DEMO COMPLETADO
======================================================================
```

#### 📊 Análisis Completo
```bash
# Análisis completo del Plan B (10-15 minutos)
python capacity-planning/plan_b_executor.py

# Pruebas específicas
python capacity-planning/worker_saturation_test.py --test-type saturation
python capacity-planning/worker_sustained_test.py --test-type sustained
```

#### 🔧 Prerequisitos
- **Redis**: Debe estar ejecutándose (puerto 6379)
- **Python**: 3.11+ con dependencias instaladas
- **Tiempo**: Demo 2 min, Análisis completo 10-15 min

#### 📈 Interpretación de Resultados
- **Throughput**: Videos procesados por minuto
- **Saturación**: Punto donde el sistema se degrada
- **Estabilidad**: Sistema estable bajo carga
- **Bottlenecks**: CPU, memoria, I/O identificados

#### 🔧 Troubleshooting

**Error: "Redis no conectado"**
```bash
# Iniciar Redis con Docker
docker run -d --name redis -p 6379:6379 redis:alpine

# O con Docker Compose
docker-compose up redis -d
```

**Error: "ModuleNotFoundError"**
```bash
# Instalar dependencias
pip install aiohttp psutil redis
```

**Demo no muestra resultados**
- Verificar que Redis esté ejecutándose
- Revisar logs para errores específicos
- Ejecutar con `python -u` para output sin buffer

### Documentación del Análisis de Capacidad

- **Reporte Completo - Entrega 2**: [capacity-planning/pruebas_de_carga_entrega2.md](capacity-planning/pruebas_de_carga_entrega2.md) - **Análisis ejecutado en AWS EC2**
- **Plan de Pruebas**: [capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)
- **Resultados de Pruebas**: [capacity-planning/RESULTS_SUMMARY.md](capacity-planning/RESULTS_SUMMARY.md)
- **Archivos de Resultados**: [capacity-planning/](capacity-planning/)
- **Scripts de Prueba**: 
  - `worker_bypass.py` - Bypass de la web para inyección directa
  - `simulated_worker.py` - Worker simulado para procesamiento
  - `plan_b_executor.py` - Ejecutor completo del Plan B

### Métricas del Plan B

- **Throughput máximo**: 45.8 videos/min (50MB, 4 workers)
- **Configuración óptima**: 50MB con 2 workers (32.1 videos/min)
- **Estabilidad**: Sistema estable con CPU < 90%, Memory < 85%
- **Bottlenecks identificados**: CPU, memoria e I/O

## CI/CD Pipeline

### Pipeline de GitHub Actions

El proyecto incluye un pipeline completo de CI/CD que se ejecuta automáticamente en cada push y pull request:

#### Etapas del Pipeline

1. **Tests Unitarios** (`test`)
   - Ejecuta 32 tests unitarios
   - Genera reporte de cobertura (54%)
   - Sube resultados a Codecov
   - Excluye scripts de capacity-planning

2. **Build Automático** (`build`)
   - Construye imagen Docker
   - Valida Docker Compose
   - **Genera artefacto**: `docker-image.tar`
   - Retención: 30 días

3. **Análisis de Calidad** (`sonarqube`)
   - SonarQube scan automático
   - Detección de vulnerabilidades
   - Métricas de calidad del código

4. **Security Check** (`security`)
   - Safety check para dependencias
   - Bandit security linter
   - Reportes de seguridad

#### Cómo Usar el Artefacto Generado

El pipeline genera automáticamente un artefacto Docker que puedes descargar y usar:

```bash
# 1. Descargar artefacto desde GitHub Actions
# Ir a: Actions → CI/CD Pipeline → build job → Artifacts
# Descargar: docker-image.tar

# 2. Cargar la imagen Docker
docker load -i anb-api.tar

# 3. Verificar que se cargó
docker images | grep anb-api

# 4. Ejecutar la aplicación
docker run -d --name anb-api -p 8000:8000 anb-api:latest

# 5. Verificar que funciona
curl http://localhost:8000/health
```

#### Ubicación del Artefacto

- **GitHub Actions**: `Actions` tab → `CI/CD Pipeline` → `build` job → `Artifacts`
- **Nombre**: `docker-image`
- **Formato**: `anb-api.tar` (imagen Docker comprimida)
- **Retención**: 30 días
- **Tamaño**: ~100-500MB

#### Comandos Completos

```bash
# Descargar y usar el artefacto
wget https://github.com/your-repo/actions/runs/123456789/artifacts/docker-image.tar
docker load -i docker-image.tar
docker run -d --name anb-api -p 8000:8000 anb-api:latest
curl http://localhost:8000/health

# Ver logs
docker logs anb-api

# Detener
docker stop anb-api
docker rm anb-api
```

## Documentación Adicional

### Entrega 1
- [Documentación Completa](docs/Entrega_1/)
- [Video de Sustentación](sustentacion/Entrega_1/)

### Entrega 2
- [Análisis de Capacidad - Entrega 2](capacity-planning/pruebas_de_carga_entrega2.md) - **Ejecutado en AWS EC2**
- [Plan de Análisis de Capacidad](capacity-planning/CAPACITY_ANALYSIS_PLAN_B.md)

### Entrega 3
- **[Guía de Despliegue en AWS](docs/Entrega_3/AWS_DEPLOYMENT_GUIDE.md)** - Documentación completa de la arquitectura y despliegue en AWS
- **[Diagrama de Arquitectura AWS](docs/Entrega_3/Arquitectura.drawio.pdf)** - Diagrama visual de la arquitectura del sistema
- **[Documento de Pruebas - Entrega 3](capacity-planning/Documento%20de%20Pruebas%20Proyecto%20-%20Entrega%203.pdf)** - Documento completo de pruebas de capacidad y rendimiento
- **[Video de Sustentación - Entrega 3](https://uniandes-my.sharepoint.com/:v:/g/personal/sf_barreram1_uniandes_edu_co/EVCUxa-NzfpFqHhbelp9JncBadBKy3sSelYfrgdUvq8WCQ?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=JNtdTx)** - Video de sustentación de la Entrega 3

### Entrega 4
- **[Documento de Arquitectura](docs/Entrega_4/ARQUITECTURA.md)** - Arquitectura completa del sistema con modelo de despliegue y componentes
- **[Imágen de la Arquitectura](docs/Entrega_4/Arquitectura.pdf)** - Imágen de la arquitectura
- **[Documento de Pruebas - Entrega 4](docs/Entrega_4/Documento%20de%20Pruebas%20Proyecto%20-%20Entrega%204.pdf)** - Documento completo de pruebas
- **[Guía de Despliegue en AWS](docs/Entrega_4/AWS_DEPLOYMENT_GUIDE.md)** - Guía paso a paso para desplegar la arquitectura escalable y de alta disponibilidad
- **[Plan de Migración](docs/Entrega_4/MIGRATION_PLAN.md)** - Plan de migración desde Entrega 3 a Entrega 4
- **[Guía de Migración SQS](docs/Entrega_4/SQS_MIGRATION_GUIDE.md)** - Detalles técnicos de la migración de Celery/Redis a SQS
- **[Video de Sustentación - Entrega 4](https://uniandes-my.sharepoint.com/:v:/g/personal/sf_barreram1_uniandes_edu_co/IQA6v9ipB7_nQqhKhtSnTbH0ATk_-leyQKNQ-L3UJ4VylF8?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=8ksOr3)** - Video de sustentación de la Entrega 4

## Licencia

Este proyecto es desarrollado como parte del curso MISW4204 - Desarrollo de Software en la Nube, Universidad de los Andes.
