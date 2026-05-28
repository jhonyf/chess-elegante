# AWS ECS Fargate Deployment Guide

This guide covers deploying Chess Elegante to AWS ECS Fargate with RDS PostgreSQL and Application Load Balancer.

---

## Architecture Overview

**Components:**
- **ECS Fargate** - Runs the containerized Flask application
- **RDS PostgreSQL** - Database for users, games, and PGNs
- **Application Load Balancer** - HTTPS termination and traffic routing
- **ECR** - Docker image registry
- **Secrets Manager** - Stores sensitive credentials
- **CloudWatch** - Logs and monitoring
- **Route 53** - DNS management (optional)
- **ACM** - Free SSL/TLS certificates

**Network:**
- VPC with public subnets
- ALB provides HTTPS and stable endpoint
- ECS tasks in public subnets with security group restrictions
- RDS in public subnet (restricted to ECS security group)

---

## Prerequisites

1. AWS Account
2. AWS CLI installed and configured
3. Docker installed locally
4. Domain name (recommended for OAuth and HTTPS)
5. SSL certificate in ACM for your domain (can be created during setup)

---

## Step 1: Build and Test Docker Image Locally

### 1.1 Test with Docker Compose

```bash
# Build and run locally
docker-compose up --build

# Test the application
curl http://localhost:5000

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

### 1.2 Test Production Image

```bash
# Build production image
docker build -t chess-elegante:latest .

# Run with environment variables
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://chess:chess@host.docker.internal:5432/chess_elegante \
  -e SECRET_KEY=your_secret_key \
  -e GOOGLE_CLIENT_ID=your_google_client_id \
  -e GOOGLE_CLIENT_SECRET=your_google_client_secret \
  chess-elegante:latest

# Test
curl http://localhost:5000
```

---

## Step 2: Set Up AWS Infrastructure

### 2.1 Create VPC with Public Subnets

**Create VPC via AWS Console:**

1. Go to **VPC Console** → **Create VPC**
2. Select **VPC and more**
3. Settings:
   - Name: `chess-elegante-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - AZs: `2`
   - Public subnets: `2`
   - Private subnets: `0`
   - NAT gateways: `None`
   - VPC endpoints: `None`
4. Click **Create VPC**

**Set Environment Variables:**

After creating the VPC, set these environment variables for use in subsequent commands:

```bash
# Set by VPC name (if you named it chess-elegante-vpc)
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=chess-elegante-vpc" --query 'Vpcs[0].VpcId' --output text)
export SUBNET_1=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*public1*" --query 'Subnets[0].SubnetId' --output text)
export SUBNET_2=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*public2*" --query 'Subnets[0].SubnetId' --output text)

# Verify environment variables are set
echo "VPC ID: $VPC_ID"
echo "Subnet 1: $SUBNET_1"
echo "Subnet 2: $SUBNET_2"
```

### 2.2 Create RDS PostgreSQL

```bash
# Create DB subnet group (use public subnets)
aws rds create-db-subnet-group \
  --db-subnet-group-name chess-db-subnet-group \
  --db-subnet-group-description "Subnet group for Chess Elegante RDS" \
  --subnet-ids $SUBNET_1 $SUBNET_2

# Create RDS security group
aws ec2 create-security-group \
  --group-name chess-rds-sg \
  --description "Security group for Chess Elegante RDS" \
  --vpc-id $VPC_ID

RDS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=chess-rds-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow PostgreSQL from ECS tasks ONLY (will create ECS SG next)
# Note: We'll add the rule after creating ECS security group

# Create RDS instance via UI
db-identifier: chess-elegante-db
user: postgres # note that default db-name will be postgres
vpc: chess-elegante-vpc
subnet groups: only select chess-db-subnet-group 
security group: only select chess-rds-sg
public-ip: disable

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier chess-elegante-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "RDS Endpoint: $RDS_ENDPOINT"
echo "Connection string: postgresql://chess:YOUR_PASSWORD@$RDS_ENDPOINT:5432/chess_elegante"
```

### 2.3 Connect to RDS and Inspect Database

Since RDS is only accessible from within the VPC (via ECS tasks), you need to connect through an ECS task.

**Method 1: Use ECS Exec (Recommended)**

First, ensure your ECS service has ECS Exec enabled (you'll do this after creating the service in Step 7):

```bash
# Enable ECS Exec on service (after service is created)
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --enable-execute-command

# Get running task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster chess-elegante-cluster \
  --service-name chess-elegante-service \
  --query 'taskArns[0]' \
  --output text)

echo "Task ARN: $TASK_ARN"

# Connect to the running container
aws ecs execute-command \
  --cluster chess-elegante-cluster \
  --task $TASK_ARN \
  --container chess-elegante-app \
  --interactive \
  --command "/bin/bash"
```

**Inside the ECS container, run psql:**

```bash
# Install PostgreSQL client (if not in Docker image)
apt-get update && apt-get install -y postgresql-client

# Connect to RDS using environment variables
psql $DATABASE_URL

# Or connect manually
psql -h $RDS_ENDPOINT -U postgres -d postgres
```

**Common Database Commands:**

```sql
-- List all databases
\l

-- Connect to chess_elegante database (if not already connected)
\c postgres 

-- List all tables
\dt

-- Show table schema
\d users
\d games
\d pgns

-- Check if tables exist (after migration)
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Count records
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM games;

-- View recent games
SELECT id, user_id, created_at, status FROM games ORDER BY created_at DESC LIMIT 10;

-- Check database size
SELECT pg_size_pretty(pg_database_size('chess_elegante'));

-- Exit psql
\q
```


**Create Additional Users (Optional):**

Once connected via any method above, you can create additional database users:

```sql
-- Create read-only user for analytics
CREATE USER analytics_user WITH PASSWORD 'analytics_password';
GRANT CONNECT ON DATABASE chess_elegante TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_user;

-- Create application user with full access
CREATE USER app_user WITH PASSWORD 'app_password';
GRANT ALL PRIVILEGES ON DATABASE chess_elegante TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;
```

**Troubleshooting:**

```bash
# Verify RDS is running
aws rds describe-db-instances \
  --db-instance-identifier chess-elegante-db \
  --query 'DBInstances[0].[DBInstanceStatus,Endpoint.Address]' \
  --output table

# Check ECS task can reach RDS (test from inside ECS container)
nc -zv $RDS_ENDPOINT 5432

# Check security group allows ECS -> RDS
aws ec2 describe-security-groups \
  --group-ids $RDS_SG \
  --query 'SecurityGroups[0].IpPermissions[?ToPort==`5432`]'
```

---

## Step 3: Create ECR Repository and Push Image

### 3.1 Create ECR Repository

```bash
# Create repository
aws ecr create-repository --repository-name chess-elegante

# Get repository URI
REPO_URI=$(aws ecr describe-repositories --repository-names chess-elegante --query 'repositories[0].repositoryUri' --output text)
echo $REPO_URI
```

### 3.2 Build and Push Image

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build image
docker build -t chess-elegante:latest .

# Tag image
docker tag chess-elegante:latest $REPO_URI:latest
docker tag chess-elegante:latest $REPO_URI:v1.0.0

# Push to ECR
docker push $REPO_URI:latest
docker push $REPO_URI:v1.0.0
```

---

## Step 4: Store Secrets in AWS Secrets Manager

### 4.1 Create Secrets

```bash
# Database URL
aws secretsmanager create-secret \
  --name chess-elegante/DATABASE_URL \
  --secret-string "postgresql://postgres:YOUR_PASSWORD@your-rds-endpoint.rds.amazonaws.com:5432/postgres"

# Google OAuth
aws secretsmanager create-secret \
  --name chess-elegante/GOOGLE_CLIENT_ID \
  --secret-string "your_google_client_id.apps.googleusercontent.com"

aws secretsmanager create-secret \
  --name chess-elegante/GOOGLE_CLIENT_SECRET \
  --secret-string "your_google_client_secret"

# Apple OAuth
aws secretsmanager create-secret \
  --name chess-elegante/APPLE_CLIENT_ID \
  --secret-string "com.yourcompany.chesselegante"

aws secretsmanager create-secret \
  --name chess-elegante/APPLE_CLIENT_SECRET \
  --secret-string "your_apple_jwt_token"

# Flask Secret Key
aws secretsmanager create-secret \
  --name chess-elegante/SECRET_KEY \
  --secret-string "$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Lichess API Token
aws secretsmanager create-secret \
  --name chess-elegante/LICHESS_API_TOKEN \
  --secret-string "your_lichess_token"

# OpenAI API Key
aws secretsmanager create-secret \
  --name chess-elegante/OPENAI_API_KEY \
  --secret-string "your_openai_api_key"

# Anthropic API Key (optional)
aws secretsmanager create-secret \
  --name chess-elegante/ANTHROPIC_API_KEY \
  --secret-string "your_anthropic_api_key"
```

---

## Step 5: Create ECS Cluster and Task Definition

### 5.1 Create ECS Cluster

```bash
# Create Fargate cluster
aws ecs create-cluster --cluster-name chess-elegante-cluster
```

### 5.2 Create IAM Roles

**Task Execution Role** (for pulling images and secrets):

```bash
# Create trust policy
cat > ecs-task-execution-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add Secrets Manager permissions
cat > ecs-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:$ACCOUNT_ID:secret:chess-elegante/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerAccess \
  --policy-document file://ecs-secrets-policy.json
```

**Task Role** (for application to access AWS services and ECS Exec):

```bash
# Create role
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Add SSM permissions for ECS Exec
cat > ecs-task-ssm-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ecsTaskRole \
  --policy-name ECSExecPolicy \
  --policy-document file://ecs-task-ssm-policy.json

# If your app needs to access other AWS services (S3, etc.), attach policies here
```

### 5.3 Create CloudWatch Log Group

```bash
aws logs create-log-group --log-group-name /ecs/chess-elegante
```

### 5.4 Register Task Definition

Update `ecs-task-definition.json` with your account ID and region, then:

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

---

## Step 6: Create Application Load Balancer

### 6.1 Create Security Groups

```bash
# Create security group for ALB
aws ec2 create-security-group \
  --group-name chess-alb-sg \
  --description "Security group for Chess Elegante ALB" \
  --vpc-id $VPC_ID

ALB_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=chess-alb-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow HTTP from anywhere (for redirect to HTTPS)
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Create security group for ECS tasks
aws ec2 create-security-group \
  --group-name chess-ecs-tasks-sg \
  --description "Security group for Chess Elegante ECS tasks" \
  --vpc-id $VPC_ID

ECS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=chess-ecs-tasks-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP from ALB only
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 5000 \
  --source-group $ALB_SG

# Allow all outbound traffic (for Lichess, OAuth, AI APIs, RDS)
aws ec2 authorize-security-group-egress \
  --group-id $ECS_SG \
  --protocol -1 \
  --cidr 0.0.0.0/0

# Allow RDS access from ECS tasks
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG

echo "ALB Security Group: $ALB_SG"
echo "ECS Security Group: $ECS_SG"
```

### 6.2 Create Target Group

```bash
# Create target group for ECS tasks
aws elbv2 create-target-group \
  --name chess-elegante-tg \
  --protocol HTTP \
  --port 5000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-path / \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Get target group ARN
TG_ARN=$(aws elbv2 describe-target-groups --names chess-elegante-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
echo "Target Group ARN: $TG_ARN"
```

### 6.3 Request SSL Certificate (if needed)

```bash
# Request ACM certificate for your domain
aws acm request-certificate \
  --domain-name chesselegante.com \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates --query 'CertificateSummaryList[?DomainName==`chesselegante.com`].CertificateArn' --output text)

# Validate the certificate by adding DNS records (follow AWS Console instructions)
echo "Certificate ARN: $CERT_ARN"
echo "Add the DNS validation records shown in ACM console"
```

### 6.4 Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name chess-elegante-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4

# Get ALB ARN and DNS name
ALB_ARN=$(aws elbv2 describe-load-balancers --names chess-elegante-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)
ALB_DNS=$(aws elbv2 describe-load-balancers --names chess-elegante-alb --query 'LoadBalancers[0].DNSName' --output text)

echo "ALB ARN: $ALB_ARN"
echo "ALB DNS: $ALB_DNS"

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

# Create HTTP listener (redirect to HTTPS)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

echo "ALB created successfully!"
echo "Access your app at: https://$ALB_DNS"
```

---

## Step 7: Create ECS Service with ALB

```bash
# Create service with ALB integration
aws ecs create-service \
  --cluster chess-elegante-cluster \
  --service-name chess-elegante-service \
  --task-definition chess-elegante:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=chess-elegante-app,containerPort=5000"

# Wait for service to stabilize
echo "Waiting for service to start..."
aws ecs wait services-stable --cluster chess-elegante-cluster --services chess-elegante-service

echo "Service created successfully!"
echo "Access your app at: https://$ALB_DNS"
```

---

## Step 8: Configure DNS

If you have a domain name, you can point it to your ALB for a custom URL.

Log into your Cloudflare account
Select your domain chesselegante.com
Go to the DNS section (left sidebar)
Click Add record
Configure the record:

Type: CNAME
Name: @ (for root domain) or www (for www subdomain)
Target: Paste your ALB DNS name (e.g., chess-elegante-alb-123456789.us-east-1.elb.amazonaws.com)
Proxy status: Toggle to DNS only (gray cloud) - this is important!
TTL: Auto

Click Save

## Step 9: Update OAuth Redirect URIs

Update your OAuth provider settings to use your ALB URL:

**Google Console:**
- Go to https://console.cloud.google.com/apis/credentials
- Edit OAuth Client ID
- Add authorized redirect URI: `https://chesselegante.com/auth/google/callback`
  (or use ALB DNS: `https://$ALB_DNS/auth/google/callback`)

**Apple Developer Console:**
- Edit your App ID configuration
- Add return URL: `https://chesselegante.com/auth/apple/callback`

---

## Step 10: Initialize Database and Set Up Migrations

### 10.1 Initial Database Setup

**Option A: Use ECS Exec (Recommended)**

```bash
# Enable ECS Exec on service
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --enable-execute-command

# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster chess-elegante-cluster \
  --service-name chess-elegante-service \
  --query 'taskArns[0]' \
  --output text)

# Connect to task
aws ecs execute-command \
  --cluster chess-elegante-cluster \
  --task $TASK_ARN \
  --container chess-elegante-app \
  --interactive \
  --command "/bin/bash"

# Inside container:
# Apply database migrations
flask db upgrade

# Verify tables were created
psql $DATABASE_URL -c "\dt"
```

**Option B: Run as one-off task**

```bash
# Apply migrations as one-off task
aws ecs run-task \
  --cluster chess-elegante-cluster \
  --task-definition chess-elegante \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"chess-elegante-app","command":["flask","db","upgrade"]}]}'
```

See [Migrations Guide](MIGRATIONS.md) for detailed migration workflow.

### 10.2 Updating Database Schema (After Deployment)

When you need to add new fields to your models:

**Step 1: Update models.py locally**

```python
# Example: Add premium field to User model
class User(Base, UserMixin):
    # ... existing fields ...
    premium = Column(Boolean, default=False)  # New field
```

**Step 2: Commit changes and rebuild/push Docker image**

```bash
# Build and push new image with updated models
docker build --platform linux/amd64 -t chess-elegante:v1.0.1 .
docker tag chess-elegante:v1.0.1 $REPO_URI:v1.0.1
docker push $REPO_URI:v1.0.1

# Update task definition with new image version
# ... update ecs-task-definition.json ...
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Update service
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --task-definition chess-elegante:2 \
  --force-new-deployment
```

**Step 3: Generate and apply migration**

```bash
# Connect to running task
TASK_ARN=$(aws ecs list-tasks \
  --cluster chess-elegante-cluster \
  --service-name chess-elegante-service \
  --query 'taskArns[0]' \
  --output text)

aws ecs execute-command \
  --cluster chess-elegante-cluster \
  --task $TASK_ARN \
  --container chess-elegante-app \
  --interactive \
  --command "/bin/bash"

# Inside container:
# Apply migrations
flask db upgrade

# Verify changes
psql $DATABASE_URL -c "\d users"
```

**Alternative: Run migration as one-off task**

```bash
# After updating and deploying new image with model changes
aws ecs run-task \
  --cluster chess-elegante-cluster \
  --task-definition chess-elegante:2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"chess-elegante-app","command":["flask","db","upgrade"]}]}'
```

See [Migrations Guide](MIGRATIONS.md) for detailed migration workflow.

### 10.3 Migration Best Practices

**Important considerations:**

1. **Always review generated migrations** before applying them
2. **Backup database** before running migrations in production
3. **Test migrations** in a staging environment first
4. **Use transactions** (Flask-Migrate does this by default)
5. **Keep migration history** in version control (commit `migrations/versions/` directory)

**Common migration scenarios:**

```bash
# Add a new column with default value
flask db migrate -m "Add email_verified column"

# Rename a column (autogenerate might not detect this, manual migration needed)
flask db revision -m "Rename user_name to username"

# Add index
flask db migrate -m "Add index on email column"

# Rollback last migration (if needed)
flask db downgrade

# Check current migration version
flask db current

# View migration history
flask db history
```

For more details, see [Migrations Guide](MIGRATIONS.md).

---

## Step 11: Monitor and Scale

### 11.1 View Logs

```bash
# Stream logs
aws logs tail /ecs/chess-elegante --follow

# Filter logs
aws logs filter-log-events \
  --log-group-name /ecs/chess-elegante \
  --filter-pattern "ERROR"
```

### 11.2 Configure Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/chess-elegante-cluster/chess-elegante-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/chess-elegante-cluster/chess-elegante-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name chess-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

**scaling-policy.json:**
```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

---

## Cost Estimate

**Monthly costs (us-east-1):**

| Service | Configuration | Cost |
|---------|--------------|------|
| ECS Fargate | 1 task (0.5 vCPU, 1GB) running 24/7 | ~$12.50 |
| RDS PostgreSQL | db.t4g.micro, 20GB gp3, single-AZ | ~$14 |
| Application Load Balancer | Standard ALB | ~$16 |
| CloudWatch Logs | 5GB ingestion, 1 month retention | ~$3 |
| Secrets Manager | 8 secrets | ~$3.20 |
| ECR | 5GB storage | ~$0.50 |
| Route 53 | 1 hosted zone (optional) | ~$0.50 |
| ACM Certificate | SSL/TLS certificate | Free |
| Data Transfer | 20GB outbound | ~$2 |
| **Total** | Without Route 53 | **~$51/month** |
| **Total** | With Route 53 | **~$52/month** |

### Cost Optimization Options

- **Fargate Spot**: Save ~70% on compute (but tasks can be interrupted)
- **Aurora Serverless v2**: Pay per use, good for variable traffic
- **Reserved RDS**: Commit 1 year for ~30% discount
- **Multi-AZ Setup**: Add ~$14/month for RDS Multi-AZ + additional Fargate tasks for high availability

---

## Troubleshooting

### Task fails to start

```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster chess-elegante-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].stoppedReason'

# Check CloudWatch logs
aws logs tail /ecs/chess-elegante --follow
```

### Health check failures

```bash
# Check target health
aws elbv2 describe-target-health --target-group-arn $TG_ARN

# Common issues:
# - Security group not allowing ALB -> ECS traffic
# - Health check path incorrect
# - App not binding to 0.0.0.0:5000
```

### Database connection issues

```bash
# Test connection from ECS task
aws ecs execute-command ... --command "/bin/bash"
apt-get update && apt-get install -y postgresql-client
psql -h your-rds-endpoint -U chess -d chess_elegante
```

### Secrets not loading

```bash
# Verify IAM role has Secrets Manager permissions
# Check secret ARNs in task definition match actual secrets
aws secretsmanager get-secret-value --secret-id chess-elegante/DATABASE_URL
```

---

## Rolling Updates

```bash
# Update image in ECR
docker build -t chess-elegante:v1.0.1 .
docker tag chess-elegante:v1.0.1 $REPO_URI:v1.0.1
docker push $REPO_URI:v1.0.1

# Update task definition with new image
# ... update ecs-task-definition.json ...
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Update service
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --task-definition chess-elegante:2
```

---

## Security Checklist

- [ ] Secrets stored in Secrets Manager (not environment variables)
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Security groups follow least privilege (ALB → ECS, ECS → RDS only)
- [ ] RDS encryption at rest enabled
- [ ] CloudWatch logs enabled
- [ ] IAM roles follow least privilege
- [ ] Container runs as non-root user (update Dockerfile)
- [ ] VPC Flow Logs enabled (optional)
- [ ] AWS WAF on ALB (optional, extra cost)

---

## Next Steps

1. Test local Docker setup with `docker-compose up`
2. Create VPC with public subnets
3. Set up RDS PostgreSQL instance
4. Create ECR repository and push image
5. Store all secrets in Secrets Manager
6. Create ECS cluster and task definition
7. Request and validate ACM SSL certificate
8. Set up Application Load Balancer with HTTPS
9. Create ECS service with ALB integration
10. Configure DNS (optional)
11. Update OAuth redirect URIs
12. Initialize database and apply Flask-Migrate migrations
13. Test production deployment

## Database Schema Updates Workflow

When you need to update the database schema:

1. **Update models locally** - Add/modify fields in `models.py`
2. **Test locally** - Run Flask-Migrate migrations on local database (`flask db migrate` and `flask db upgrade`)
3. **Commit migrations** - Add `migrations/versions/*.py` to git
4. **Build and push image** - Include updated models and migrations
5. **Deploy to ECS** - Update task definition and service
6. **Run migration** - Connect via ECS Exec and run `flask db upgrade`

See [Migrations Guide](MIGRATIONS.md) for detailed instructions.

For automated provisioning, consider using Infrastructure as Code tools like Terraform or CloudFormation.
