# GitHub Actions CI/CD Setup

This repository includes three automated workflows for continuous integration and deployment.

## Workflows

### 1. **CI - Build and Test** (`.github/workflows/ci.yml`)
**Triggers:** Pull requests and pushes to non-main branches

**Actions:**
- Builds Docker image
- Verifies image can start
- Runs basic smoke tests

**Purpose:** Validates changes before merging

---

### 2. **Build and Deploy to AWS ECS** (`.github/workflows/deploy.yml`)
**Triggers:**
- Pushes to `main` or `master` branch
- Manual dispatch via GitHub Actions UI

**Actions:**
1. Builds production Docker image
2. Pushes to Amazon ECR with commit SHA tag and `:latest` tag
3. Updates ECS task definition with new image
4. Deploys to ECS Fargate cluster
5. Waits for deployment stability

**Purpose:** Automated production deployment on every merge to main

---

### 3. **Run Database Migrations** (`.github/workflows/run-migrations.yml`)
**Triggers:** Manual only (workflow_dispatch)

**Actions:**
1. Finds running ECS task
2. Connects via ECS Exec
3. Runs Alembic migrations (`alembic revision --autogenerate` + `alembic upgrade head`)

**Purpose:** Safe, on-demand database schema updates

---

## Initial Setup

### Step 1: Configure AWS Credentials

Add these secrets to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key with ECS/ECR permissions | Create IAM user in AWS Console |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Same IAM user |

**IAM Policy Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService",
        "ecs:ExecuteCommand",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 2: Enable ECS Exec (for migrations)

```bash
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --enable-execute-command
```

### Step 3: Verify Configuration

Update the environment variables in `.github/workflows/deploy.yml` if your setup differs:

```yaml
env:
  AWS_REGION: us-east-1                          # Your AWS region
  ECR_REPOSITORY: chess-elegante                 # Your ECR repository name
  ECS_CLUSTER: chess-elegante-cluster            # Your ECS cluster name
  ECS_SERVICE: chess-elegante-service            # Your ECS service name
  ECS_TASK_DEFINITION: ecs-task-definition.json  # Path to task definition
  CONTAINER_NAME: chess-elegante-app             # Container name in task def
```

---

## Usage

### Automatic Deployment

1. **Push to main/master:**
   ```bash
   git checkout main
   git pull
   git merge feature-branch
   git push origin main
   ```

2. **GitHub Actions will automatically:**
   - Build Docker image
   - Push to ECR
   - Deploy to ECS
   - Wait for service stability

3. **Monitor deployment:**
   - Go to **Actions** tab in GitHub
   - Click on the running workflow
   - View real-time logs

### Manual Deployment

1. Go to **Actions** → **Build and Deploy to AWS ECS**
2. Click **Run workflow**
3. Select branch (usually `main`)
4. Click **Run workflow**

### Running Database Migrations

**When to run:**
- After updating `models.py` and deploying new code
- When adding/modifying database fields

**Steps:**
1. Update `models.py` locally
2. Commit and push changes
3. Wait for deployment to complete
4. Go to **Actions** → **Run Database Migrations**
5. Click **Run workflow**
6. Enter migration description (e.g., "Add premium field to users")
7. Click **Run workflow**

**What it does:**
- Connects to your running ECS task
- Generates Alembic migration from model changes
- Applies migration to production database

---

## Monitoring and Troubleshooting

### View Deployment Logs

**GitHub Actions:**
- Go to **Actions** tab
- Click on workflow run
- Expand job steps to see detailed logs

**AWS CloudWatch:**
```bash
aws logs tail /ecs/chess-elegante --follow
```

### Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster chess-elegante-cluster \
  --services chess-elegante-service
```

### Rollback Deployment

If a deployment fails or introduces issues:

```bash
# List task definitions
aws ecs list-task-definitions --family-prefix chess-elegante

# Update service to previous version
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --task-definition chess-elegante:PREVIOUS_VERSION
```

Or use **Manual Deployment** workflow with an older commit SHA.

---

## Development Workflow

### Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

**CI workflow runs automatically:**
- Builds Docker image
- Runs tests
- Reports status on PR

### Merge to Production

```bash
# Create pull request on GitHub
# Once approved and CI passes:
git checkout main
git merge feature/new-feature
git push origin main
```

**Deploy workflow runs automatically:**
- Builds production image
- Pushes to ECR
- Deploys to ECS

### Database Schema Updates

```bash
# 1. Update models.py
# 2. Commit and merge to main
git add models.py
git commit -m "Add new user fields"
git push origin main

# 3. Wait for deployment to finish

# 4. Run migrations via GitHub Actions UI
# Actions → Run Database Migrations → Run workflow
```

---

## Advanced: Adding Tests

To add automated testing before deployment, update `.github/workflows/ci.yml`:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'

- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install pytest pytest-cov

- name: Run tests
  run: |
    pytest tests/ -v --cov=.
```

Then create tests in `tests/` directory:
```bash
mkdir tests
touch tests/test_app.py
```

---

## Cost Optimization

**GitHub Actions free tier:**
- 2,000 minutes/month for private repos
- Unlimited for public repos

**Typical usage:**
- Build + Deploy: ~3-5 minutes per run
- Migrations: ~1 minute per run

**To reduce CI time:**
1. Use Docker layer caching
2. Run tests only on PRs, not on main
3. Use smaller runner for builds

---

## Security Best Practices

✅ **DO:**
- Store all credentials in GitHub Secrets
- Use IAM roles with least privilege
- Review deployments before merging
- Enable branch protection on `main`

❌ **DON'T:**
- Commit AWS credentials to code
- Disable security checks
- Skip PR reviews for deployments
- Use overly permissive IAM policies

---

## Next Steps

1. ✅ Add GitHub Secrets for AWS credentials
2. ✅ Enable ECS Exec on service
3. ✅ Verify workflow environment variables
4. ✅ Test deployment with a small change
5. ✅ Set up branch protection rules
6. ✅ Add Slack/email notifications (optional)

---

## Troubleshooting Common Issues

### "No running tasks found" (migrations)

**Solution:** Ensure ECS service has at least 1 running task:
```bash
aws ecs update-service \
  --cluster chess-elegante-cluster \
  --service chess-elegante-service \
  --desired-count 1
```

### "Permission denied" on ECR push

**Solution:** Verify IAM user has `ecr:PutImage` permission

### Deployment stuck "Waiting for stability"

**Solution:** Check ECS task health:
```bash
aws ecs describe-services \
  --cluster chess-elegante-cluster \
  --services chess-elegante-service
```

Common causes:
- Health check failing (check `/` endpoint returns 200)
- Not enough memory/CPU (check CloudWatch logs)
- Database connection failing (verify secrets in task def)

---

## Support

- **GitHub Actions docs:** https://docs.github.com/en/actions
- **AWS ECS docs:** https://docs.aws.amazon.com/ecs/
- **Project README:** See main README.md for application setup
