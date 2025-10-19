#!/usr/bin/env python3
"""
Script simplificado para configurar pruebas de capacidad
"""

import os
import json
from datetime import datetime

def create_requirements():
    """Crear archivo de requirements para las pruebas de capacidad"""
    requirements = """# Dependencias para pruebas de capacidad
aiohttp==3.9.1
asyncio
psutil==5.9.6
redis==5.0.1
pyyaml==6.0.1
"""
    
    with open("capacity-planning/requirements.txt", 'w') as f:
        f.write(requirements)
    
    print("Requirements para pruebas de capacidad creados")

def create_run_script():
    """Crear script de ejecución de pruebas de carga"""
    script_content = """#!/bin/bash
# Script para ejecutar pruebas de capacidad completas

echo "Iniciando pruebas de capacidad para ANB Rising Stars Showcase"
echo "================================================================"

# Verificar que la aplicación esté ejecutándose
echo "Verificando que la aplicación esté ejecutándose..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "ERROR: La aplicación no está ejecutándose en localhost:8000"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi
echo "Aplicación ejecutándose"

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
"""
    
    with open("capacity-planning/run_capacity_tests.sh", 'w') as f:
        f.write(script_content)
    
    # Hacer el script ejecutable
    os.chmod("capacity-planning/run_capacity_tests.sh", 0o755)
    
    print("Script de ejecución de pruebas creado")

def create_docker_compose_monitoring():
    """Crear docker-compose para servicios de monitoreo"""
    compose_content = """
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: anb_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./capacity-planning/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - anb_network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: anb_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - anb_network
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  anb_network:
    external: true
"""
    
    with open("capacity-planning/docker-compose-monitoring.yml", 'w') as f:
        f.write(compose_content)
    
    print("Docker Compose para monitoreo creado")

def create_prometheus_config():
    """Crear configuración de Prometheus"""
    config = {
        "global": {
            "scrape_interval": "5s",
            "evaluation_interval": "5s"
        },
        "scrape_configs": [
            {
                "job_name": "anb-api",
                "static_configs": [
                    {
                        "targets": ["api:8000"]
                    }
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "5s"
            }
        ]
    }
    
    with open("capacity-planning/prometheus.yml", 'w') as f:
        import yaml
        yaml.dump(config, f, default_flow_style=False)
    
    print("Configuración de Prometheus creada")

def main():
    """Configurar todo el entorno de monitoreo y pruebas de capacidad"""
    print("Configurando entorno de pruebas de capacidad...")
    
    # Crear directorio si no existe
    os.makedirs("capacity-planning", exist_ok=True)
    
    # Crear configuraciones
    create_prometheus_config()
    create_docker_compose_monitoring()
    create_run_script()
    create_requirements()
    
    print("\n" + "="*60)
    print("CONFIGURACION DE PRUEBAS DE CAPACIDAD COMPLETADA")
    print("="*60)
    print("\nArchivos creados:")
    print("   • capacity-planning/load_test.py - Pruebas de carga de API")
    print("   • capacity-planning/worker_test.py - Pruebas de capacidad del worker")
    print("   • capacity-planning/prometheus.yml - Configuración de Prometheus")
    print("   • capacity-planning/docker-compose-monitoring.yml - Servicios de monitoreo")
    print("   • capacity-planning/run_capacity_tests.sh - Script de ejecución")
    print("   • capacity-planning/requirements.txt - Dependencias")
    
    print("\nPara ejecutar las pruebas:")
    print("   1. Asegúrate de que la aplicación esté ejecutándose:")
    print("      docker-compose up -d")
    print("   2. Ejecuta las pruebas de capacidad:")
    print("      ./capacity-planning/run_capacity_tests.sh")
    print("   3. Accede a los dashboards:")
    print("      • Grafana: http://localhost:3000 (admin/admin123)")
    print("      • Prometheus: http://localhost:9090")
    
    print("\nEscenarios de prueba implementados:")
    print("   Smoke Test - 5 usuarios durante 1 minuto")
    print("   Ramp Test - Escalamiento gradual de usuarios")
    print("   Sustained Test - Carga sostenida")
    print("   Worker Saturation Test - Pruebas de saturación del worker")
    print("   Worker Sustained Test - Pruebas sostenidas del worker")
    
    print("\nListo para ejecutar análisis de capacidad!")

if __name__ == "__main__":
    main()
