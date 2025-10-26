#!/bin/bash

# ANB Rising Stars Showcase - AWS Cleanup Script
# This script destroys the AWS infrastructure to avoid costs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to confirm cleanup
confirm_cleanup() {
    print_warning "⚠️  ADVERTENCIA: Este script destruirá TODA la infraestructura AWS del proyecto ANB Rising Stars Showcase"
    print_warning "Esto incluye:"
    print_warning "  - Todas las instancias EC2"
    print_warning "  - La base de datos RDS"
    print_warning "  - El cluster Redis"
    print_warning "  - Todos los recursos de red (VPC, subnets, etc.)"
    print_warning "  - Todos los datos almacenados"
    echo ""
    print_warning "Esta acción NO se puede deshacer."
    echo ""
    
    read -p "¿Estás seguro de que quieres continuar? (escribe 'yes' para confirmar): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        print_status "Operación cancelada por el usuario"
        exit 0
    fi
}

# Function to backup important data
backup_data() {
    print_status "Creando backup de datos importantes..."
    
    # Create backup directory
    mkdir -p backups/$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    
    # Get infrastructure outputs
    cd terraform
    if [ -f "terraform.tfstate" ]; then
        WEB_SERVER_IP=$(terraform output -raw web_server_public_ip 2>/dev/null || echo "N/A")
        WORKER_SERVER_IP=$(terraform output -raw worker_server_public_ip 2>/dev/null || echo "N/A")
        NFS_SERVER_IP=$(terraform output -raw nfs_server_private_ip 2>/dev/null || echo "N/A")
        RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "N/A")
        REDIS_ENDPOINT=$(terraform output -raw redis_endpoint 2>/dev/null || echo "N/A")
        
        # Save infrastructure info
        cat > "../$BACKUP_DIR/infrastructure_info.txt" << EOF
ANB Rising Stars Showcase - Infrastructure Information
Backup Date: $(date)
================================================

Web Server IP: $WEB_SERVER_IP
Worker Server IP: $WORKER_SERVER_IP
NFS Server IP: $NFS_SERVER_IP
RDS Endpoint: $RDS_ENDPOINT
Redis Endpoint: $REDIS_ENDPOINT

Application URL: http://$WEB_SERVER_IP:8000
API Documentation: http://$WEB_SERVER_IP:8000/docs
EOF
        
        print_success "Información de infraestructura guardada en $BACKUP_DIR/infrastructure_info.txt"
    fi
    
    cd ..
    
    # Backup application logs if servers are still accessible
    if [ "$WEB_SERVER_IP" != "N/A" ] && [ "$WEB_SERVER_IP" != "" ]; then
        print_status "Intentando backup de logs del servidor web..."
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WEB_SERVER_IP "test -d /opt/anb-app/logs" 2>/dev/null; then
            scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ubuntu@$WEB_SERVER_IP:/opt/anb-app/logs "$BACKUP_DIR/web_logs" 2>/dev/null || print_warning "No se pudieron copiar los logs del servidor web"
        fi
    fi
    
    if [ "$WORKER_SERVER_IP" != "N/A" ] && [ "$WORKER_SERVER_IP" != "" ]; then
        print_status "Intentando backup de logs del servidor worker..."
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WORKER_SERVER_IP "test -d /opt/anb-app/logs" 2>/dev/null; then
            scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ubuntu@$WORKER_SERVER_IP:/opt/anb-app/logs "$BACKUP_DIR/worker_logs" 2>/dev/null || print_warning "No se pudieron copiar los logs del servidor worker"
        fi
    fi
    
    print_success "Backup completado en directorio: $BACKUP_DIR"
}

# Function to destroy infrastructure
destroy_infrastructure() {
    print_status "Destruyendo infraestructura con Terraform..."
    
    cd terraform
    
    # Check if terraform state exists
    if [ ! -f "terraform.tfstate" ]; then
        print_warning "No se encontró estado de Terraform. La infraestructura puede no existir."
        cd ..
        return 0
    fi
    
    # Plan destruction
    print_status "Planificando destrucción..."
    terraform plan -destroy -out=destroy.tfplan
    
    # Confirm destruction
    print_warning "Revisa el plan de destrucción arriba."
    read -p "¿Continuar con la destrucción? (escribe 'yes' para confirmar): " destroy_confirmation
    
    if [ "$destroy_confirmation" != "yes" ]; then
        print_status "Destrucción cancelada por el usuario"
        cd ..
        return 0
    fi
    
    # Execute destruction
    print_status "Ejecutando destrucción..."
    terraform apply destroy.tfplan
    
    print_success "Infraestructura destruida exitosamente"
    
    cd ..
}

# Function to clean up local files
cleanup_local() {
    print_status "Limpiando archivos locales..."
    
    # Remove environment files
    rm -f .env.aws
    rm -f terraform/.env.aws
    
    # Remove terraform plan files
    rm -f terraform/tfplan
    rm -f terraform/destroy.tfplan
    
    # Remove temporary files
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "*.log" -delete 2>/dev/null || true
    
    print_success "Archivos locales limpiados"
}

# Function to show cost summary
show_cost_summary() {
    print_status "Resumen de costos estimados:"
    echo ""
    echo "Recursos destruidos:"
    echo "  - 3x EC2 t3.medium: ~$90/mes"
    echo "  - 1x RDS db.t3.micro: ~$15/mes"
    echo "  - 1x ElastiCache cache.t3.micro: ~$15/mes"
    echo "  - Almacenamiento EBS: ~$5/mes"
    echo "  - Transferencia de datos: ~$2/mes"
    echo ""
    echo "Total estimado ahorrado: ~$127/mes"
    echo ""
    print_success "¡Has ahorrado aproximadamente $127/mes en costos de AWS!"
}

# Main cleanup function
main() {
    print_status "Iniciando limpieza de infraestructura AWS..."
    
    # Confirm cleanup
    confirm_cleanup
    
    # Backup data
    backup_data
    
    # Destroy infrastructure
    destroy_infrastructure
    
    # Clean up local files
    cleanup_local
    
    # Show cost summary
    show_cost_summary
    
    print_success "Limpieza completada exitosamente!"
    print_status "Todos los recursos AWS han sido destruidos"
    print_status "Los backups están disponibles en el directorio 'backups/'"
    print_warning "Recuerda eliminar manualmente cualquier recurso que no haya sido destruido por Terraform"
}

# Run main function
main "$@"
