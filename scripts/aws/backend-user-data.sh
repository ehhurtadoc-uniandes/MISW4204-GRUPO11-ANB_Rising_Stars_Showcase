#!/bin/bash
# User data script for ANB Backend EC2 instances
# This script is executed when the instance launches

set -e

echo "=========================================="
echo "ANB Backend - User Data Script"
echo "Started at: $(date)"
echo "=========================================="


# Detect OS and set user
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        OS_USER="ubuntu"
        PACKAGE_MANAGER="apt"
    elif [[ "$ID" == "amzn" ]]; then
        OS_USER="ec2-user"
        PACKAGE_MANAGER="yum"
    else
        OS_USER="ubuntu"
        PACKAGE_MANAGER="apt"
    fi
else
    OS_USER="ubuntu"
    PACKAGE_MANAGER="apt"
fi

echo "Detected OS user: $OS_USER"

# Install Docker based on OS
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo apt update && sudo apt upgrade -y
    sudo apt install docker.io -y
    sudo systemctl start docker
    sudo systemctl enable docker
elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
    sudo yum update -y
    sudo yum install docker -y
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Add user to docker group
sudo usermod -aG docker $OS_USER

# Install Docker Compose (same for both)
echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/anb-api
cd /opt/anb-api

# Clone repository
echo "Cloning repository..."
git clone https://github.com/ehhurtadoc-uniandes/MISW4204-GRUPO11-ANB_Rising_Stars_Showcase.git /tmp/anb-api
cp -r /tmp/anb-api/* /opt/anb-api/
rm -rf /tmp/anb-api

# Create .env file with actual values
echo "Creating .env file..."
cat > .env << 'EOF'
# Database (RDS)
DATABASE_URL=postgresql://anb_user:anb_password@anb-db.cmzycdutcfqt.us-east-1.rds.amazonaws.com:5432/anbdb
POSTGRES_HOST=anb-db.cmzycdutcfqt.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=anb_user
POSTGRES_PASSWORD=anb_password
POSTGRES_DB=anbdb

# SQS Configuration (Entrega 4)
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/906569879596/anb-video-processing-queue
SQS_REGION=us-east-1
SQS_VISIBILITY_TIMEOUT=300
SQS_MAX_RECEIVE_COUNT=3
SQS_WAIT_TIME_SECONDS=20

# JWT Configuration
SECRET_KEY=1cbaf2c31556651ef478e2067555263f33d8d0b359ff990b19c3d3351c620003
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3 Storage (bucket público para lectura)
STORAGE_TYPE=cloud
AWS_REGION=us-east-1
S3_BUCKET_NAME=anb-rising-starts-videos-east1
S3_UPLOAD_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed_videos/

# AWS Credentials
# IMPORTANTE: NO incluir credenciales aquí. Usar IAM Roles en las instancias EC2.
# Si necesitas credenciales temporales, configúralas manualmente en la instancia o usa AWS Systems Manager Parameter Store.
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_SESSION_TOKEN=

# Environment
ENVIRONMENT=production
DEBUG=False

# File Storage (fallback local)
UPLOAD_DIR=/app/uploads
PROCESSED_DIR=/app/processed_videos
MAX_FILE_SIZE_MB=100

# ANB Configuration
ANB_LOGO_PATH=/app/assets/anb_logo.png
VIDEO_MAX_DURATION=30
VIDEO_RESOLUTION=720p
EOF

# Create startup script
echo "Creating startup script..."
cat > start-backend.sh << 'EOFSTART'
#!/bin/bash
set -e

cd /opt/anb-api

# Esperar a que Docker esté listo
until docker info > /dev/null 2>&1; do
    echo "Waiting for Docker..."
    sleep 2
done

# Detener contenedor existente si existe
docker stop anb-api || true
docker rm anb-api || true

# Construir imagen si no existe
if ! docker images | grep -q "anb-api"; then
    echo "Building Docker image..."
    docker build -t anb-api:latest .
fi

# Ejecutar migraciones (contenedor temporal que se elimina después)
echo "Running database migrations..."
docker run --rm --env-file .env \
    anb-api:latest \
    alembic upgrade head || echo "Migration failed, continuing..."

# Iniciar contenedor de la API
echo "Starting API container..."
docker run -d --name anb-api \
    --env-file .env \
    -p 8000:8000 \
    --restart unless-stopped \
    anb-api:latest \
    uvicorn app.main:app --host 0.0.0.0 --port 8000

echo "API service started successfully!"

# Monitorear el contenedor para que systemd no lo detenga
# El script se queda ejecutándose monitoreando el contenedor
while true; do
    if ! docker ps | grep -q "anb-api"; then
        echo "Container anb-api stopped unexpectedly"
        exit 1
    fi
    sleep 10
done
EOFSTART

chmod +x start-backend.sh

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/anb-api.service << 'EOFSERVICE'
[Unit]
Description=ANB API Service
After=docker.service network-online.target
Requires=docker.service network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/anb-api
ExecStart=/opt/anb-api/start-backend.sh
ExecStop=/usr/bin/docker stop anb-api
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Enable and start service
echo "Enabling systemd service..."
systemctl daemon-reload
systemctl enable anb-api

# Wait a bit for everything to be ready
sleep 10

# Start the service
echo "Starting ANB API service..."
systemctl start anb-api

echo "=========================================="
echo "User data script completed at: $(date)"
echo "=========================================="
