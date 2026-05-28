# Database Setup Guide

This guide covers setting up PostgreSQL for Chess Elegante locally and for AWS deployment.

---

## Local Development Setup

### Option 1: Using Docker (Recommended)

**Prerequisites:**
- Docker installed on your machine

**Steps:**

1. **Create a `docker-compose.yml` file** (already included in project root):

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: chess_elegante_db
    environment:
      POSTGRES_USER: chess
      POSTGRES_PASSWORD: chess
      POSTGRES_DB: chess_elegante
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chess -d chess_elegante"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

2. **Start PostgreSQL:**

```bash
docker-compose up -d
```

3. **Verify it's running:**

```bash
docker ps
# Should show chess_elegante_db container running on port 5432

# Check logs
docker-compose logs postgres
```

4. **Connect to PostgreSQL (optional):**

```bash
# Using psql in the container
docker exec -it chess_elegante_db psql -U chess -d chess_elegante

# Or using a GUI tool like pgAdmin/DBeaver
# Host: localhost
# Port: 5432
# Database: chess_elegante
# Username: chess
# Password: chess
```

5. **Stop PostgreSQL when done:**

```bash
docker-compose down
# Or to also remove data volumes:
docker-compose down -v
```

---

## Application Setup

### 1. Install Python Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and update the `DATABASE_URL`:

```env
# For local Docker setup (default)
DATABASE_URL=postgresql://chess:chess@localhost:5432/chess_elegante

# For native PostgreSQL with different credentials
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/chess_elegante
```

### 3. Initialize Database and Migrations

Set up Flask-Migrate for database schema management:

```bash
# Initialize Flask-Migrate (first time only)
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migration to create tables
flask db upgrade
```

See [Migrations Guide](MIGRATIONS.md) for detailed instructions.

### 4. Updating Schema (Adding New Fields)

When you add new fields to your models:

```bash
# 1. Update models.py with new fields
# 2. Generate migration
flask db migrate -m "Add new field description"

# 3. Review the migration in migrations/versions/
# 4. Apply the migration
flask db upgrade
```

**Example: Adding a new field**

```python
# models.py - Add new field to User model
class User(Base, UserMixin):
    # ... existing fields ...
    premium = Column(Boolean, default=False)  # New field
```

```bash
# Generate and apply migration
flask db migrate -m "Add premium field to users"
flask db upgrade
```

For more migration scenarios, see [Migrations Guide](MIGRATIONS.md).

### 5. Run the Application

```bash
python app.py
```

The application should now be running at http://localhost:5000

---

## Verifying the Setup

### Check Database Connection

```bash
# Using Docker
docker exec -it chess_elegante_db psql -U chess -d chess_elegante -c "\dt"

# Using native psql
psql -U chess -d chess_elegante -c "\dt"
```

You should see tables:
- `games`
- `pgns`

### Check Data

```sql
-- Connect to database
psql -U chess -d chess_elegante

-- Check games
SELECT game_id, status, move_count FROM games ORDER BY updated_at DESC LIMIT 5;

-- Check PGNs
SELECT pgn_id, name, move_count FROM pgns ORDER BY updated_at DESC LIMIT 5;

-- Exit
\q
```

---

## AWS Deployment (RDS PostgreSQL)

### 1. Create RDS PostgreSQL Instance

**Via AWS Console:**

1. Go to RDS Console
2. Click "Create database"
3. **Engine options:**
   - Engine type: PostgreSQL
   - Version: PostgreSQL 15.x
4. **Templates:**
   - For production: Production
   - For testing: Free tier (db.t3.micro or db.t4g.micro)
5. **Settings:**
   - DB instance identifier: `chess-elegante-db`
   - Master username: `chess`
   - Master password: (choose a strong password)
6. **Instance configuration:**
   - Free tier: db.t3.micro or db.t4g.micro
   - Production: db.t4g.small or larger
7. **Storage:**
   - Storage type: General Purpose SSD (gp3)
   - Allocated storage: 20 GB (free tier) or more
   - Enable storage autoscaling
8. **Connectivity:**
   - VPC: Default VPC or your custom VPC
   - Public access: Yes (for testing) or No (for production with VPN/bastion)
   - VPC security group: Create new or select existing
9. **Database authentication:**
   - Password authentication
10. **Additional configuration:**
    - Initial database name: `chess_elegante`
    - Backup retention: 7 days (recommended)
    - Enable encryption (recommended)

**Via AWS CLI:**

```bash
aws rds create-db-instance \
    --db-instance-identifier chess-elegante-db \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15.5 \
    --master-username chess \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --storage-type gp3 \
    --db-name chess_elegante \
    --backup-retention-period 7 \
    --no-multi-az \
    --publicly-accessible
```

### 2. Configure Security Group

Allow inbound traffic on port 5432:

1. Go to RDS instance details
2. Click on the VPC security group
3. Add inbound rule:
   - Type: PostgreSQL
   - Port: 5432
   - Source: Your IP (for testing) or your EC2 security group (for production)

### 3. Get RDS Endpoint

After creation (takes ~5-10 minutes):

```bash
aws rds describe-db-instances \
    --db-instance-identifier chess-elegante-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

Example endpoint: `chess-elegante-db.c1234abcd.us-east-1.rds.amazonaws.com`

### 4. Update Application Configuration

On your EC2 instance or container, set the environment variable:

```bash
export DATABASE_URL=postgresql://chess:YOUR_PASSWORD@chess-elegante-db.c1234abcd.us-east-1.rds.amazonaws.com:5432/chess_elegante
```

Or in your `.env` file:

```env
DATABASE_URL=postgresql://chess:YOUR_PASSWORD@your-rds-endpoint.region.rds.amazonaws.com:5432/chess_elegante
```

### 5. Initialize Database and Run Migrations

**Option A: Using ECS Exec (Recommended)**

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
# Initialize database and apply migrations
flask db upgrade
```

**Option B: Run as one-off task**

```bash
# Run migrations as one-off task
aws ecs run-task \
  --cluster chess-elegante-cluster \
  --task-definition chess-elegante \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"chess-elegante-app","command":["flask","db","upgrade"]}]}'
```

See [Migrations Guide](MIGRATIONS.md) for more details on database migrations.

### 6. Monitor and Maintain

**View logs:**
```bash
aws rds describe-db-log-files --db-instance-identifier chess-elegante-db
```

**Create snapshot:**
```bash
aws rds create-db-snapshot \
    --db-snapshot-identifier chess-elegante-backup-$(date +%Y%m%d) \
    --db-instance-identifier chess-elegante-db
```

**Modify instance (scale up/down):**
```bash
aws rds modify-db-instance \
    --db-instance-identifier chess-elegante-db \
    --db-instance-class db.t4g.small \
    --apply-immediately
```

---

## Troubleshooting

### Connection Refused

**Docker:**
```bash
# Check if container is running
docker ps

# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

**Native:**
```bash
# macOS
brew services restart postgresql@15

# Linux
sudo systemctl restart postgresql
```

### Authentication Failed

Check your credentials in `.env`:
```bash
# Test connection
psql "postgresql://chess:chess@localhost:5432/chess_elegante"
```

### Port Already in Use

```bash
# Find process using port 5432
lsof -i :5432
# or
sudo netstat -tulpn | grep 5432

# Kill the process or change port in docker-compose.yml
```

### RDS Connection Timeout (AWS)

1. Check security group allows your IP on port 5432
2. Check that "Publicly accessible" is enabled (if connecting from outside AWS)
3. Verify your VPC/subnet configuration
4. Test connection:
```bash
psql -h your-endpoint.rds.amazonaws.com -U chess -d chess_elegante
```

---

## Cost Estimation (AWS RDS)

**Free Tier (first 12 months):**
- 750 hours/month of db.t3.micro or db.t4g.micro
- 20 GB storage
- 20 GB backup storage
- **Cost: $0** (within limits)

**After Free Tier:**
- db.t4g.micro: ~$13/month
- db.t4g.small: ~$26/month
- Storage (gp3): $0.10/GB/month (20GB = $2/month)
- Backup storage: $0.095/GB/month (first 20GB free)
- **Total: $15-30/month** (small app)

**Production scale:**
- db.t4g.medium: ~$52/month
- db.m6g.large: ~$130/month
- Multi-AZ doubles cost but adds high availability

---

## Backup and Recovery

### Local Backup

```bash
# Dump database
docker exec chess_elegante_db pg_dump -U chess chess_elegante > backup.sql

# Restore
docker exec -i chess_elegante_db psql -U chess chess_elegante < backup.sql
```

### RDS Automated Backups

RDS automatically creates daily snapshots during the backup window. Configure:

```bash
aws rds modify-db-instance \
    --db-instance-identifier chess-elegante-db \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00"
```

### Point-in-Time Recovery

```bash
# Restore to specific time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier chess-elegante-db \
    --target-db-instance-identifier chess-elegante-db-restored \
    --restore-time 2025-01-15T10:00:00Z
```

---

## Next Steps

1. ✅ Set up local PostgreSQL
2. ✅ Install dependencies
3. ✅ Configure `.env`
4. ✅ Run migration script
5. ✅ Start application
6. 🚀 Deploy to AWS (optional)

For questions or issues, check the logs in `logs/app.log` or enable debug mode in `app.py`.
