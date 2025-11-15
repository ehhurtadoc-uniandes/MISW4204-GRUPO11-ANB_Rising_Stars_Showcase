#!/bin/bash
# User Data Script for SQS Worker EC2 Instances
# Entrega 4: Workers with SQS and Auto Scaling

set -e

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

# Update system and install Docker based on OS
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    apt update && apt upgrade -y
    apt install docker.io git python3 python3-pip -y
    systemctl start docker
    systemctl enable docker
elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
    yum update -y
    yum install docker git python3 python3-pip -y
    systemctl start docker
    systemctl enable docker
fi

# Add user to docker group
usermod -aG docker $OS_USER

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create directory for application
mkdir -p /opt/anb-worker
cd /opt/anb-worker

# Clone repository (adjust URL as needed)
git clone https://github.com/ehhurtadoc-uniandes/MISW4204-GRUPO11-ANB_Rising_Stars_Showcase.git .

# Create .env file with SQS configuration
cat > .env << EOF
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

# Create startup script for SQS worker
cat > start-worker.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

cd /opt/anb-worker

# Wait for Docker to be ready
until docker info > /dev/null 2>&1; do
    echo "Waiting for Docker..."
    sleep 2
done

# Stop existing container if exists
docker stop anb-worker-sqs || true
docker rm anb-worker-sqs || true

# Build image if it doesn't exist
if ! docker images | grep -q "anb-worker"; then
    echo "Building Docker image..."
    docker build -t anb-worker:latest .
fi

# Run SQS worker
echo "Starting SQS worker container..."
docker run -d --name anb-worker-sqs \
  --env-file .env \
  --restart unless-stopped \
  anb-worker:latest \
  python -m app.workers.sqs_worker

echo "SQS worker service started successfully!"

# Monitor the container so systemd doesn't stop it
while true; do
    if ! docker ps | grep -q "anb-worker-sqs"; then
        echo "Container anb-worker-sqs stopped unexpectedly"
        exit 1
    fi
    sleep 10
done
EOFSCRIPT

chmod +x start-worker.sh

# Create systemd service for auto-restart
cat > /etc/systemd/system/anb-worker-sqs.service << 'EOFSERVICE'
[Unit]
Description=ANB SQS Worker Service
After=docker.service network-online.target
Requires=docker.service network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/anb-worker
ExecStart=/opt/anb-worker/start-worker.sh
ExecStop=/usr/bin/docker stop anb-worker-sqs
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Reload systemd and start service
systemctl daemon-reload
systemctl enable anb-worker-sqs
systemctl start anb-worker-sqs

echo "SQS Worker setup completed!"

