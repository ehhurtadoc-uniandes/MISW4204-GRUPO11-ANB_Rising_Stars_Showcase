#!/bin/bash
set -e

# Actualizar sistema
apt update && apt upgrade -y

# Instalar Redis
apt install redis-server -y

# Configurar Redis
cat > /etc/redis/redis.conf << EOF
# Redis configuration file
# Network
bind 0.0.0.0 ::1
port 6379
protected-mode no
tcp-backlog 511
timeout 0
tcp-keepalive 300

# General
daemonize no
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Replication
# replicaof <masterip> <masterport>

# Security
# requirepass foobared

# AOF
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Lazy freeing
lazyfree-lazy-eviction no
lazyfree-lazy-expire no
lazyfree-lazy-server-del no
replica-lazy-flush no

# Threaded I/O
io-threads 4
io-threads-do-reads no
EOF

# Crear directorio de logs
sudo mkdir -p /var/log/redis
sudo chown redis:redis /var/log/redis
sudo chmod 755 /var/log/redis

# Iniciar y habilitar Redis
systemctl restart redis-server
systemctl enable redis-server

# Verificar que Redis esté corriendo
sleep 2
redis-cli ping
# Debe responder: PONG