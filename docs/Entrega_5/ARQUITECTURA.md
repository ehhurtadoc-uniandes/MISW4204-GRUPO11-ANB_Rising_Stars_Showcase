# Arquitectura de la Aplicación - Entrega 5: Despliegue en PaaS

## 📋 Resumen Ejecutivo

Este documento describe la arquitectura del sistema ANB Rising Stars Showcase en su versión de la Entrega 5, enfocada en el despliegue sobre servicios de Plataforma como Servicio (PaaS) en AWS. La arquitectura evoluciona de un modelo IaaS (EC2) a un modelo PaaS utilizando **AWS Elastic Container Service (ECS) con AWS Fargate** para la ejecución de contenedores sin gestión de servidores, manteniendo la integración con servicios gestionados como RDS, SQS y S3.

---

## 🏗️ Modelo de Despliegue PaaS

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │    Balancer (ALB)    │
              └──────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │ ECS     │     │ ECS     │     │ ECS     │
   │ Fargate │     │ Fargate │     │ Fargate │
   │ (Web)   │     │ (Web)   │     │ (Web)   │
   │ AZ-1a   │     │ AZ-1b   │     │ AZ-1c   │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │                │
        └───────────────┼────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐   ┌─────────┐
   │   RDS   │    │   SQS     │   │   S3    │
   │PostgreSQL│    │  Queue    │   │ Bucket  │
   │ (Multi-AZ)│    │           │   │         │
   └─────────┘    └──────────┘   └─────────┘
        │               │               
        │               │               
        ▼               ▼               
   ┌─────────┐    ┌──────────┐
   │ ECS     │    │ ECS      │
   │ Fargate │    │ Fargate  │
   │ (Worker)│    │ (Worker) │
   │ AZ-1a   │    │ AZ-1b    │
   └─────────┘    └──────────┘
```

### Componentes PaaS Seleccionados

1.  **Capa Web (Compute): AWS ECS + Fargate**
    *   **Justificación:** Elimina la necesidad de gestionar instancias EC2, parches del SO y configuración de servidores. Fargate escala automáticamente y cobra por uso de vCPU/RAM.
    *   **Configuración:** Servicio ECS balanceado por carga, ejecutando la imagen Docker de la API.

2.  **Capa Worker (Compute): AWS ECS + Fargate**
    *   **Justificación:** Permite procesamiento de tareas pesadas (video) en un entorno aislado y efímero sin gestionar servidores.
    *   **Configuración:** Servicio ECS (o Standalone Tasks) que escala basado en la profundidad de la cola SQS.

3.  **Base de Datos: Amazon RDS (PostgreSQL)**
    *   **Justificación:** Servicio gestionado que maneja backups, parches y alta disponibilidad (Multi-AZ).

4.  **Mensajería: Amazon SQS**
    *   **Justificación:** Desacopla la capa web de los workers, permitiendo escalabilidad asíncrona y manejo de picos de carga.

5.  **Almacenamiento: Amazon S3**
    *   **Justificación:** Almacenamiento ilimitado, duradero y altamente disponible para videos.

---

## 🔄 Cambios respecto a Entrega 4 (IaaS vs PaaS)

| Componente | Entrega 4 (IaaS) | Entrega 5 (PaaS) | Beneficio PaaS |
| :--- | :--- | :--- | :--- |
| **Cómputo Web** | Instancias EC2 gestionadas manualmente o por ASG | **AWS Fargate (Serverless Containers)** | Sin gestión de SO, parches ni aprovisionamiento de instancias. |
| **Cómputo Worker** | Instancias EC2 gestionadas manualmente o por ASG | **AWS Fargate (Serverless Containers)** | Escalado más rápido, pago por uso exacto, menor carga operativa. |
| **Orquestación** | Scripts de User Data / Docker Compose en EC2 | **AWS ECS (Elastic Container Service)** | Gestión nativa de contenedores, deployments, rollbacks y salud. |
| **Logs** | Archivos locales / CloudWatch Agent | **AWS CloudWatch Logs (Nativo)** | Integración directa `awslogs` driver, centralización automática. |

---

## 🧩 Especificaciones de Configuración

### Definición de Tareas (Task Definitions)

#### Web Task (`anb-web-task`)
*   **Compatibilidad:** Fargate
*   **CPU:** 512 (.5 vCPU)
*   **Memoria:** 1024 (1 GB)
*   **Imagen:** `[Account-ID].dkr.ecr.[Region].amazonaws.com/anb-backend:latest`
*   **Puerto:** 8000
*   **Variables de Entorno:** `DATABASE_URL`, `SQS_QUEUE_URL`, `S3_BUCKET_NAME`, etc.
*   **Log Driver:** `awslogs`

#### Worker Task (`anb-worker-task`)
*   **Compatibilidad:** Fargate
*   **CPU:** 1024 (1 vCPU) - *Mayor potencia para procesamiento de video*
*   **Memoria:** 2048 (2 GB)
*   **Imagen:** `[Account-ID].dkr.ecr.[Region].amazonaws.com/anb-backend:latest`
*   **Comando:** `python -m app.workers.sqs_worker`
*   **Variables de Entorno:** Mismas que Web + credenciales específicas si aplica.

### Escalado (Auto Scaling)

*   **Web:** Application Auto Scaling basado en `ECSServiceAverageCPUUtilization` (Target: 70%).
*   **Worker:** Application Auto Scaling basado en métrica personalizada de CloudWatch (Profundidad de cola SQS).

---

## 🔐 Seguridad y Redes

*   **VPC:** Se utiliza la misma VPC de la entrega anterior.
*   **Subnets:** Fargate se despliega en **Subnets Privadas** para mayor seguridad (requiere NAT Gateway para salir a internet a buscar imágenes ECR o conectar con AWS APIs).
*   **Security Groups:**
    *   `anb-fargate-web-sg`: Permite entrada puerto 8000 desde ALB.
    *   `anb-fargate-worker-sg`: Sin puertos de entrada (solo salida a internet/AWS).
*   **IAM Roles:**
    *   `TaskExecutionRole`: Permisos para que ECS baje imágenes de ECR y escriba logs en CloudWatch.
    *   `TaskRole`: Permisos para que la aplicación acceda a S3 y SQS.

---

## 📝 Conclusiones del Modelo PaaS

La adopción de PaaS mediante AWS Fargate simplifica drásticamente la operación del sistema ANB Rising Stars. Se elimina la carga cognitiva de mantener el sistema operativo de las instancias EC2, se mejora la seguridad al reducir la superficie de ataque (contenedores efímeros), y se optimizan los costos al pagar estrictamente por los recursos de CPU/Memoria consumidos durante la ejecución de las tareas.
