# ANB Rising Stars Showcase - AWS Deployment Script (PowerShell)
# This script deploys the application to AWS

param(
    [Parameter(Mandatory=$true)]
    [string]$DBPassword,
    
    [Parameter(Mandatory=$true)]
    [string]$SecretKey,
    
    [string]$AWSRegion = "us-east-1"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if required tools are installed
function Test-Requirements {
    Write-Status "Checking requirements..."
    
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Error "Terraform is not installed. Please install Terraform first."
        exit 1
    }
    
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    }
    
    Write-Success "All requirements are met"
}

# Check AWS credentials
function Test-AWSCredentials {
    Write-Status "Checking AWS credentials..."
    
    try {
        aws sts get-caller-identity | Out-Null
        Write-Success "AWS credentials are configured"
    }
    catch {
        Write-Error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    }
}

# Deploy infrastructure with Terraform
function Deploy-Infrastructure {
    Write-Status "Deploying infrastructure with Terraform..."
    
    Set-Location terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    $script:WebServerIP = terraform output -raw web_server_public_ip
    $script:WorkerServerIP = terraform output -raw worker_server_public_ip
    $script:NFSServerIP = terraform output -raw nfs_server_private_ip
    $script:RDSEndpoint = terraform output -raw rds_endpoint
    $script:RedisEndpoint = terraform output -raw redis_endpoint
    
    Write-Success "Infrastructure deployed successfully"
    Write-Status "Web Server IP: $WebServerIP"
    Write-Status "Worker Server IP: $WorkerServerIP"
    Write-Status "NFS Server IP: $NFSServerIP"
    Write-Status "RDS Endpoint: $RDSEndpoint"
    Write-Status "Redis Endpoint: $RedisEndpoint"
    
    Set-Location ..
}

# Wait for instances to be ready
function Wait-ForInstances {
    Write-Status "Waiting for instances to be ready..."
    
    # Wait for web server
    Write-Status "Waiting for web server to be ready..."
    do {
        try {
            ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WebServerIP "echo 'Web server is ready'" 2>$null
            $webReady = $true
        }
        catch {
            $webReady = $false
            Write-Status "Web server not ready yet, waiting..."
            Start-Sleep -Seconds 10
        }
    } while (-not $webReady)
    
    # Wait for worker server
    Write-Status "Waiting for worker server to be ready..."
    do {
        try {
            ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WorkerServerIP "echo 'Worker server is ready'" 2>$null
            $workerReady = $true
        }
        catch {
            $workerReady = $false
            Write-Status "Worker server not ready yet, waiting..."
            Start-Sleep -Seconds 10
        }
    } while (-not $workerReady)
    
    # Wait for NFS server
    Write-Status "Waiting for NFS server to be ready..."
    do {
        try {
            ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$NFSServerIP "echo 'NFS server is ready'" 2>$null
            $nfsReady = $true
        }
        catch {
            $nfsReady = $false
            Write-Status "NFS server not ready yet, waiting..."
            Start-Sleep -Seconds 10
        }
    } while (-not $nfsReady)
    
    Write-Success "All instances are ready"
}

# Configure NFS mounts
function Set-NFSMounts {
    Write-Status "Configuring NFS mounts..."
    
    # Configure NFS on web server
    $nfsCommands = @"
sudo mount -t nfs $NFSServerIP:/mnt/nfs/uploads /mnt/nfs/uploads
sudo mount -t nfs $NFSServerIP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos
sudo mount -t nfs $NFSServerIP:/mnt/nfs/assets /mnt/nfs/assets

# Add to fstab for persistence
echo '$NFSServerIP:/mnt/nfs/uploads /mnt/nfs/uploads nfs defaults 0 0' | sudo tee -a /etc/fstab
echo '$NFSServerIP:/mnt/nfs/processed_videos /mnt/nfs/processed_videos nfs defaults 0 0' | sudo tee -a /etc/fstab
echo '$NFSServerIP:/mnt/nfs/assets /mnt/nfs/assets nfs defaults 0 0' | sudo tee -a /etc/fstab
"@
    
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WebServerIP $nfsCommands
    
    # Configure NFS on worker server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WorkerServerIP $nfsCommands
    
    Write-Success "NFS mounts configured"
}

# Deploy application
function Deploy-Application {
    Write-Status "Deploying application..."
    
    # Create environment file
    $envContent = @"
DB_PASSWORD=$DBPassword
RDS_ENDPOINT=$RDSEndpoint
REDIS_ENDPOINT=$RedisEndpoint
NFS_SERVER_IP=$NFSServerIP
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=$SecretKey
"@
    
    $envContent | Out-File -FilePath ".env.aws" -Encoding UTF8
    
    # Deploy to web server
    Write-Status "Deploying to web server..."
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$WebServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../alembic ubuntu@$WebServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$WebServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$WebServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../alembic.ini ubuntu@$WebServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.aws.yml ubuntu@$WebServerIP:/opt/anb-app/docker-compose.yml
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$WebServerIP:/opt/anb-app/.env
    
    # Deploy to worker server
    Write-Status "Deploying to worker server..."
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa -r ../app ubuntu@$WorkerServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../Dockerfile ubuntu@$WorkerServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ../requirements.txt ubuntu@$WorkerServerIP:/opt/anb-app/
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa docker-compose.worker.aws.yml ubuntu@$WorkerServerIP:/opt/anb-app/docker-compose.yml
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa .env.aws ubuntu@$WorkerServerIP:/opt/anb-app/.env
    
    Write-Success "Application deployed"
}

# Start services
function Start-Services {
    Write-Status "Starting services..."
    
    # Start web server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WebServerIP "cd /opt/anb-app; docker-compose up -d"
    
    # Start worker server
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$WorkerServerIP "cd /opt/anb-app; docker-compose up -d"
    
    Write-Success "Services started"
}

# Test deployment
function Test-Deployment {
    Write-Status "Testing deployment..."
    
    # Wait for services to be ready
    Start-Sleep -Seconds 30
    
    # Test web server
    try {
        $response = Invoke-WebRequest -Uri "http://$WebServerIP:8000/health" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "Web server is responding"
        }
    }
    catch {
        Write-Error "Web server is not responding"
        exit 1
    }
    
    # Test API endpoints
    try {
        $response = Invoke-WebRequest -Uri "http://$WebServerIP:8000/" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "API is responding"
        }
    }
    catch {
        Write-Error "API is not responding"
        exit 1
    }
    
    Write-Success "Deployment test passed"
}

# Main deployment function
function Main {
    Write-Status "Starting ANB Rising Stars Showcase deployment to AWS..."
    
    Test-Requirements
    Test-AWSCredentials
    Deploy-Infrastructure
    Wait-ForInstances
    Set-NFSMounts
    Deploy-Application
    Start-Services
    Test-Deployment
    
    Write-Success "Deployment completed successfully!"
    Write-Status "Application URL: http://$WebServerIP:8000"
    Write-Status "API Documentation: http://$WebServerIP:8000/docs"
}

# Run main function
Main
