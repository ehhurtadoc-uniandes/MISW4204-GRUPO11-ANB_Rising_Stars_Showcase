#!/bin/bash
# Script para ejecutar pruebas de capacidad completas

echo "Iniciando pruebas de capacidad para ANB Rising Stars Showcase"
echo "================================================================"

# Verificar que la aplicaci�n est� ejecut�ndose
echo "Verificando que la aplicaci�n est� ejecut�ndose..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "ERROR: La aplicaci�n no est� ejecut�ndose en localhost:8000"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi
echo "Aplicaci�n ejecut�ndose"

# Instalar dependencias de Python si es necesario
echo "Instalando dependencias de Python..."
pip install aiohttp asyncio psutil redis

# Ejecutar pruebas de carga de la API
echo "Ejecutando pruebas de carga de la API..."
python capacity-planning/load_test.py --scenario all --users 100 --duration 5

# Ejecutar pruebas de capacidad del worker
echo "Ejecutando pruebas de capacidad del worker..."
python capacity-planning/worker_test.py --test-type all --video-size 50 --concurrency 2

echo "Pruebas de capacidad completadas"
echo "Resultados guardados en: capacity-planning/results_*.json"
