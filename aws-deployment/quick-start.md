# 🚀 Guía de Inicio Rápido - ANB Rising Stars Showcase AWS

## ⚡ Despliegue en 5 Pasos

### Paso 1: Prerrequisitos
```bash
# Instalar herramientas (Ubuntu/Debian)
sudo apt update
sudo apt install -y terraform awscli docker.io docker-compose python3-pip

# Configurar AWS CLI
aws configure
# Ingresa tu Access Key ID, Secret Access Key, región (us-east-1), formato (json)

# Generar par de claves SSH
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
```

### Paso 2: Configurar Variables
```bash
# Copiar archivo de configuración
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Editar configuración
nano terraform/terraform.tfvars
```

**Contenido de `terraform.tfvars`:**
```hcl
aws_region = "us-east-1"
instance_type = "t3.medium"
public_key_path = "~/.ssh/id_rsa.pub"
db_password = "TuPasswordSeguro123!"
environment = "production"
project_name = "ANB-Rising-Stars"
```

### Paso 3: Desplegar Infraestructura
```bash
# Ejecutar despliegue automático
export DB_PASSWORD="TuPasswordSeguro123!"
export SECRET_KEY="tu-clave-secreta-super-segura-para-produccion"

./deploy.sh
```

### Paso 4: Verificar Despliegue
```bash
# Obtener IP del servidor web
cd terraform
WEB_IP=$(terraform output -raw web_server_public_ip)
echo "Aplicación disponible en: http://$WEB_IP:8000"

# Probar endpoints
curl http://$WEB_IP:8000/health
curl http://$WEB_IP:8000/
```

### Paso 5: Acceder a la Aplicación
- **API**: http://[WEB_IP]:8000
- **Documentación**: http://[WEB_IP]:8000/docs
- **Health Check**: http://[WEB_IP]:8000/health

## 🔧 Comandos Útiles

### Verificar Estado
```bash
# Estado de instancias
aws ec2 describe-instances --filters "Name=tag:Project,Values=ANB-Rising-Stars"

# Estado de RDS
aws rds describe-db-instances --db-instance-identifier anb-postgres-db

# Estado de Redis
aws elasticache describe-replication-groups --replication-group-id anb-redis
```

### Conectar a Servidores
```bash
# Web Server
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP]

# Worker Server
ssh -i ~/.ssh/id_rsa ubuntu@[WORKER_IP]

# NFS Server
ssh -i ~/.ssh/id_rsa ubuntu@[NFS_IP]
```

### Ver Logs
```bash
# Logs de aplicación
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "cd /opt/anb-app && docker-compose logs -f"

# Logs de worker
ssh -i ~/.ssh/id_rsa ubuntu@[WORKER_IP] "cd /opt/anb-app && docker-compose logs -f worker"
```

## 🧪 Pruebas Rápidas

### Prueba Funcional
```bash
# Instalar dependencias
pip install requests

# Script de prueba
python3 -c "
import requests
import json

base_url = 'http://[WEB_IP]:8000'

# Probar endpoints
endpoints = ['/', '/health', '/docs']
for endpoint in endpoints:
    try:
        response = requests.get(f'{base_url}{endpoint}', timeout=10)
        print(f'✅ {endpoint}: {response.status_code}')
    except Exception as e:
        print(f'❌ {endpoint}: {e}')
"
```

### Prueba de Carga
```bash
# Instalar herramienta de carga
pip install aiohttp

# Ejecutar prueba
python3 load-test.py --url http://[WEB_IP]:8000 --users 10 --duration 60
```

## 🚨 Solución de Problemas Rápidos

### Problema: No puedo conectar por SSH
```bash
# Verificar Security Groups
aws ec2 describe-security-groups --filters "Name=tag:Project,Values=ANB-Rising-Stars"

# Verificar estado de instancia
aws ec2 describe-instances --filters "Name=tag:Project,Values=ANB-Rising-Stars"
```

### Problema: La aplicación no responde
```bash
# Verificar contenedores
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "docker ps"

# Verificar logs
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "cd /opt/anb-app && docker-compose logs"
```

### Problema: Base de datos no conecta
```bash
# Verificar RDS
aws rds describe-db-instances --db-instance-identifier anb-postgres-db

# Probar conectividad
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "telnet [RDS_ENDPOINT] 5432"
```

## 💰 Gestión de Costos

### Ver Costos Actuales
```bash
# Costos por servicio
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

### Limpiar Recursos (IMPORTANTE)
```bash
# Destruir toda la infraestructura
./cleanup.sh
```

## 📊 Monitoreo Básico

### Métricas de Sistema
```bash
# CPU y memoria
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "htop"

# Uso de disco
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "df -h"

# Estado de servicios
ssh -i ~/.ssh/id_rsa ubuntu@[WEB_IP] "systemctl status docker"
```

### Métricas de Aplicación
```bash
# Requests por segundo
curl -s http://[WEB_IP]:8000/health | jq

# Estado de worker
ssh -i ~/.ssh/id_rsa ubuntu@[WORKER_IP] "cd /opt/anb-app && docker-compose exec worker celery -A app.workers.celery_app inspect active"
```

## 🎯 Checklist de Verificación

- [ ] Infraestructura desplegada
- [ ] Web server respondiendo
- [ ] Worker procesando tareas
- [ ] NFS montado correctamente
- [ ] RDS conectado
- [ ] Redis funcionando
- [ ] API endpoints funcionando
- [ ] Documentación accesible
- [ ] Pruebas de carga pasando
- [ ] Monitoreo configurado

## 📞 Soporte Rápido

### Comandos de Diagnóstico
```bash
# Estado general
./deploy.sh --check

# Logs completos
./deploy.sh --logs

# Reiniciar servicios
./deploy.sh --restart
```

### Información de Contacto
- **Documentación**: Ver README.md
- **Arquitectura**: Ver ARCHITECTURE.md
- **Pruebas**: Ver TEST_RESULTS.md
- **Troubleshooting**: Ver TROUBLESHOOTING.md

---

**⚠️ IMPORTANTE**: Recuerda ejecutar `./cleanup.sh` después de completar la entrega para evitar costos innecesarios.
