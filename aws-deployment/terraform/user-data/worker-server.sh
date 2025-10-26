#!/bin/bash

# Worker Server User Data Script
# This script configures the worker server instance

set -e

# Update system
apt-get update -y
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install NFS client
apt-get install -y nfs-common

# Create application directory
mkdir -p /opt/anb-app
cd /opt/anb-app

# Create NFS mount points
mkdir -p /mnt/nfs/uploads
mkdir -p /mnt/nfs/processed_videos

# Install Python and pip
apt-get install -y python3 python3-pip python3-venv

# Install Git
apt-get install -y git

# Install FFmpeg for video processing
apt-get install -y ffmpeg

# Create systemd service for the worker
cat > /etc/systemd/system/anb-worker.service << 'EOF'
[Unit]
Description=ANB Worker Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/anb-app
ExecStart=/usr/local/bin/docker-compose up worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start yet)
systemctl enable anb-worker.service

# Create log directory
mkdir -p /var/log/anb
chown ubuntu:ubuntu /var/log/anb

# Install monitoring tools
apt-get install -y htop iotop nethogs

# Configure log rotation
cat > /etc/logrotate.d/anb << 'EOF'
/var/log/anb/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
}
EOF

echo "Worker server setup completed successfully" > /var/log/anb/setup.log
