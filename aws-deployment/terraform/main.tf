# Terraform configuration for ANB Rising Stars Showcase AWS deployment
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-22.04-lts-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC
resource "aws_vpc" "anb_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "anb-vpc"
    Project = "ANB-Rising-Stars"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "anb_igw" {
  vpc_id = aws_vpc.anb_vpc.id

  tags = {
    Name = "anb-igw"
    Project = "ANB-Rising-Stars"
  }
}

# Public Subnets
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.anb_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "anb-public-subnet-1"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.anb_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name = "anb-public-subnet-2"
    Project = "ANB-Rising-Stars"
  }
}

# Private Subnets
resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.anb_vpc.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "anb-private-subnet-1"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.anb_vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "anb-private-subnet-2"
    Project = "ANB-Rising-Stars"
  }
}

# Route Tables
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.anb_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.anb_igw.id
  }

  tags = {
    Name = "anb-public-rt"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.anb_vpc.id

  tags = {
    Name = "anb-private-rt"
    Project = "ANB-Rising-Stars"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private_rt.id
}

# Security Groups
resource "aws_security_group" "web_sg" {
  name_prefix = "anb-web-sg"
  vpc_id      = aws_vpc.anb_vpc.id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # FastAPI
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NFS
  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "anb-web-sg"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_security_group" "worker_sg" {
  name_prefix = "anb-worker-sg"
  vpc_id      = aws_vpc.anb_vpc.id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NFS
  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "anb-worker-sg"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_security_group" "nfs_sg" {
  name_prefix = "anb-nfs-sg"
  vpc_id      = aws_vpc.anb_vpc.id

  # NFS
  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "anb-nfs-sg"
    Project = "ANB-Rising-Stars"
  }
}

resource "aws_security_group" "rds_sg" {
  name_prefix = "anb-rds-sg"
  vpc_id      = aws_vpc.anb_vpc.id

  # PostgreSQL
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id, aws_security_group.worker_sg.id]
  }

  tags = {
    Name = "anb-rds-sg"
    Project = "ANB-Rising-Stars"
  }
}

# Key Pair
resource "aws_key_pair" "anb_key" {
  key_name   = "anb-key-pair"
  public_key = file(var.public_key_path)

  tags = {
    Name = "anb-key-pair"
    Project = "ANB-Rising-Stars"
  }
}

# EC2 Instances
resource "aws_instance" "web_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.anb_key.key_name
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  subnet_id             = aws_subnet.public_subnet_1.id

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user-data/web-server.sh")

  tags = {
    Name = "anb-web-server"
    Project = "ANB-Rising-Stars"
    Role = "web-server"
  }
}

resource "aws_instance" "worker_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.anb_key.key_name
  vpc_security_group_ids = [aws_security_group.worker_sg.id]
  subnet_id             = aws_subnet.public_subnet_2.id

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user-data/worker-server.sh")

  tags = {
    Name = "anb-worker-server"
    Project = "ANB-Rising-Stars"
    Role = "worker"
  }
}

resource "aws_instance" "nfs_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name              = aws_key_pair.anb_key.key_name
  vpc_security_group_ids = [aws_security_group.nfs_sg.id]
  subnet_id             = aws_subnet.private_subnet_1.id

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user-data/nfs-server.sh")

  tags = {
    Name = "anb-nfs-server"
    Project = "ANB-Rising-Stars"
    Role = "nfs-server"
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "anb_db_subnet_group" {
  name       = "anb-db-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]

  tags = {
    Name = "anb-db-subnet-group"
    Project = "ANB-Rising-Stars"
  }
}

# RDS Instance
resource "aws_db_instance" "anb_postgres" {
  identifier = "anb-postgres-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true
  
  db_name  = "anb_db"
  username = "anb_user"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.anb_db_subnet_group.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  tags = {
    Name = "anb-postgres-db"
    Project = "ANB-Rising-Stars"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "anb_redis_subnet_group" {
  name       = "anb-redis-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "anb_redis" {
  replication_group_id       = "anb-redis"
  description                = "Redis for ANB application"
  
  node_type                  = "cache.t3.micro"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  
  num_cache_clusters         = 1
  
  subnet_group_name          = aws_elasticache_subnet_group.anb_redis_subnet_group.name
  security_group_ids         = [aws_security_group.redis_sg.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name = "anb-redis"
    Project = "ANB-Rising-Stars"
  }
}

# Security Group for Redis
resource "aws_security_group" "redis_sg" {
  name_prefix = "anb-redis-sg"
  vpc_id      = aws_vpc.anb_vpc.id

  # Redis
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id, aws_security_group.worker_sg.id]
  }

  tags = {
    Name = "anb-redis-sg"
    Project = "ANB-Rising-Stars"
  }
}
