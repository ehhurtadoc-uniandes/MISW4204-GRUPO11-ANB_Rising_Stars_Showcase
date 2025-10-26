#!/bin/bash

# ANB Application Configuration Script for AWS
# This script configures the application for AWS deployment

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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to update configuration files
update_config() {
    local server_type=$1
    local server_ip=$2
    
    print_status "Configuring $server_type at $server_ip..."
    
    # Create environment file
    cat > .env.aws << EOF
# Database Configuration
DB_PASSWORD=${DB_PASSWORD}
RDS_ENDPOINT=${RDS_ENDPOINT}
POSTGRES_HOST=${RDS_ENDPOINT}
POSTGRES_PORT=5432
POSTGRES_USER=anb_user
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=anb_db
DATABASE_URL=postgresql://anb_user:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/anb_db

# Redis Configuration
REDIS_ENDPOINT=${REDIS_ENDPOINT}
REDIS_URL=redis://${REDIS_ENDPOINT}:6379/0
CELERY_BROKER_URL=redis://${REDIS_ENDPOINT}:6379/0
CELERY_RESULT_BACKEND=redis://${REDIS_ENDPOINT}:6379/0

# NFS Configuration
NFS_SERVER_IP=${NFS_SERVER_IP}

# Application Configuration
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}

# File Storage
UPLOAD_DIR=/mnt/nfs/uploads
PROCESSED_DIR=/mnt/nfs/processed_videos
ASSETS_DIR=/mnt/nfs/assets

# AWS Configuration
AWS_REGION=${AWS_REGION}
EOF

    # Copy application files
    print_status "Copying application files to $server_type..."
    
    if [ "$server_type" = "web" ]; then
        # Copy web server files
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../alembic ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../alembic.ini ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.aws.yml ubuntu@$server_ip:/opt/anb-app/docker-compose.yml
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$server_ip:/opt/anb-app/.env
        
        # Copy nginx configuration
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../nginx ubuntu@$server_ip:/opt/anb-app/
        
    elif [ "$server_type" = "worker" ]; then
        # Copy worker server files
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$server_ip:/opt/anb-app/
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.worker.aws.yml ubuntu@$server_ip:/opt/anb-app/docker-compose.yml
        scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$server_ip:/opt/anb-app/.env
    fi
    
    print_success "$server_type configured successfully"
}

# Function to start services
start_services() {
    local server_type=$1
    local server_ip=$2
    
    print_status "Starting services on $server_type..."
    
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$server_ip "
        cd /opt/anb-app
        
        # Build and start containers
        docker-compose build
        docker-compose up -d
        
        # Wait for services to be ready
        sleep 30
        
        # Check if services are running
        docker-compose ps
    "
    
    print_success "Services started on $server_type"
}

# Function to run database migrations
run_migrations() {
    local server_ip=$1
    
    print_status "Running database migrations..."
    
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$server_ip "
        cd /opt/anb-app
        
        # Wait for database to be ready
        sleep 10
        
        # Run migrations
        docker-compose exec -T api alembic upgrade head
    "
    
    print_success "Database migrations completed"
}

# Function to test deployment
test_deployment() {
    local web_server_ip=$1
    
    print_status "Testing deployment..."
    
    # Wait for services to be ready
    sleep 30
    
    # Test health endpoint
    if curl -f http://$web_server_ip:8000/health &> /dev/null; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        return 1
    fi
    
    # Test root endpoint
    if curl -f http://$web_server_ip:8000/ &> /dev/null; then
        print_success "Root endpoint test passed"
    else
        print_error "Root endpoint test failed"
        return 1
    fi
    
    # Test API documentation
    if curl -f http://$web_server_ip:8000/docs &> /dev/null; then
        print_success "API documentation is accessible"
    else
        print_error "API documentation is not accessible"
        return 1
    fi
    
    print_success "All deployment tests passed"
}

# Main configuration function
main() {
    print_status "Starting application configuration for AWS..."
    
    # Check if required variables are set
    if [ -z "$WEB_SERVER_IP" ] || [ -z "$WORKER_SERVER_IP" ] || [ -z "$NFS_SERVER_IP" ] || [ -z "$RDS_ENDPOINT" ] || [ -z "$REDIS_ENDPOINT" ] || [ -z "$DB_PASSWORD" ] || [ -z "$SECRET_KEY" ]; then
        print_error "Required environment variables are not set"
        print_error "Please set: WEB_SERVER_IP, WORKER_SERVER_IP, NFS_SERVER_IP, RDS_ENDPOINT, REDIS_ENDPOINT, DB_PASSWORD, SECRET_KEY"
        exit 1
    fi
    
    # Configure web server
    update_config "web" "$WEB_SERVER_IP"
    
    # Configure worker server
    update_config "worker" "$WORKER_SERVER_IP"
    
    # Start services
    start_services "web" "$WEB_SERVER_IP"
    start_services "worker" "$WORKER_SERVER_IP"
    
    # Run migrations
    run_migrations "$WEB_SERVER_IP"
    
    # Test deployment
    test_deployment "$WEB_SERVER_IP"
    
    print_success "Application configuration completed successfully!"
    print_status "Application URL: http://$WEB_SERVER_IP:8000"
    print_status "API Documentation: http://$WEB_SERVER_IP:8000/docs"
}

# Run main function
main "$@"
