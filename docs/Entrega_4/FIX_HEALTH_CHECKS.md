# Fix: Health Checks Failing (Unhealthy Targets)

## Problema
- ✅ Backend está corriendo (`docker ps` muestra contenedor activo)
- ✅ Backend responde localmente (`curl localhost:8000/health` funciona)
- ❌ Target Group muestra instancias como "Unhealthy"
- ❌ Health checks están fallando

## Solución Rápida

### 1. Verificar Health Check Configuration

En el Target Group `anb-backend-tg`:

1. Ve a **Health checks** tab → **Edit**
2. Verifica:
   - **Health check protocol**: HTTP
   - **Health check path**: `/health` (debe ser exactamente esto, sin trailing slash)
   - **Port**: 8000 (o "Traffic port")
   - **Healthy threshold**: 2
   - **Unhealthy threshold**: 3
   - **Timeout**: 10 segundos (aumentar si es muy corto)
   - **Interval**: 30 segundos
   - **Success codes**: 200 (o "200-299")

3. **Guardar cambios** y esperar 2-3 minutos

### 2. Verificar Security Group del Backend

El Security Group del backend (`anb-backend-sg`) **DEBE** permitir tráfico desde el ALB:

1. Ve a **EC2 Dashboard** → **Security Groups** → `anb-backend-sg`
2. **Inbound rules** → **Edit inbound rules**
3. Verifica que exista una regla:
   - **Type**: Custom TCP
   - **Port**: 8000
   - **Source**: Security Group del ALB (`anb-alb-sg` o el ID del SG del ALB)
   - **Description**: "Allow ALB health checks"

Si no existe, **agregarla**:
- Click **Add rule**
- **Type**: Custom TCP
- **Port range**: 8000
- **Source**: Seleccionar "Security group" → Buscar `anb-alb-sg`
- **Description**: "Allow ALB health checks"
- **Save rules**

### 3. Verificar Security Group del ALB

El Security Group del ALB debe permitir tráfico saliente:

1. Ve a **EC2 Dashboard** → **Security Groups** → Security Group del ALB
2. **Outbound rules** → Debe permitir tráfico a cualquier destino (0.0.0.0/0) en puerto 8000

### 4. Probar Health Check Manualmente

Desde una instancia del backend, prueba si el health check funciona:

```bash
# Desde dentro de la instancia EC2 del backend
curl -v http://localhost:8000/health

# Deberías ver:
# HTTP/1.1 200 OK
# {"status":"healthy","environment":"production"}
```

Si esto funciona pero el ALB no puede, el problema es de Security Groups.

### 5. Verificar que la App Escucha en 0.0.0.0

Verifica que la aplicación esté escuchando en todas las interfaces:

```bash
# En la instancia del backend
netstat -tlnp | grep 8000
# O
ss -tlnp | grep 8000

# Deberías ver:
# 0.0.0.0:8000 (no 127.0.0.1:8000)
```

Si ves `127.0.0.1:8000`, la app solo escucha localmente y el ALB no podrá conectarse.

### 6. Ver Logs del Health Check

El ALB envía requests con un User-Agent específico. Puedes verificar en los logs:

```bash
# En la instancia del backend
docker logs anb-api | grep -i health

# Busca requests del ALB (IPs internas de AWS)
# Deberías ver requests como:
# INFO: 10.0.XX.XX:XXXXX - "GET /health HTTP/1.1" 200 OK
```

Si no ves requests del ALB, el Security Group está bloqueando el tráfico.

## Diagnóstico Detallado

### Verificar IPs del ALB

El ALB usa IPs privadas de AWS. Puedes verificar desde CloudWatch:

1. Ve a **CloudWatch** → **Metrics** → **ApplicationELB**
2. Selecciona tu ALB
3. Busca métricas de "HealthyHostCount" y "UnHealthyHostCount"

### Probar desde Otra Instancia

Si tienes acceso a otra instancia EC2 en la misma VPC:

```bash
# Desde otra instancia EC2 (no el backend)
curl http://PRIVATE_IP_BACKEND:8000/health

# Si esto funciona, el problema es específico del ALB
# Si no funciona, el Security Group del backend está bloqueando
```

## Checklist

- [ ] Health check path es `/health` (sin trailing slash)
- [ ] Health check timeout es al menos 10 segundos
- [ ] Backend Security Group permite tráfico en puerto 8000 desde ALB Security Group
- [ ] ALB Security Group permite tráfico saliente
- [ ] Aplicación escucha en `0.0.0.0:8000` (no `127.0.0.1:8000`)
- [ ] Health check protocol es HTTP (no HTTPS si no tienes certificado)
- [ ] Success codes incluyen 200

## Comandos Útiles

### Ver Health Check Details en AWS CLI

```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/anb-backend-tg/ID
```

### Ver Security Groups de una Instancia

```bash
aws ec2 describe-instances \
  --instance-ids i-09d1c6ae35f7cbf8e \
  --query 'Reservations[0].Instances[0].SecurityGroups'
```

### Verificar Reglas de Security Group

```bash
aws ec2 describe-security-groups \
  --group-ids sg-XXXXX \
  --query 'SecurityGroups[0].IpPermissions'
```

## Solución Más Común

**99% de los casos**: El Security Group del backend no permite tráfico desde el ALB.

**Solución**:
1. Backend Security Group → Inbound rules
2. Agregar regla: TCP 8000 desde ALB Security Group
3. Guardar
4. Esperar 2-3 minutos para que los health checks se actualicen

