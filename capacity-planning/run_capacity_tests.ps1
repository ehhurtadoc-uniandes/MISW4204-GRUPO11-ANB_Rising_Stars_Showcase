# Script de PowerShell para ejecutar pruebas de capacidad en Windows

Write-Host "Iniciando pruebas de capacidad para ANB Rising Stars Showcase" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Yellow

# Verificar que la aplicación esté ejecutándose
Write-Host "Verificando que la aplicación esté ejecutándose..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "Aplicación ejecutándose correctamente" -ForegroundColor Green
    } else {
        Write-Host "ERROR: La aplicación no está respondiendo correctamente" -ForegroundColor Red
        Write-Host "   Ejecuta: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "ERROR: La aplicación no está ejecutándose en localhost:8000" -ForegroundColor Red
    Write-Host "   Ejecuta: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

# Instalar dependencias de Python si es necesario
Write-Host "Instalando dependencias de Python..." -ForegroundColor Cyan
try {
    pip install aiohttp asyncio psutil redis pyyaml
    Write-Host "Dependencias instaladas correctamente" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudieron instalar las dependencias" -ForegroundColor Red
    Write-Host "   Ejecuta manualmente: pip install aiohttp asyncio psutil redis pyyaml" -ForegroundColor Yellow
}

# Ejecutar pruebas de carga de la API
Write-Host "Ejecutando pruebas de carga de la API..." -ForegroundColor Cyan
try {
    python capacity-planning/load_test.py --scenario all --users 100 --duration 5
    Write-Host "Pruebas de carga de API completadas" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Falló la ejecución de pruebas de carga de API" -ForegroundColor Red
}

# Ejecutar pruebas de capacidad del worker
Write-Host "Ejecutando pruebas de capacidad del worker..." -ForegroundColor Cyan
try {
    python capacity-planning/worker_test.py --test-type all --video-size 50 --concurrency 2
    Write-Host "Pruebas de capacidad del worker completadas" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Falló la ejecución de pruebas de capacidad del worker" -ForegroundColor Red
}

# Iniciar servicios de monitoreo (opcional)
Write-Host "¿Deseas iniciar servicios de monitoreo? (y/n)" -ForegroundColor Yellow
$monitoring = Read-Host
if ($monitoring -eq "y" -or $monitoring -eq "Y") {
    Write-Host "Iniciando servicios de monitoreo..." -ForegroundColor Cyan
    try {
        docker-compose -f capacity-planning/docker-compose-monitoring.yml up -d
        Write-Host "Servicios de monitoreo iniciados" -ForegroundColor Green
        Write-Host "Accede a los dashboards:" -ForegroundColor Yellow
        Write-Host "   • Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor White
        Write-Host "   • Prometheus: http://localhost:9090" -ForegroundColor White
    } catch {
        Write-Host "ERROR: No se pudieron iniciar los servicios de monitoreo" -ForegroundColor Red
    }
}

Write-Host "Pruebas de capacidad completadas" -ForegroundColor Green
Write-Host "Resultados guardados en: capacity-planning/results_*.json" -ForegroundColor Yellow

# Mostrar resumen de archivos generados
Write-Host "`nArchivos de resultados generados:" -ForegroundColor Cyan
Get-ChildItem -Path "capacity-planning" -Filter "results_*.json" | ForEach-Object {
    Write-Host "   • $($_.Name)" -ForegroundColor White
}

Write-Host "`nPara ver los resultados:" -ForegroundColor Yellow
Write-Host "   • Abre los archivos JSON en un editor de texto" -ForegroundColor White
Write-Host "   • Usa herramientas como jq para formatear JSON" -ForegroundColor White
Write-Host "   • Consulta CAPACITY_ANALYSIS.md para interpretar los resultados" -ForegroundColor White
