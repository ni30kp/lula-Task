# Support Copilot - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [AWS Deployment](#aws-deployment)
5. [Production Configuration](#production-configuration)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **RAM**: 8GB+ (16GB+ recommended for production)
- **Storage**: 50GB+ available space
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS

### Software Requirements
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.9+ (for local development)
- **Git**: Latest version

### AWS Requirements (for cloud deployment)
- **AWS CLI**: Configured with appropriate permissions
- **Terraform**: 1.0+ (for infrastructure as code)
- **Kubernetes**: 1.21+ (if using EKS)

## Local Development Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd support-copilot
```

### 2. Set Up Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables:**
```env
# Application Settings
DEBUG=false
SECRET_KEY=your-secure-secret-key-here

# Database Settings
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=support_user
MYSQL_PASSWORD=support_password
MYSQL_DATABASE=support_copilot

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ Settings
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# AI/ML Settings
OPENAI_API_KEY=your-openai-api-key
HUGGINGFACE_API_KEY=your-huggingface-api-key

# AWS Settings (for production)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
```

### 3. Install Dependencies
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Initialize Database
```bash
# Start MySQL container
docker run -d \
  --name mysql-dev \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -e MYSQL_DATABASE=support_copilot \
  -e MYSQL_USER=support_user \
  -e MYSQL_PASSWORD=support_password \
  -p 3306:3306 \
  mysql:8.0

# Wait for MySQL to start
sleep 30

# Initialize database
mysql -h localhost -P 3306 -u support_user -psupport_password support_copilot < init.sql
```

### 5. Start Services
```bash
# Start Redis
docker run -d --name redis-dev -p 6379:6379 redis:7-alpine

# Start RabbitMQ
docker run -d \
  --name rabbitmq-dev \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management-alpine

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Verify Installation
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test API documentation
open http://localhost:8000/docs
```

## Docker Deployment

### 1. Build and Start All Services
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f support-copilot-api
```

### 2. Initialize Database
```bash
# Wait for MySQL to be ready
docker-compose exec mysql mysql -u root -proot_password -e "SELECT 1"

# Initialize database (already handled by init.sql in docker-compose)
docker-compose exec mysql mysql -u support_user -psupport_password support_copilot -e "SHOW TABLES;"
```

### 3. Verify Deployment
```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/metrics

# Access monitoring dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# RabbitMQ Management: http://localhost:15672 (guest/guest)
```

### 4. Scale Services
```bash
# Scale API service
docker-compose up -d --scale support-copilot-api=3

# Scale with specific resources
docker-compose up -d --scale support-copilot-api=3 --scale mysql=1 --scale redis=1
```

## AWS Deployment

### 1. Infrastructure Setup with Terraform

**Create `terraform/main.tf`:**
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  environment = var.environment
}

# RDS MySQL Database
module "rds" {
  source = "./modules/rds"
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  environment = var.environment
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  environment = var.environment
}

# ECS Fargate Cluster
module "ecs" {
  source = "./modules/ecs"
  vpc_id = module.vpc.vpc_id
  public_subnets = module.vpc.public_subnets
  private_subnets = module.vpc.private_subnets
  environment = var.environment
  rds_endpoint = module.rds.endpoint
  redis_endpoint = module.redis.endpoint
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  vpc_id = module.vpc.vpc_id
  public_subnets = module.vpc.public_subnets
  environment = var.environment
}
```

### 2. Deploy Infrastructure
```bash
# Initialize Terraform
cd terraform
terraform init

# Plan deployment
terraform plan -var-file=environments/prod.tfvars

# Apply infrastructure
terraform apply -var-file=environments/prod.tfvars
```

### 3. Deploy Application
```bash
# Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t support-copilot .
docker tag support-copilot:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/support-copilot:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/support-copilot:latest

# Deploy to ECS
aws ecs update-service --cluster support-copilot-cluster --service support-copilot-service --force-new-deployment
```

### 4. Configure CI/CD Pipeline

**Create `.github/workflows/deploy.yml`:**
```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: support-copilot
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster support-copilot-cluster \
            --service support-copilot-service \
            --force-new-deployment
```

## Production Configuration

### 1. Environment Variables for Production
```env
# Production Settings
DEBUG=false
ENVIRONMENT=production

# Security
SECRET_KEY=your-very-secure-production-secret-key
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Database (RDS)
MYSQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_USER=support_user
MYSQL_PASSWORD=your-secure-db-password
MYSQL_DATABASE=support_copilot

# Redis (ElastiCache)
REDIS_HOST=your-redis-endpoint.region.cache.amazonaws.com
REDIS_PORT=6379

# RabbitMQ (Amazon MQ)
RABBITMQ_HOST=your-rabbitmq-endpoint.region.amazonaws.com
RABBITMQ_PORT=5671
RABBITMQ_USER=your-rabbitmq-user
RABBITMQ_PASSWORD=your-rabbitmq-password

# AI/ML Services
OPENAI_API_KEY=your-openai-api-key
HUGGINGFACE_API_KEY=your-huggingface-api-key

# AWS Services
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name

# Monitoring
CLOUDWATCH_LOG_GROUP=/aws/ecs/support-copilot
METRICS_NAMESPACE=SupportCopilot
```

### 2. SSL/TLS Configuration
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://support-copilot-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Auto Scaling Configuration
```json
{
  "autoScalingGroupName": "support-copilot-asg",
  "minSize": 2,
  "maxSize": 10,
  "desiredCapacity": 3,
  "targetTrackingConfigurations": [
    {
      "targetValue": 70.0,
      "predefinedMetricSpecification": {
        "predefinedMetricType": "ASGAverageCPUUtilization"
      }
    }
  ]
}
```

## Monitoring and Logging

### 1. CloudWatch Logs Configuration
```python
# app/core/logging.py
import logging
import boto3
from watchtower import CloudWatchLogHandler

def setup_cloudwatch_logging():
    logger = logging.getLogger('support_copilot')
    logger.setLevel(logging.INFO)
    
    # CloudWatch handler
    cloudwatch_handler = CloudWatchLogHandler(
        log_group='/aws/ecs/support-copilot',
        stream_name='application-logs',
        boto3_client=boto3.client('logs')
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    cloudwatch_handler.setFormatter(formatter)
    logger.addHandler(cloudwatch_handler)
    
    return logger
```

### 2. Prometheus Metrics
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# API Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_ISSUES = Gauge('active_issues_total', 'Total active issues')
CRITICAL_ISSUES = Gauge('critical_issues_total', 'Total critical issues')

# AI Metrics
AI_ANALYSIS_DURATION = Histogram('ai_analysis_duration_seconds', 'AI analysis duration')
RECOMMENDATION_CONFIDENCE = Histogram('recommendation_confidence', 'Recommendation confidence scores')
```

### 3. Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Support Copilot Metrics",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Active Issues",
        "type": "stat",
        "targets": [
          {
            "expr": "active_issues_total"
          }
        ]
      },
      {
        "title": "Critical Issues",
        "type": "stat",
        "targets": [
          {
            "expr": "critical_issues_total"
          }
        ]
      }
    ]
  }
}
```

## Security Considerations

### 1. Network Security
```bash
# Security Groups
aws ec2 create-security-group \
  --group-name support-copilot-api-sg \
  --description "Security group for Support Copilot API"

# Allow HTTPS only
aws ec2 authorize-security-group-ingress \
  --group-name support-copilot-api-sg \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 2. IAM Roles and Policies
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": "arn:aws:rds-db:*:*:dbuser:*/*"
    }
  ]
}
```

### 3. Secrets Management
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name support-copilot/database \
  --description "Support Copilot database credentials" \
  --secret-string '{"username":"support_user","password":"secure-password"}'

# Retrieve secrets in application
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check MySQL connectivity
docker-compose exec mysql mysql -u support_user -psupport_password -e "SELECT 1"

# Check connection pool
docker-compose logs support-copilot-api | grep "database"
```

#### 2. Redis Connection Issues
```bash
# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check Redis memory usage
docker-compose exec redis redis-cli info memory
```

#### 3. AI Service Issues
```bash
# Check OpenAI API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check model loading
docker-compose logs support-copilot-api | grep "AI models"
```

#### 4. Performance Issues
```bash
# Check resource usage
docker stats

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health"

# Monitor database performance
docker-compose exec mysql mysql -u root -proot_password -e "SHOW PROCESSLIST;"
```

### Log Analysis
```bash
# View application logs
docker-compose logs -f support-copilot-api

# Search for errors
docker-compose logs support-copilot-api | grep -i error

# Monitor specific endpoints
docker-compose logs support-copilot-api | grep "POST /api/v1/issues/analyze"
```

### Health Checks
```bash
# API Health
curl http://localhost:8000/health

# Database Health
docker-compose exec mysql mysql -u support_user -psupport_password -e "SELECT COUNT(*) FROM issues;"

# Redis Health
docker-compose exec redis redis-cli ping

# RabbitMQ Health
curl -u guest:guest http://localhost:15672/api/overview
```

## Performance Optimization

### 1. Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_issues_customer_status ON issues(customer_id, status);
CREATE INDEX idx_issues_created_severity ON issues(created_at, severity);
CREATE INDEX idx_conversations_issue_created ON conversations(issue_id, created_at);

-- Optimize queries
EXPLAIN SELECT * FROM issues WHERE customer_id = 1 AND status = 'OPEN';
```

### 2. Caching Strategy
```python
# Cache frequently accessed data
@cache(ttl=300)  # 5 minutes
def get_customer_history(customer_id: int):
    # Implementation
    pass

# Cache AI model results
@cache(ttl=3600)  # 1 hour
def get_similar_issues(issue_text: str):
    # Implementation
    pass
```

### 3. Load Balancing
```nginx
# Nginx upstream configuration
upstream support_copilot {
    least_conn;
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://support_copilot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

This deployment guide provides comprehensive instructions for setting up the Support Copilot system in various environments, from local development to production AWS deployment. 