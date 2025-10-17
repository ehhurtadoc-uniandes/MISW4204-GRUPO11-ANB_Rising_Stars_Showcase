# Script para ejecutar ANB Rising Stars Showcase localmente sin Docker
# Requiere Python 3.13, PostgreSQL y Redis instalados

Write-Host "🏀 ANB Rising Stars Showcase - Configuración Local" -ForegroundColor Green

# Verificar Python 3.13
Write-Host "`n📋 Verificando Python..." -ForegroundColor Yellow
python --version

# Crear entorno virtual
Write-Host "`n🔧 Creando entorno virtual..." -ForegroundColor Yellow
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependencias
Write-Host "`n📦 Instalando dependencias..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Configurar variables de entorno
Write-Host "`n⚙️ Configurando variables de entorno..." -ForegroundColor Yellow
$env:DATABASE_URL = "postgresql://postgres:password@localhost:5432/anb_showcase"
$env:REDIS_URL = "redis://localhost:6379"
$env:SECRET_KEY = "your-secret-key-here-please-change-in-production"
$env:ALGORITHM = "HS256"
$env:ACCESS_TOKEN_EXPIRE_MINUTES = "30"

Write-Host "`n📝 Variables configuradas:" -ForegroundColor Cyan
Write-Host "DATABASE_URL: $env:DATABASE_URL"
Write-Host "REDIS_URL: $env:REDIS_URL"

Write-Host "`n🚀 Para iniciar la aplicación:" -ForegroundColor Green
Write-Host "1. Asegurar PostgreSQL corriendo en puerto 5432"
Write-Host "2. Asegurar Redis corriendo en puerto 6379"
Write-Host "3. Ejecutar migraciones: alembic upgrade head"
Write-Host "4. Iniciar API: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host "5. Iniciar worker: celery -A app.workers.video_processor worker --loglevel=info"

Write-Host "`n📚 Documentación API disponible en: http://localhost:8000/docs" -ForegroundColor Blue