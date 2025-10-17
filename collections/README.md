# Colecciones de Postman - ANB Rising Stars Showcase

## Descripción

Este directorio contiene las colecciones de Postman para probar y documentar la API de la plataforma ANB Rising Stars Showcase.

## Archivos Incluidos

### 1. anb-api.postman_collection.json
Colección principal que incluye todos los endpoints de la API con:
- Pruebas automatizadas
- Validaciones de respuesta
- Documentación integrada
- Manejo de variables de entorno

### 2. postman_environment.json
Archivo de entorno que contiene las variables necesarias para la ejecución de las pruebas:
- `base_url`: URL base para desarrollo local
- `deploy_url`: URL base para entorno de despliegue
- `access_token`: Token JWT para autenticación
- Variables auxiliares para IDs de videos

## Uso de las Colecciones

### Importar en Postman
1. Abrir Postman
2. Hacer clic en "Import"
3. Seleccionar ambos archivos JSON
4. La colección aparecerá en el workspace

### Configurar Entorno
1. Seleccionar el entorno "ANB API Environment"
2. Actualizar las variables según el entorno de prueba:
   - Para desarrollo local: usar `base_url`
   - Para despliegue: activar y configurar `deploy_url`

### Ejecutar Pruebas

#### Flujo Recomendado
1. **Health Check** - Verificar que la API esté funcionando
2. **User Signup** - Crear un usuario de prueba
3. **User Login** - Obtener token de autenticación
4. **Get My Videos** - Verificar lista vacía inicialmente
5. **Upload Video** - Subir un video de prueba
6. **Get Video Detail** - Verificar detalles del video
7. **Get Public Videos** - Ver videos públicos
8. **Vote for Video** - Votar por un video
9. **Get Rankings** - Ver ranking actualizado

#### Ejecución Automatizada
Las pruebas incluyen validaciones automáticas que verifican:
- Códigos de estado HTTP correctos
- Estructura de respuestas JSON
- Presencia de campos requeridos
- Lógica de negocio (ej: no votar dos veces)

## Ejecución con Newman CLI

### Instalación de Newman
```bash
npm install -g newman
```

### Ejecutar Colección Completa
```bash
newman run collections/anb-api.postman_collection.json \
  -e collections/postman_environment.json \
  --reporters cli,json \
  --reporter-json-export results.json
```

### Ejecutar con Variables de Entorno Personalizadas
```bash
newman run collections/anb-api.postman_collection.json \
  -e collections/postman_environment.json \
  --env-var "base_url=http://production-server:8000" \
  --reporters cli,htmlextra \
  --reporter-htmlextra-export report.html
```

### Integración en CI/CD
```yaml
# Ejemplo para GitHub Actions
- name: Run API Tests
  run: |
    newman run collections/anb-api.postman_collection.json \
      -e collections/postman_environment.json \
      --env-var "base_url=${{ env.API_URL }}" \
      --reporters cli,junit \
      --reporter-junit-export newman-results.xml
```

## Estructura de la Colección

### 1. Authentication
- **User Signup**: Registro de nuevos usuarios
- **User Login**: Autenticación y obtención de token
- **Invalid Login**: Prueba de credenciales incorrectas

### 2. Videos
- **Get My Videos**: Lista de videos del usuario autenticado
- **Upload Video**: Subida de archivos de video
- **Get Video Detail**: Detalles de un video específico
- **Delete Video**: Eliminación de videos propios

### 3. Public
- **Get Public Videos**: Lista de videos públicos con paginación
- **Vote for Video**: Emisión de votos por videos
- **Get Rankings**: Ranking general de jugadores
- **Get Rankings by City**: Ranking filtrado por ciudad

### 4. Health Check
- **Health Check**: Verificación del estado de la API

## Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `base_url` | URL base de la API | `http://localhost:8000` |
| `deploy_url` | URL de despliegue | `http://prod-server:8000` |
| `access_token` | Token JWT de autenticación | `eyJ0eXAiOiJKV1Q...` |
| `video_id` | ID de video para pruebas | `123e4567-e89b-12d3` |
| `public_video_id` | ID de video público | `456e7890-e89b-12d3` |

## Validaciones Incluidas

### Códigos de Estado
- 200: Operaciones exitosas
- 201: Creación exitosa
- 400: Errores de validación
- 401: No autenticado
- 403: No autorizado
- 404: Recurso no encontrado

### Estructura de Respuestas
- Presencia de campos obligatorios
- Tipos de datos correctos
- Formato de timestamps
- Estructura de arrays y objetos

### Lógica de Negocio
- Token JWT válido después del login
- Videos propios solo visibles al propietario
- Un voto por usuario por video
- Rankings ordenados por votos

## Ejemplos de Uso

### 1. Prueba de Autenticación Completa
```javascript
// En Postman, estos scripts se ejecutan automáticamente
pm.test("Login successful", function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.environment.set("access_token", jsonData.access_token);
});
```

### 2. Validación de Upload de Video
```javascript
pm.test("Video upload initiated", function () {
    pm.response.to.have.status(201);
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('task_id');
    pm.expect(jsonData.message).to.include('procesamiento');
});
```

### 3. Verificación de Ranking
```javascript
pm.test("Rankings are ordered by votes", function () {
    var rankings = pm.response.json();
    for (let i = 0; i < rankings.length - 1; i++) {
        pm.expect(rankings[i].votes).to.be.at.least(rankings[i + 1].votes);
    }
});
```

## Troubleshooting

### Problemas Comunes

#### Error de Conexión
- Verificar que la API esté ejecutándose
- Confirmar la URL en las variables de entorno
- Revisar configuración de puertos

#### Token Expirado
- Ejecutar nuevamente el endpoint de login
- Verificar configuración de expiración de tokens
- Usar tokens con TTL apropiado para pruebas

#### Archivos de Video
- Para pruebas de upload, usar archivos MP4 pequeños (<10MB)
- Verificar formato de archivo soportado
- Confirmar permisos de escritura en directorios

### Logs y Debugging
- Usar la consola de Postman para ver logs detallados
- Revisar respuestas en la pestaña "Response"
- Verificar variables de entorno en tiempo real

## Mantenimiento

### Actualización de Colecciones
- Exportar colecciones actualizadas desde Postman
- Mantener sincronización con cambios en la API
- Documentar nuevos endpoints en la colección

### Versionado
- Usar tags de Git para versionar colecciones
- Mantener compatibilidad con versiones anteriores
- Documentar breaking changes en release notes