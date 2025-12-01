#!/bin/bash
# Script para construir y subir imagen Docker a ECR

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-anb-rising-stars-api}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo -e "${GREEN}=== Build and Push Docker Image to ECR ===${NC}"

# Verificar que AWS CLI está instalado
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está instalado${NC}"
    exit 1
fi

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker no está instalado${NC}"
    exit 1
fi

# Obtener Account ID
echo -e "${YELLOW}Obteniendo Account ID de AWS...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}Error: No se pudo obtener Account ID. Verifica tus credenciales de AWS.${NC}"
    exit 1
fi

echo -e "${GREEN}Account ID: $ACCOUNT_ID${NC}"

# ECR Repository URI
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo -e "${YELLOW}ECR URI: ${ECR_URI}${NC}"

# Verificar si el repositorio existe, si no, crearlo
echo -e "${YELLOW}Verificando si el repositorio ECR existe...${NC}"
if ! aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" &> /dev/null; then
    echo -e "${YELLOW}Repositorio no existe. Creando...${NC}"
    aws ecr create-repository \
        --repository-name "${ECR_REPOSITORY}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --image-tag-mutability MUTABLE
    echo -e "${GREEN}Repositorio creado exitosamente${NC}"
else
    echo -e "${GREEN}Repositorio ya existe${NC}"
fi

# Autenticar Docker con ECR
echo -e "${YELLOW}Autenticando Docker con ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_URI}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Falló la autenticación con ECR${NC}"
    exit 1
fi

echo -e "${GREEN}Autenticación exitosa${NC}"

# Construir imagen
echo -e "${YELLOW}Construyendo imagen Docker...${NC}"
docker build -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Falló la construcción de la imagen${NC}"
    exit 1
fi

echo -e "${GREEN}Imagen construida exitosamente${NC}"

# Tag para ECR
echo -e "${YELLOW}Etiquetando imagen para ECR...${NC}"
docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"

# Push a ECR
echo -e "${YELLOW}Subiendo imagen a ECR...${NC}"
docker push "${ECR_URI}:${IMAGE_TAG}"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Falló el push a ECR${NC}"
    exit 1
fi

echo -e "${GREEN}=== Imagen subida exitosamente ===${NC}"
echo -e "${GREEN}URI de la imagen: ${ECR_URI}:${IMAGE_TAG}${NC}"
echo ""
echo -e "${YELLOW}Para usar esta imagen en ECS Task Definition, usa:${NC}"
echo -e "${GREEN}${ECR_URI}:${IMAGE_TAG}${NC}"

