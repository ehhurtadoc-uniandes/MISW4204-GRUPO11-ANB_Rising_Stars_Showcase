#!/bin/bash
# Script para actualizar un servicio ECS con una nueva revisión de Task Definition

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
CLUSTER_NAME="${CLUSTER_NAME:-anb-rising-stars-cluster}"
SERVICE_NAME="${SERVICE_NAME:-anb-api-service}"
TASK_DEFINITION_FAMILY="${TASK_DEFINITION_FAMILY:-anb-api-task}"

echo -e "${GREEN}=== Update ECS Service ===${NC}"

# Verificar que AWS CLI está instalado
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está instalado${NC}"
    exit 1
fi

# Verificar que el cluster existe
echo -e "${YELLOW}Verificando que el cluster existe...${NC}"
if ! aws ecs describe-clusters --clusters "${CLUSTER_NAME}" --query 'clusters[0].status' --output text | grep -q "ACTIVE"; then
    echo -e "${RED}Error: El cluster '${CLUSTER_NAME}' no existe o no está activo${NC}"
    exit 1
fi

echo -e "${GREEN}Cluster encontrado${NC}"

# Obtener la última revisión de la Task Definition
echo -e "${YELLOW}Obteniendo última revisión de Task Definition...${NC}"
TASK_DEFINITION_ARN=$(aws ecs describe-task-definition \
    --task-definition "${TASK_DEFINITION_FAMILY}" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

if [ -z "$TASK_DEFINITION_ARN" ]; then
    echo -e "${RED}Error: No se pudo obtener la Task Definition${NC}"
    exit 1
fi

echo -e "${GREEN}Task Definition: ${TASK_DEFINITION_ARN}${NC}"

# Actualizar el servicio
echo -e "${YELLOW}Actualizando servicio ECS...${NC}"
aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --task-definition "${TASK_DEFINITION_FAMILY}" \
    --force-new-deployment \
    > /dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Falló la actualización del servicio${NC}"
    exit 1
fi

echo -e "${GREEN}Servicio actualizado exitosamente${NC}"
echo -e "${YELLOW}Esperando a que el despliegue se complete...${NC}"

# Esperar a que el servicio se estabilice
aws ecs wait services-stable \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: El servicio no se estabilizó${NC}"
    exit 1
fi

echo -e "${GREEN}=== Despliegue completado exitosamente ===${NC}"

