# Entrega 5: Despliegue en PaaS (AWS ECS/Lambda)

## 📋 Resumen

Esta entrega consiste en migrar la aplicación de un modelo IaaS (EC2 con Auto Scaling) a un modelo PaaS utilizando servicios administrados de AWS, específicamente **Amazon ECS (Elastic Container Service)** para la capa web y workers.

## 🎯 Objetivos

- Migrar de IaaS (EC2) a PaaS (ECS/Lambda)
- Evaluar beneficios de servicios administrados vs infraestructura tradicional
- Implementar escalado automático con servicios PaaS
- Reducir complejidad operacional

## 📚 Documentación

### Guías Principales

1. **[Guía de Despliegue PaaS](AWS_PAAS_DEPLOYMENT_GUIDE.md)** - Guía paso a paso para desplegar en ECS
2. **[Arquitectura PaaS](ARQUITECTURA_PAAS.md)** - Arquitectura del sistema en modelo PaaS
3. **[Plan de Migración IaaS → PaaS](MIGRATION_PLAN_PAAS.md)** - Plan detallado de migración

### Configuraciones

- **[Task Definitions ECS](ecs-task-definitions/)** - Definiciones de tareas para ECS
- **[Scripts de Despliegue](scripts/)** - Scripts de automatización

## ✅ Actividades de la Entrega

### Actividad 1 (20%): Capa Web en ECS/Lambda
- [ ] Configurar ECS Cluster
- [ ] Crear Task Definition para API
- [ ] Desplegar servicio ECS con ALB
- [ ] Verificar que responde a solicitudes HTTP

### Actividad 2 (20%): Capa Worker en ECS/Lambda
- [ ] Crear Task Definition para Workers
- [ ] Desplegar servicio ECS para workers
- [ ] Configurar consumo de mensajes SQS
- [ ] Verificar procesamiento de videos

### Actividad 3 (10%): Base de Datos RDS
- [ ] Configurar instancia RDS (db.t3.micro para desarrollo)
- [ ] Ajustar conexiones en aplicación y workers
- [ ] Ejecutar migraciones de base de datos
- [ ] Verificar persistencia de datos

### Actividad 4 (10%): Sistema de Mensajería
- [ ] Configurar SQS/SNS/Kinesis
- [ ] Ajustar lógica de aplicación para encolar solicitudes
- [ ] Configurar workers para consumir mensajes
- [ ] Verificar flujo completo

### Actividad 5 (10%): Almacenamiento S3
- [ ] Configurar bucket S3
- [ ] Ajustar aplicación para usar S3
- [ ] Verificar almacenamiento de videos originales y procesados

### Actividad 6 (10%): Requerimientos Funcionales
- [ ] Autenticación funcionando
- [ ] Subida de videos funcionando
- [ ] Procesamiento asíncrono funcionando
- [ ] Consulta de videos funcionando
- [ ] Votación funcionando

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │    Balancer (ALB)   │
              └──────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │      ECS Cluster (Web Layer)        │
        │  ┌──────────┐  ┌──────────┐        │
        │  │  Task    │  │  Task    │        │
        │  │  (API)  │  │  (API)  │        │
        │  └──────────┘  └──────────┘        │
        └────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   SQS     │   │   S3    │
   │PostgreSQL│    │  Queue    │   │ Bucket  │
   └─────────┘    └──────────┘   └─────────┘
        │                │               
        │                │               
        ▼                ▼               
   ┌────────────────────────────────────┐
   │    ECS Cluster (Worker Layer)      │
   │  ┌──────────┐  ┌──────────┐       │
   │  │  Task    │  │  Task    │       │
   │  │ (Worker) │  │ (Worker) │       │
   │  └──────────┘  └──────────┘       │
   └────────────────────────────────────┘
```

## 🔧 Tecnologías Utilizadas

- **Amazon ECS (Fargate)**: Ejecución de contenedores sin gestión de servidores
- **Amazon RDS**: Base de datos PostgreSQL administrada
- **Amazon S3**: Almacenamiento de objetos
- **Amazon SQS**: Mensajería asíncrona
- **Application Load Balancer**: Distribución de carga
- **Amazon CloudWatch**: Monitoreo y logs
- **Docker**: Contenedores de la aplicación

## 📝 Notas Importantes

### Cuentas de Estudiante

Si estás usando una cuenta de estudiante (voclabs) con permisos restringidos:

1. **LabRole**: Asegúrate de usar `LabRole` como rol de tarea y ejecución en ECS
2. **Permisos**: Algunos recursos pueden requerir permisos del administrador
3. **Límites**: Lambda tiene máximo 10 instancias concurrentes en cuentas de estudiante

### Optimización de Costos

- **Detener recursos**: Detén instancias y servicios cuando no los uses
- **RDS**: Elimina la base de datos después de la entrega (recrear antes de sustentación)
- **Alarmas**: Configura alarmas de consumo y presupuestos
- **Desarrollo**: Usa `db.t3.micro` para desarrollo, solo escala para pruebas de capacidad

### Gestión de Credenciales

- **NO almacenar en código**: Usa variables de entorno
- **IAM Roles**: Preferir roles IAM sobre credenciales en texto plano
- **Secrets Manager**: Considerar AWS Secrets Manager para producción

## 🚀 Inicio Rápido

1. Lee la **[Guía de Despliegue PaaS](AWS_PAAS_DEPLOYMENT_GUIDE.md)**
2. Revisa la **[Arquitectura PaaS](ARQUITECTURA_PAAS.md)**
3. Sigue el **[Plan de Migración](MIGRATION_PLAN_PAAS.md)**

## 📞 Soporte

Para problemas o preguntas, consulta:
- Guía de despliegue para troubleshooting
- Documentación oficial de AWS ECS
- Logs de CloudWatch para diagnóstico

