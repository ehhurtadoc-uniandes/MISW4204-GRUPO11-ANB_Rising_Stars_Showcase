#!/usr/bin/env python3
"""
Script para configurar monitoreo con Prometheus y Grafana
para las pruebas de capacidad del sistema ANB Rising Stars Showcase
"""

import os
import yaml
import json
from datetime import datetime

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
            },
            {
                "job_name": "anb-worker",
                "static_configs": [
                    {
                        "targets": ["worker:8001"]
                    }
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "5s"
            },
            {
                "job_name": "redis",
                "static_configs": [
                    {
                        "targets": ["redis:6379"]
                    }
                ],
                "scrape_interval": "10s"
            },
            {
                "job_name": "postgres",
                "static_configs": [
                    {
                        "targets": ["postgres:5432"]
                    }
                ],
                "scrape_interval": "10s"
            }
        ]
    }
    
    with open("capacity-planning/prometheus.yml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("Configuracion de Prometheus creada")

def create_grafana_dashboard():
    """Crear dashboard de Grafana para monitoreo de capacidad"""
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "ANB Rising Stars - Capacity Monitoring",
            "tags": ["anb", "capacity", "performance"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Request Rate (RPS)",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total[5m])",
                            "legendFormat": "{{method}} {{endpoint}}"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Requests per second"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Response Time (P95)",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "P95 Response Time"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Seconds"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Error Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
                            "legendFormat": "Error Rate %"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Percentage"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "id": 4,
                    "title": "Active Connections",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "http_connections_active",
                            "legendFormat": "Active Connections"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Connections"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                },
                {
                    "id": 5,
                    "title": "CPU Usage",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(process_cpu_seconds_total[5m]) * 100",
                            "legendFormat": "{{instance}} CPU %"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Percentage"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
                },
                {
                    "id": 6,
                    "title": "Memory Usage",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "process_resident_memory_bytes / 1024 / 1024",
                            "legendFormat": "{{instance}} Memory MB"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "MB"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
                },
                {
                    "id": 7,
                    "title": "Queue Length (Redis)",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "redis_list_length{key=\"video_queue\"}",
                            "legendFormat": "Video Queue Length"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Tasks"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
                },
                {
                    "id": 8,
                    "title": "Database Connections",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "pg_stat_activity_count",
                            "legendFormat": "Active DB Connections"
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Connections"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
                }
            ],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "refresh": "5s"
        }
    }
    
    with open("capacity-planning/grafana-dashboard.json", 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    print("✅ Dashboard de Grafana creado")

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
      - ./capacity-planning/grafana-dashboard.json:/var/lib/grafana/dashboards/anb-capacity.json
    networks:
      - anb_network
    restart: unless-stopped
    depends_on:
      - prometheus

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: anb_redis_exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://redis:6379
    networks:
      - anb_network
    restart: unless-stopped

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: anb_postgres_exporter
    ports:
      - "9187:9187"
    environment:
      - DATA_SOURCE_NAME=postgresql://anb_user:anb_password@postgres:5432/anb_db?sslmode=disable
    networks:
      - anb_network
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:

networks:
  anb_network:
    external: true
"""
    
    with open("capacity-planning/docker-compose-monitoring.yml", 'w') as f:
        f.write(compose_content)
    
    print("✅ Docker Compose para monitoreo creado")

def create_load_test_script():
    """Crear script de ejecución de pruebas de carga"""
    script_content = """#!/bin/bash
# Script para ejecutar pruebas de capacidad completas

echo "🚀 Iniciando pruebas de capacidad para ANB Rising Stars Showcase"
echo "================================================================"

# Verificar que la aplicación esté ejecutándose
echo "🔍 Verificando que la aplicación esté ejecutándose..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ La aplicación no está ejecutándose en localhost:8000"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi
echo "✅ Aplicación ejecutándose"

# Instalar dependencias de Python si es necesario
echo "📦 Instalando dependencias de Python..."
pip install aiohttp asyncio psutil redis

# Ejecutar pruebas de carga de la API
echo "🔥 Ejecutando pruebas de carga de la API..."
python capacity-planning/load_test.py --scenario all --users 100 --duration 5

# Ejecutar pruebas de capacidad del worker
echo "🔧 Ejecutando pruebas de capacidad del worker..."
python capacity-planning/worker_test.py --test-type all --video-size 50 --concurrency 2

# Iniciar servicios de monitoreo
echo "📊 Iniciando servicios de monitoreo..."
docker-compose -f capacity-planning/docker-compose-monitoring.yml up -d

echo "✅ Pruebas de capacidad completadas"
echo "📊 Accede a los dashboards:"
echo "   • Grafana: http://localhost:3000 (admin/admin123)"
echo "   • Prometheus: http://localhost:9090"
echo "📁 Resultados guardados en: capacity-planning/results_*.json"
"""
    
    with open("capacity-planning/run_capacity_tests.sh", 'w') as f:
        f.write(script_content)
    
    # Hacer el script ejecutable
    os.chmod("capacity-planning/run_capacity_tests.sh", 0o755)
    
    print("✅ Script de ejecución de pruebas creado")

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
    
    print("✅ Requirements para pruebas de capacidad creados")

def main():
    """Configurar todo el entorno de monitoreo y pruebas de capacidad"""
    print("Configurando entorno de pruebas de capacidad...")
    
    # Crear directorio si no existe
    os.makedirs("capacity-planning", exist_ok=True)
    
    # Crear configuraciones
    create_prometheus_config()
    create_grafana_dashboard()
    create_docker_compose_monitoring()
    create_load_test_script()
    create_requirements()
    
    print("\n" + "="*60)
    print("🎯 CONFIGURACIÓN DE PRUEBAS DE CAPACIDAD COMPLETADA")
    print("="*60)
    print("\n📋 Archivos creados:")
    print("   • capacity-planning/load_test.py - Pruebas de carga de API")
    print("   • capacity-planning/worker_test.py - Pruebas de capacidad del worker")
    print("   • capacity-planning/monitoring_setup.py - Configuración de monitoreo")
    print("   • capacity-planning/prometheus.yml - Configuración de Prometheus")
    print("   • capacity-planning/grafana-dashboard.json - Dashboard de Grafana")
    print("   • capacity-planning/docker-compose-monitoring.yml - Servicios de monitoreo")
    print("   • capacity-planning/run_capacity_tests.sh - Script de ejecución")
    print("   • capacity-planning/requirements.txt - Dependencias")
    
    print("\n🚀 Para ejecutar las pruebas:")
    print("   1. Asegúrate de que la aplicación esté ejecutándose:")
    print("      docker-compose up -d")
    print("   2. Ejecuta las pruebas de capacidad:")
    print("      ./capacity-planning/run_capacity_tests.sh")
    print("   3. Accede a los dashboards:")
    print("      • Grafana: http://localhost:3000 (admin/admin123)")
    print("      • Prometheus: http://localhost:9090")
    
    print("\n📊 Escenarios de prueba implementados:")
    print("   🔥 Smoke Test - 5 usuarios durante 1 minuto")
    print("   📈 Ramp Test - Escalamiento gradual de usuarios")
    print("   ⏱️ Sustained Test - Carga sostenida")
    print("   🔧 Worker Saturation Test - Pruebas de saturación del worker")
    print("   ⏱️ Worker Sustained Test - Pruebas sostenidas del worker")
    
    print("\n✅ ¡Listo para ejecutar análisis de capacidad!")

if __name__ == "__main__":
    main()
