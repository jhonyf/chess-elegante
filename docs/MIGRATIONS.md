# Database Migrations Guide

Chess Elegante uses **Flask-Migrate** for managing database schema changes safely and trackably.

---

## Quick Start

### Initial Setup (First Time)

```bash
# 1. Initialize Flask-Migrate
flask db init

# 2. Create and apply first migration
flask db migrate -m "Initial migration"
flask db upgrade
```

### Adding a New Field (Most Common)

```bash
# 1. Edit models.py and add your field
# Example: Add 'premium' field to User model

# 2. Generate migration
flask db migrate -m "Add premium field to users"

# 3. Review the generated migration file
cat migrations/versions/[latest_file].py

# 4. Apply migration
flask db upgrade

# 5. Verify
psql $DATABASE_URL -c "\d users"
```

---

## Why Flask-Migrate?

**Problem:** `Base.metadata.create_all(engine)` only creates missing tables. It **cannot**:
- Add new columns to existing tables
- Modify column types
- Add indexes or constraints
- Rename columns

**Solution:** Flask-Migrate (built on Alembic) generates ALTER statements that safely update your schema while preserving data, with Flask-native commands.

---

## Common Commands

```bash
# Generate migration (auto-detect changes from models.py)
flask db migrate -m "Description"

# Apply all pending migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# Check current version
flask db current

# View migration history
flask db history

# Generate SQL without applying (for review)
flask db upgrade --sql
```

---

## Common Scenarios

### Add Column with Default Value

```python
# models.py
class Game(Base):
    # ...
    difficulty = Column(String(20), default='normal')
```

```bash
flask db migrate -m "Add difficulty to games"
flask db upgrade
```

### Add Column with NOT NULL Constraint

When adding a NOT NULL column to existing table with data:

```python
# Manual migration required
def upgrade():
    # Step 1: Add column as nullable
    op.add_column('users', sa.Column('username', sa.String(50), nullable=True))

    # Step 2: Populate with default values
    op.execute("UPDATE users SET username = email WHERE username IS NULL")

    # Step 3: Make it NOT NULL
    op.alter_column('users', 'username', nullable=False)
```

### Rename Column

Flask-Migrate might not detect renames, so create manual migration:

```bash
flask db revision -m "Rename ai_level to difficulty"
```

```python
def upgrade():
    op.alter_column('games', 'ai_level', new_column_name='difficulty')

def downgrade():
    op.alter_column('games', 'difficulty', new_column_name='ai_level')
```

### Add Index

```python
# models.py
class Game(Base):
    # ...
    status = Column(String(20), nullable=False, index=True)  # ← Added index=True
```

```bash
flask db migrate -m "Add index on game status"
flask db upgrade
```

---

## Production Deployment

### Local Development Workflow

```bash
# 1. Update models.py with new fields
# 2. Generate migration
flask db migrate -m "Add new feature"

# 3. Review migration file
cat migrations/versions/*.py

# 4. Test locally
flask db upgrade

# 5. Test application
python app.py

# 6. Commit to git
git add migrations/versions/*.py models.py
git commit -m "Add new feature with migration"
```

### AWS ECS Deployment

**Option 1: Manual via ECS Exec**

```bash
# Get running task
TASK_ARN=$(aws ecs list-tasks \
  --cluster chess-elegante-cluster \
  --service-name chess-elegante-service \
  --query 'taskArns[0]' \
  --output text)

# Connect to container
aws ecs execute-command \
  --cluster chess-elegante-cluster \
  --task $TASK_ARN \
  --container chess-elegante-app \
  --interactive \
  --command "/bin/bash"

# Inside container: Run migration
flask db upgrade

# Verify
psql $DATABASE_URL -c "\d users"
```

**Option 2: GitHub Actions Workflow**

Use the "Run Database Migrations" workflow:
1. Go to **Actions** → **Run Database Migrations**
2. Click **Run workflow**
3. Enter migration description
4. Click **Run workflow**

See [CI/CD Setup](.github/SETUP_CI.md) for details.

---

## Troubleshooting

### Migration Out of Sync

```bash
# Check current version
flask db current

# If database is ahead of codebase, downgrade
flask db downgrade abc123

# If codebase is ahead, upgrade
flask db upgrade

# If completely out of sync, stamp to specific version
flask db stamp abc123
```

### Autogenerate Not Detecting Changes

```bash
# Ensure models are imported in migrations/env.py
# Check that target_metadata = Base.metadata is set

# Create manual migration
flask db revision -m "Manual migration"
```

### Migration Failed Partially

```bash
# Check what was applied
flask db current

# Manually fix database if needed
psql $DATABASE_URL

# Mark migration as complete (if you fixed it manually)
flask db stamp head
```

---

## Best Practices

✅ **DO:**
- Review all auto-generated migrations before applying
- Test migrations locally first
- Commit migration files to git
- Backup database before production migrations
- Use descriptive migration names
- One logical change per migration

❌ **DON'T:**
- Use `Base.metadata.create_all()` after initial setup
- Edit applied migration files
- Skip reviewing auto-generated migrations
- Apply migrations without testing
- Forget to commit migration files

---

## File Structure

```
chess-elegante/
├── models.py                    # Database models (edit this)
├── migrations/
│   ├── versions/               # Migration files (commit these!)
│   │   ├── abc123_initial.py
│   │   └── def456_add_field.py
│   └── env.py                  # Flask-Migrate config
└── app.py                      # Flask app with Migrate(app, db)
```

---

## Additional Resources

- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Database Setup Guide](DATABASE_SETUP.md)
- [AWS Deployment Guide](AWS_DEPLOYMENT.md)
