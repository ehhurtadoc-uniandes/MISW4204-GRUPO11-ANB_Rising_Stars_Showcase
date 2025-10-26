#!/bin/bash

# ANB Rising Stars Showcase - AWS Deployment Script
# This script deploys the application to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."
    
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    if ! command -v ssh &> /dev/null; then
        print_error "SSH is not installed. Please install SSH first."
        exit 1
    fi
    
    print_success "All requirements are met"
}

# Check AWS credentials
check_aws_credentials() {
    print_status "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS credentials are configured"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    WEB_SERVER_IP=$(terraform output -raw web_server_public_ip)
    WORKER_SERVER_IP=$(terraform output -raw worker_server_public_ip)
    NFS_SERVER_IP=$(terraform output -raw nfs_server_private_ip)
    RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
    REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
    
    print_success "Infrastructure deployed successfully"
    print_status "Web Server IP: $WEB_SERVER_IP"
    print_status "Worker Server IP: $WORKER_SERVER_IP"
    print_status "NFS Server IP: $NFS_SERVER_IP"
    print_status "RDS Endpoint: $RDS_ENDPOINT"
    print_status "Redis Endpoint: $REDIS_ENDPOINT"
    
    cd ..
}

# Wait for instances to be ready
wait_for_instances() {
    print_status "Waiting for instances to be ready..."
    
    # Wait for web server
    print_status "Waiting for web server to be ready..."
    until ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WEB_SERVER_IP "echo 'Web server is ready'" &> /dev/null; do
        print_status "Web server not ready yet, waiting..."
        sleep 10
    done
    
    # Wait for worker server
    print_status "Waiting for worker server to be ready..."
    until ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WORKER_SERVER_IP "echo 'Worker server is ready'" &> /dev/null; do
        print_status "Worker server not ready yet, waiting..."
        sleep 10
    done
    
    # Wait for NFS server
    print_status "Waiting for NFS server to be ready..."
    until ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$NFS_SERVER_IP "echo 'NFS server is ready'" &> /dev/null; do
        print_status "NFS server not ready yet, waiting..."
        sleep 10
    done
    
    print_success "All instances are ready"
}

# Configure NFS mounts
configure_nfs() {
    print_status "Configuring NFS mounts..."
    
    # Configure NFS on web server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WEB_SERVER_IP "
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/uploads /mnt/nfs/uploads
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/assets /mnt/nfs/assets
        
        # Add to fstab for persistence
        echo '$NFS_SERVER_IP:/mnt/nfs/uploads /mnt/nfs/uploads nfs defaults 0 0' | sudo tee -a /etc/fstab
        echo '$NFS_SERVER_IP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos nfs defaults 0 0' | sudo tee -a /etc/fstab
        echo '$NFS_SERVER_IP:/mnt/nfs/assets /mnt/nfs/assets nfs defaults 0 0' | sudo tee -a /etc/fstab
    "
    
    # Configure NFS on worker server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WORKER_SERVER_IP "
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/uploads /mnt/nfs/uploads
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos
        sudo mount -t nfs $NFS_SERVER_IP:/mnt/nfs/assets /mnt/nfs/assets
        
        # Add to fstab for persistence
        echo '$NFS_SERVER_IP:/mnt/nfs/uploads /mnt/nfs/uploads nfs defaults 0 0' | sudo tee -a /etc/fstab
        echo '$NFS_SERVER_IP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos nfs defaults 0 0' | sudo tee -a /etc/fstab
        echo '$NFS_SERVER_IP:/mnt/nfs/assets /mnt/nfs/assets nfs defaults 0 0' | sudo tee -a /etc/fstab
    "
    
    print_success "NFS mounts configured"
}

# Deploy application
deploy_application() {
    print_status "Deploying application..."
    
    # Create environment file
    cat > .env.aws << EOF
DB_PASSWORD=$DB_PASSWORD
RDS_ENDPOINT=$RDS_ENDPOINT
REDIS_ENDPOINT=$REDIS_ENDPOINT
NFS_SERVER_IP=$NFS_SERVER_IP
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=$SECRET_KEY
EOF
    
    # Deploy to web server
    print_status "Deploying to web server..."
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$WEB_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../alembic ubuntu@$WEB_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$WEB_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$WEB_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../alembic.ini ubuntu@$WEB_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.aws.yml ubuntu@$WEB_SERVER_IP:/opt/anb-app/docker-compose.yml
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$WEB_SERVER_IP:/opt/anb-app/.env
    
    # Deploy to worker server
    print_status "Deploying to worker server..."
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$WORKER_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$WORKER_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$WORKER_SERVER_IP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.worker.aws.yml ubuntu@$WORKER_SERVER_IP:/opt/anb-app/docker-compose.yml
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$WORKER_SERVER_IP:/opt/anb-app/.env
    
    print_success "Application deployed"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Start web server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WEB_SERVER_IP "
        cd /opt/anb-app
        docker-compose up -d
    "
    
    # Start worker server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WORKER_SERVER_IP "
        cd /opt/anb-app
        docker-compose up -d
    "
    
    print_success "Services started"
}

# Test deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Wait for services to be ready
    sleep 30
    
    # Test web server
    if curl -f http://$WEB_SERVER_IP:8000/health &> /dev/null; then
        print_success "Web server is responding"
    else
        print_error "Web server is not responding"
        exit 1
    fi
    
    # Test API endpoints
    if curl -f http://$WEB_SERVER_IP:8000/ &> /dev/null; then
        print_success "API is responding"
    else
        print_error "API is not responding"
        exit 1
    fi
    
    print_success "Deployment test passed"
}

# Main deployment function
main() {
    print_status "Starting ANB Rising Stars Showcase deployment to AWS..."
    
    # Check if required variables are set
    if [ -z "$DB_PASSWORD" ]; then
        print_error "DB_PASSWORD environment variable is not set"
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ]; then
        print_error "SECRET_KEY environment variable is not set"
        exit 1
    fi
    
    check_requirements
    check_aws_credentials
    deploy_infrastructure
    wait_for_instances
    configure_nfs
    deploy_application
    start_services
    test_deployment
    
    print_success "Deployment completed successfully!"
    print_status "Application URL: http://$WEB_SERVER_IP:8000"
    print_status "API Documentation: http://$WEB_SERVER_IP:8000/docs"
}

# Run main function
main "$@"
