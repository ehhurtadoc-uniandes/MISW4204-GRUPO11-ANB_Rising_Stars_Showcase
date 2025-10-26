#!/bin/bash

# NFS Server User Data Script
# This script configures the NFS server instance

set -e

# Update system
apt-get update -y
apt-get upgrade -y

# Install NFS server
apt-get install -y nfs-kernel-server

# Create NFS export directories
mkdir -p /mnt/nfs/uploads
mkdir -p /mnt/nfs/processed_videos
mkdir -p /mnt/nfs/assets

# Set proper permissions
chown nobody:nogroup /mnt/nfs/uploads
chown nobody:nogroup /mnt/nfs/processed_videos
chown nobody:nogroup /mnt/nfs/assets

chmod 755 /mnt/nfs/uploads
chmod 755 /mnt/nfs/processed_videos
chmod 755 /mnt/nfs/assets

# Configure NFS exports
cat > /etc/exports << 'EOF'
/mnt/nfs/uploads 10.0.0.0/16(rw,sync,no_subtree_check,no_root_squash)
/mnt/nfs/processed_videos 10.0.0.0/16(rw,sync,no_subtree_check,no_root_squash)
/mnt/nfs/assets 10.0.0.0/16(rw,sync,no_subtree_check,no_root_squash)
EOF

# Start and enable NFS services
systemctl start nfs-kernel-server
systemctl enable nfs-kernel-server

# Export the filesystems
exportfs -a

# Install monitoring tools
apt-get install -y htop iotop nethogs

# Create log directory
mkdir -p /var/log/anb
chown ubuntu:ubuntu /var/log/anb

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

# Create a simple health check script
cat > /usr/local/bin/nfs-health-check.sh << 'EOF'
#!/bin/bash
# Check if NFS is running and exports are available
if systemctl is-active --quiet nfs-kernel-server; then
    echo "NFS server is running"
    exportfs -v
    exit 0
else
    echo "NFS server is not running"
    exit 1
fi
EOF

chmod +x /usr/local/bin/nfs-health-check.sh

# Create systemd timer for health checks
cat > /etc/systemd/system/nfs-health-check.service << 'EOF'
[Unit]
Description=NFS Health Check
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/nfs-health-check.sh
EOF

cat > /etc/systemd/system/nfs-health-check.timer << 'EOF'
[Unit]
Description=Run NFS Health Check every 5 minutes
Requires=nfs-health-check.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

systemctl enable nfs-health-check.timer
systemctl start nfs-health-check.timer

echo "NFS server setup completed successfully" > /var/log/anb/setup.log
