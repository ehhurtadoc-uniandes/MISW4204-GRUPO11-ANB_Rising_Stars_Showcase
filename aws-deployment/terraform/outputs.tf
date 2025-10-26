# Outputs for ANB Rising Stars Showcase AWS deployment

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.anb_vpc.id
}

output "web_server_public_ip" {
  description = "Public IP address of the web server"
  value       = aws_instance.web_server.public_ip
}

output "web_server_private_ip" {
  description = "Private IP address of the web server"
  value       = aws_instance.web_server.private_ip
}

output "worker_server_public_ip" {
  description = "Public IP address of the worker server"
  value       = aws_instance.worker_server.public_ip
}

output "worker_server_private_ip" {
  description = "Private IP address of the worker server"
  value       = aws_instance.worker_server.private_ip
}

output "nfs_server_private_ip" {
  description = "Private IP address of the NFS server"
  value       = aws_instance.nfs_server.private_ip
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.anb_postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.anb_redis.primary_endpoint_address
  sensitive   = true
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${aws_instance.web_server.public_ip}:8000"
}

output "ssh_commands" {
  description = "SSH commands to connect to instances"
  value = {
    web_server = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.web_server.public_ip}"
    worker_server = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.worker_server.public_ip}"
    nfs_server = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.nfs_server.private_ip}"
  }
}
