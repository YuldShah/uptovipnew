# PostgreSQL Database Setup for YTDLBot

## 🐘 PostgreSQL Setup Commands

### Method 1: Using PostgreSQL Command Line (psql)

```bash
# Connect to PostgreSQL as superuser (usually postgres)
sudo -u postgres psql

# Or on Windows with PostgreSQL installed:
psql -U postgres
```

Then run these SQL commands:

```sql
-- Create the database user
CREATE USER ytdlbot WITH PASSWORD 'ytdlbot';

-- Create the database
CREATE DATABASE ytdlbot OWNER ytdlbot;

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE ytdlbot TO ytdlbot;

-- Connect to the ytdlbot database
\c ytdlbot

-- Grant privileges on the public schema
GRANT ALL ON SCHEMA public TO ytdlbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ytdlbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ytdlbot;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ytdlbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ytdlbot;

-- Exit psql
\q
```

### Method 2: Using Command Line Utilities

```bash
# Create the user (will prompt for password)
sudo -u postgres createuser -P ytdlbot

# Create the database with the user as owner
sudo -u postgres createdb -O ytdlbot ytdlbot

# Grant privileges (connect to database first)
sudo -u postgres psql ytdlbot -c "GRANT ALL ON SCHEMA public TO ytdlbot;"
sudo -u postgres psql ytdlbot -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ytdlbot;"
sudo -u postgres psql ytdlbot -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ytdlbot;"
```

### Method 3: For Production with Custom Password

```sql
-- Connect as superuser
sudo -u postgres psql

-- Create user with a strong password
CREATE USER ytdlbot WITH PASSWORD 'your_secure_password_here';

-- Create database
CREATE DATABASE ytdlbot OWNER ytdlbot;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ytdlbot TO ytdlbot;

-- Connect to the database
\c ytdlbot

-- Set up schema permissions
GRANT ALL ON SCHEMA public TO ytdlbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ytdlbot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ytdlbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ytdlbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ytdlbot;

-- Exit
\q
```

## 🔗 Connection String Examples

After creating the database, use these connection strings in your `.env` file:

### For Local PostgreSQL:
```bash
# Default setup (user: ytdlbot, password: ytdlbot)
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@localhost:5432/ytdlbot

# Custom password
DB_DSN=postgresql+psycopg2://ytdlbot:your_secure_password@localhost:5432/ytdlbot

# Custom port
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@localhost:5433/ytdlbot
```

### For Docker PostgreSQL:
```bash
# Docker Compose (uses service name as hostname)
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@postgres:5432/ytdlbot

# Docker with custom network
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@db_container_name:5432/ytdlbot
```

### For Remote PostgreSQL:
```bash
# Remote server
DB_DSN=postgresql+psycopg2://ytdlbot:password@your-server.com:5432/ytdlbot

# SSL enabled
DB_DSN=postgresql+psycopg2://ytdlbot:password@your-server.com:5432/ytdlbot?sslmode=require
```

## 🐳 Docker Compose PostgreSQL Setup

If you're using Docker, add this to your `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ytdlbot
      POSTGRES_PASSWORD: ytdlbot
      POSTGRES_DB: ytdlbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  ytdlbot:
    build: .
    depends_on:
      - postgres
    env_file:
      - .env
    restart: unless-stopped

volumes:
  postgres_data:
```

## ✅ Verify Database Setup

Test your database connection:

```bash
# Test connection
psql -h localhost -U ytdlbot -d ytdlbot

# Or with connection string
psql "postgresql://ytdlbot:ytdlbot@localhost:5432/ytdlbot"
```

If successful, you should see:
```
ytdlbot=> 
```

## 🔒 Security Best Practices

### For Production:

1. **Use strong passwords:**
```sql
CREATE USER ytdlbot WITH PASSWORD 'ComplexPassword123!@#';
```

2. **Limit connections:**
```sql
ALTER USER ytdlbot CONNECTION LIMIT 10;
```

3. **Create dedicated database:**
```sql
CREATE DATABASE ytdlbot_prod OWNER ytdlbot;
```

4. **Use SSL connections:**
```bash
DB_DSN=postgresql+psycopg2://ytdlbot:password@host:5432/ytdlbot?sslmode=require
```

## 🚨 Troubleshooting

### Common Issues:

1. **"role does not exist"**
   - Make sure you created the user first
   - Check spelling of username

2. **"database does not exist"**
   - Create database with correct name
   - Verify you're connecting to right server

3. **"permission denied"**
   - Grant proper privileges as shown above
   - Check if user owns the database

4. **Connection refused**
   - Check if PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify port (default 5432)
   - Check firewall settings

### Check PostgreSQL Status:
```bash
# Linux
sudo systemctl status postgresql

# Check if listening
sudo netstat -tlnp | grep 5432

# View logs
sudo journalctl -u postgresql
```

Your PostgreSQL database is now ready for YTDLBot! 🎉
