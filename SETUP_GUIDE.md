# YTDLBot Setup Guide - Private Use Edition

## 🚀 Quick Setup Guide

### 1. **Get Telegram API Credentials**

#### APP_ID and APP_HASH
1. Go to [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your phone number
3. Click "API Development tools"
4. Create a new application:
   - **App title**: `YTDLBot Private`
   - **Short name**: `ytdlbot`
   - **Platform**: Choose any (Desktop recommended)
5. Copy the **App api_id** → This is your `APP_ID`
6. Copy the **App api_hash** → This is your `APP_HASH`

#### BOT_TOKEN
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name: `My YouTube Downloader Bot`
4. Choose a username: `your_ytdl_bot` (must end with 'bot')
5. Copy the token (format: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`)

### 2. **Get Admin User IDs**

#### ADMIN_IDS (Bot Administrators)
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID (a number like `123456789`)
3. Add other admin user IDs separated by commas: `123456789,987654321`
4. **Admin users have full control:**
   - Can use `/admin` command
   - Can manage channel requirements
   - Can whitelist/ban users
   - Have unlimited access to bot features

## 👥 **Two Types of Users**

### 🔧 **Admin Users**
- Listed in `ADMIN_IDS` environment variable
- Full control over bot settings and access control
- Can manage required channels and user permissions
- Always have access regardless of other restrictions

### 👤 **Regular Users** 
- All users not listed in `ADMIN_IDS`
- Subject to access control rules:
  - Must meet channel membership requirements (if any)
  - Can be manually whitelisted by admins (bypass channel requirements)
  - Can be banned by admins (deny all access)
  - Default status: must follow channel membership rules

### 3. **Database Setup**

For **Docker** (recommended):
```bash
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@postgres/ytdlbot
```

For **Local PostgreSQL**:
1. Install PostgreSQL
2. Create database: `createdb ytdlbot`
3. Create user: `createuser -P ytdlbot` (set password)
4. Grant access: `GRANT ALL ON DATABASE ytdlbot TO ytdlbot;`
5. Use: `postgresql+psycopg2://ytdlbot:password@localhost:5432/ytdlbot`

### 4. **Example Working Configuration**

```bash
# Required - Replace with your values
APP_ID=12345678
APP_HASH=1a2b3c4d5e6f7g8h9i0j
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
ADMIN_IDS=123456789,987654321

# Database (for Docker)
DB_DSN=postgresql+psycopg2://ytdlbot:ytdlbot@postgres/ytdlbot
REDIS_HOST=redis

# Access Control
ACCESS_CONTROL_ENABLED=True

# Optional settings (defaults work fine)
WORKERS=100
ENABLE_FFMPEG=False
AUDIO_FORMAT=
TG_NORMAL_MAX_SIZE=2000
```

## 🔐 Access Control System

### How It Works
1. **Admin Panel**: Use `/admin` command to manage access
2. **Required Channels**: Users must join at least ONE required channel
3. **Manual Control**: Whitelist/ban users individually
4. **Status Levels**:
   - ✅ **Whitelisted**: Always has access
   - ❌ **Banned**: No access regardless of channels
   - 👤 **Normal**: Must follow channel requirements

### Managing Access
1. Send `/admin` to your bot
2. Use the inline keyboard to:
   - **Manage Channels**: Add/remove required channels
   - **Manual Access**: Whitelist/ban specific users
   - **Access Stats**: View user statistics

### Adding Required Channels
1. Go to **Admin Panel** → **Manage Channels** → **Add Channel**
2. Either:
   - Forward a message from the channel
   - Send channel username: `@channelname`
   - Send channel ID: `-1001234567890`
3. **Important**: Your bot must be added as an admin to the channel

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Copy environment file
cp .env.example .env

# Edit .env with your values
nano .env

# Start the bot
docker-compose up -d
```

### Manual Docker
```bash
# Build image
docker build -t ytdlbot .

# Run with environment file
docker run -d --env-file .env ytdlbot
```

## 💡 Tips & Best Practices

### Security
- Keep your `BOT_TOKEN` and `APP_HASH` secret
- Don't share your `.env` file
- Use strong database passwords in production

### Performance
- Start with `WORKERS=100` (adjust based on server capacity)
- Enable `ENABLE_FFMPEG=True` only if you need video processing
- Use Redis for better caching: `REDIS_HOST=redis`

### Access Control
- Set `ACCESS_CONTROL_ENABLED=True` for private use
- Add yourself to `ADMIN_IDS` to manage the bot
- Use channel requirements for automatic access control

### YouTube Downloads
- Default settings work for most users
- For high-volume usage, consider getting your own `POTOKEN`
- Use `BROWSERS=firefox` if you have Firefox installed for better cookie support

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid token"**: Check your `BOT_TOKEN` format
2. **"Database connection failed"**: Verify `DB_DSN` and database is running
3. **"Bot not responding"**: Ensure `APP_ID` and `APP_HASH` are correct
4. **"Access denied"**: Check if your user ID is in `ADMIN_IDS`

### Getting Help
- Check logs: `docker-compose logs ytdlbot`
- Verify environment: All required variables set?
- Test bot: Send `/start` to see if it responds

## 🎯 What Each Setting Does

| Setting | Required | Description |
|---------|----------|-------------|
| `APP_ID` | ✅ | Telegram API ID from my.telegram.org |
| `APP_HASH` | ✅ | Telegram API hash from my.telegram.org |
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `ADMIN_IDS` | ✅ | Admin user IDs (full bot control) |
| `ADMIN_IDS` | ✅ | Admin user IDs (can manage access) |
| `DB_DSN` | ✅ | Database connection string |
| `ACCESS_CONTROL_ENABLED` | ⚠️ | Enable access control (recommended: True) |
| `REDIS_HOST` | ❌ | Redis server for caching (optional) |
| `WORKERS` | ❌ | Concurrent download workers (default: 100) |
| `ENABLE_FFMPEG` | ❌ | Video processing (requires ffmpeg) |
| `AUDIO_FORMAT` | ❌ | Audio format (default: m4a) |
| `TG_NORMAL_MAX_SIZE` | ❌ | Upload size limit MB (default: 2000) |

Your bot is now ready for private use with robust access control! 🎉
