# Troubleshooting: Bad Gateway (502) Error

## Diagnóstico Rápido

### 1. Verificar Target Group Health

1. Ve a **EC2 Dashboard** → **Target Groups** → Selecciona `anb-backend-tg`
2. Click en **Health checks** tab
3. Verifica el estado de las instancias:
   - ✅ **Healthy**: Instancia está funcionando
   - ❌ **Unhealthy**: Instancia no está respondiendo
   - ⏳ **Initial**: Health check aún no ha terminado

**Si todas las instancias están "Unhealthy":**

### 2. Verificar Puerto del Target Group

**⚠️ PROBLEMA COMÚN**: Target Group configurado en puerto 80, pero la app está en puerto 8000

1. En el Target Group → **Attributes** tab → **Edit**
2. Verifica que el **Port** sea **8000** (no 80)
3. Guarda los cambios
4. Espera 2-3 minutos para que los health checks se actualicen

### 3. Verificar Health Check Path

1. En el Target Group → **Health checks** tab → **Edit**
2. Verifica que el **Health check path** sea `/health`
3. **Healthy threshold**: 2
4. **Unhealthy threshold**: 3
5. **Timeout**: 5 segundos
6. **Interval**: 30 segundos

### 4. Verificar Instancias del Backend

**SSH a una instancia del backend:**

```bash
# Verificar que el contenedor está corriendo
docker ps | grep anb-api

# Si no está corriendo, verificar el servicio
systemctl status anb-api

# Ver logs del contenedor
docker logs anb-api

# Ver logs del servicio
journalctl -u anb-api -n 50
```

**Probar el endpoint directamente en la instancia:**

```bash
# Desde dentro de la instancia EC2
curl http://localhost:8000/health
curl http://localhost:8000/docs
curl http://localhost:8000/openapi.json
```

Si estos comandos funcionan localmente pero el ALB no puede conectarse, el problema es de configuración del Target Group o Security Groups.

### 5. Verificar Security Groups

**Backend Security Group (`anb-backend-sg`):**

Debe tener una regla que permita tráfico desde el ALB:

- **Type**: HTTP
- **Protocol**: TCP
- **Port**: 8000
- **Source**: Security Group `anb-alb-sg` (o el Security Group del ALB)

**ALB Security Group (`anb-alb-sg`):**

Debe permitir tráfico entrante:

- **Type**: HTTP
- **Protocol**: TCP
- **Port**: 80
- **Source**: 0.0.0.0/0 (o tu IP específica)

### 6. Verificar que la App está Escuchando en 0.0.0.0

La aplicación debe estar escuchando en `0.0.0.0:8000`, no en `127.0.0.1:8000`.

Verifica en `app/main.py`:
```python
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",  # ✅ Correcto
    port=8000,
    reload=settings.debug
)
```

### 7. Verificar Auto Scaling Group

1. **EC2 Dashboard** → **Auto Scaling Groups** → `anb-backend-asg`
2. Verifica que haya instancias corriendo:
   - **Desired capacity**: Debe ser > 0
   - **Instances**: Debe mostrar instancias activas
3. Si no hay instancias, el ASG puede estar fallando al lanzarlas

### 8. Verificar Logs de la Aplicación

```bash
# En la instancia EC2 del backend
docker logs anb-api -f

# Buscar errores como:
# - "Address already in use" (puerto ocupado)
# - "Connection refused" (no puede conectar a DB)
# - "NoSuchBucket" (S3 bucket no existe)
# - Cualquier traceback de Python
```

## Soluciones Comunes

### Solución 1: Target Group en Puerto Incorrecto

**Síntoma**: Todas las instancias están "Unhealthy" con "Request timed out"

**Solución**:
1. Target Group → **Attributes** → **Edit**
2. Cambiar **Port** de 80 a **8000**
3. Guardar y esperar 2-3 minutos

### Solución 2: Security Group Bloqueando Tráfico

**Síntoma**: Instancias están "Unhealthy", pero `curl localhost:8000/health` funciona

**Solución**:
1. Backend Security Group → **Inbound rules** → **Edit**
2. Agregar regla:
   - **Type**: Custom TCP
   - **Port**: 8000
   - **Source**: Security Group del ALB (`anb-alb-sg`)
3. Guardar

### Solución 3: Aplicación No Está Corriendo

**Síntoma**: `docker ps` no muestra `anb-api`

**Solución**:
```bash
# Reiniciar el servicio
sudo systemctl restart anb-api

# O reiniciar el contenedor directamente
sudo docker restart anb-api

# Verificar logs para ver por qué falló
docker logs anb-api
```

### Solución 4: Health Check Path Incorrecto

**Síntoma**: Health checks fallan pero la app funciona

**Solución**:
1. Target Group → **Health checks** → **Edit**
2. Cambiar **Health check path** a `/health`
3. Guardar

### Solución 5: Aplicación Está Crashing

**Síntoma**: Logs muestran errores constantes

**Causas comunes**:
- Base de datos no accesible (RDS endpoint incorrecto)
- S3 bucket no existe (ver error anterior)
- Credenciales AWS incorrectas
- Variables de entorno faltantes

**Solución**: Revisar logs y corregir el problema específico

## Comandos Útiles

### Verificar Estado del Target Group
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/anb-backend-tg/ID
```

### Verificar Instancias en el ASG
```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names anb-backend-asg
```

### Probar Endpoint Directamente
```bash
# Desde tu máquina local
curl http://ALB_DNS_NAME/health

# Desde dentro de una instancia EC2
curl http://PRIVATE_IP_INSTANCE:8000/health
```

## Checklist de Verificación

- [ ] Target Group está en puerto **8000** (no 80)
- [ ] Health check path es `/health`
- [ ] Backend Security Group permite tráfico en puerto 8000 desde ALB Security Group
- [ ] Instancias del backend están corriendo (`docker ps`)
- [ ] Aplicación responde localmente (`curl localhost:8000/health`)
- [ ] Aplicación está escuchando en `0.0.0.0:8000`
- [ ] No hay errores en los logs del contenedor
- [ ] Auto Scaling Group tiene instancias activas
- [ ] Base de datos (RDS) es accesible
- [ ] S3 bucket existe y es accesible

