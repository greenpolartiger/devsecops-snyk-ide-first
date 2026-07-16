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
  region = "us-east-1"
}

# VULN: S3 bucket with public access enabled
resource "aws_s3_bucket" "app_data" {
  bucket = "vuln-app-data-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  # VULN: Public access not blocked
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# VULN: No encryption enabled
resource "aws_s3_bucket_server_side_encryption_configuration" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# VULN: RDS database without encryption and publicly accessible
resource "aws_db_instance" "app_db" {
  identifier     = "vuln-app-db"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"

  allocated_storage = 20

  # VULN: No encryption
  storage_encrypted = false

  # VULN: Publicly accessible
  publicly_accessible = true

  # VULN: Default master username/password (bad practice)
  db_name  = "appdb"
  username = "admin"
  password = "Admin123456"

  # VULN: No backup retention
  backup_retention_period = 0
  skip_final_snapshot     = true

  # VULN: No monitoring
  enabled_cloudwatch_logs_exports = []
}

# VULN: Security group with overly permissive rules
resource "aws_security_group" "app_sg" {
  name = "vuln-app-sg"

  # VULN: Allow SSH from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # VULN: Allow HTTP from anywhere
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # VULN: Allow database port from anywhere
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# VULN: EC2 instance with default settings and no IAM role
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  # VULN: No IAM instance profile
  # Should have: iam_instance_profile = aws_iam_instance_profile.app.name

  # VULN: Root volume not encrypted
  root_block_device {
    volume_type           = "gp2"
    volume_size           = 20
    delete_on_termination = true
    encrypted             = false
  }

  security_groups = [aws_security_group.app_sg.name]

  # VULN: Passing secrets in user data
  user_data = base64encode(<<-EOF
              #!/bin/bash
              export API_KEY="sk-1234567890abcdefghijklmnop"
              export DB_PASSWORD="admin123"
              EOF
  )

  tags = {
    Name = "vuln-app-server"
  }
}

data "aws_caller_identity" "current" {}

output "s3_bucket" {
  value = aws_s3_bucket.app_data.id
}

output "rds_endpoint" {
  value = aws_db_instance.app_db.endpoint
}

output "ec2_public_ip" {
  value = aws_instance.app_server.public_ip
}