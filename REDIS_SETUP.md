# Redis Setup Guide for YTDLBot on VPS

## 🚀 Redis Installation on VPS

### Method 1: Ubuntu/Debian (Recommended)

```bash
# Update package list
sudo apt update

# Install Redis
sudo apt install redis-server -y

# Start Redis service
sudo systemctl start redis-server

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Check Redis status
sudo systemctl status redis-server
```

### Method 2: CentOS/RHEL/Rocky Linux

```bash
# Install EPEL repository
sudo dnf install epel-release -y

# Install Redis
sudo dnf install redis -y

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis

# Check status
sudo systemctl status redis
```

### Method 3: Using Docker (Alternative)

```bash
# Pull Redis image
docker pull redis:7-alpine

# Run Redis container
docker run -d \
  --name redis \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:7-alpine

# Check if running
docker ps | grep redis
```

## ⚙️ Redis Configuration

### 1. Basic Security Configuration

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Or on some systems:
sudo nano /etc/redis.conf
```

**Important settings to change:**

```bash
# Bind to localhost only (security)
bind 127.0.0.1

# Set a password (recommended)
requirepass your_secure_password_here

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Set memory limit (optional, e.g., 256MB)
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### 2. Restart Redis after configuration

```bash
sudo systemctl restart redis-server
# OR
sudo systemctl restart redis
```

## 🔐 Security Best Practices

### 1. Firewall Configuration

```bash
# Only allow local connections (recommended for bot)
sudo ufw allow from 127.0.0.1 to any port 6379

# Or if Redis is on different server:
sudo ufw allow from YOUR_BOT_SERVER_IP to any port 6379
```

### 2. Create Redis User (Optional)

```bash
# Connect to Redis
redis-cli

# Create user for your bot
AUTH your_secure_password_here
ACL SETUSER ytdlbot on >bot_password_here ~* +@all

# Save ACL
ACL SAVE
```

## 🧪 Test Redis Installation

### 1. Basic Connection Test

```bash
# Test Redis connection
redis-cli ping

# Should return: PONG
```

### 2. Test with Password (if set)

```bash
# Connect with password
redis-cli -a your_secure_password_here ping

# Should return: PONG
```

### 3. Test Basic Operations

```bash
redis-cli -a your_password_here
127.0.0.1:6379> SET test "Hello Redis"
127.0.0.1:6379> GET test
127.0.0.1:6379> DEL test
127.0.0.1:6379> EXIT
```

## 🔧 YTDLBot Configuration

### For Local Redis (Same Server)

Update your `.env` file:

```bash
# Basic setup (no password)
REDIS_HOST=localhost:6379

# With password
REDIS_HOST=redis://:your_password@localhost:6379

# Alternative format
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
```

### For Remote Redis

```bash
# Remote Redis server
REDIS_HOST=redis://:password@your-redis-server.com:6379

# With SSL (if configured)
REDIS_HOST=rediss://:password@your-redis-server.com:6380
```

### For Docker Setup

If using Docker Compose, add Redis service:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass your_secure_password
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    restart: unless-stopped

  ytdlbot:
    build: .
    depends_on:
      - redis
      - postgres
    env_file:
      - .env
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

Then in your `.env`:

```bash
REDIS_HOST=redis://redis:6379
# OR with password:
REDIS_HOST=redis://:your_password@redis:6379
```

## 📊 Redis Monitoring

### 1. Check Redis Performance

```bash
# Monitor Redis in real-time
redis-cli monitor

# Get Redis info
redis-cli info

# Check memory usage
redis-cli info memory

# See connected clients
redis-cli info clients
```

### 2. Redis Logs

```bash
# View Redis logs
sudo journalctl -u redis-server -f

# Or check log file
sudo tail -f /var/log/redis/redis-server.log
```

## 🚨 Troubleshooting

### Common Issues:

1. **Connection Refused**
   ```bash
   # Check if Redis is running
   sudo systemctl status redis-server
   
   # Check port
   sudo netstat -tlnp | grep 6379
   
   # Restart Redis
   sudo systemctl restart redis-server
   ```

2. **Permission Denied**
   ```bash
   # Check Redis user permissions
   sudo chown redis:redis /var/lib/redis
   sudo chmod 755 /var/lib/redis
   ```

3. **Memory Issues**
   ```bash
   # Check available memory
   free -h
   
   # Set memory limit in redis.conf
   maxmemory 512mb
   ```

4. **Authentication Failed**
   ```bash
   # Check password in config
   sudo grep requirepass /etc/redis/redis.conf
   
   # Test with correct password
   redis-cli -a your_password ping
   ```

## 🔄 Without Redis (Fallback)

If you don't want to install Redis, your bot will automatically use fakeredis (in-memory):

```bash
# In your .env file, leave Redis empty or comment out
# REDIS_HOST=

# The bot will use fakeredis automatically
```

**Note:** Without Redis, caching data will be lost when the bot restarts.

## 🎯 Recommended Setup for Production

```bash
# 1. Install Redis
sudo apt update && sudo apt install redis-server -y

# 2. Configure security
sudo nano /etc/redis/redis.conf
# Add: requirepass your_secure_password

# 3. Restart Redis
sudo systemctl restart redis-server

# 4. Test connection
redis-cli -a your_secure_password ping

# 5. Update bot .env
echo "REDIS_HOST=redis://:your_secure_password@localhost:6379" >> .env

# 6. Restart your bot
docker-compose restart ytdlbot
```

Your Redis is now ready for YTDLBot! 🎉

## Performance Tips

1. **Memory Management**: Set appropriate `maxmemory` limit
2. **Persistence**: Enable RDB snapshots for data backup
3. **Monitoring**: Use `redis-cli info` to monitor performance
4. **Security**: Always use passwords in production
5. **Firewall**: Restrict access to Redis port

Redis will significantly improve your bot's performance by caching user states, download sessions, and other temporary data! 🚀
