# YouTube Download Bot - Private Edition

## Complete Setup and Configuration Guide

### Overview

This is a comprehensive private YouTube download bot with advanced access control, dynamic quality selection, statistics dashboard, and robust error handling. The bot has been completely refactored for private use with enterprise-grade features.

### Features

#### ✅ **Completed Core Features**

1. **🚫 Payment System Removal**
   - All VIP/quota/payment features removed
   - No public credits or author references
   - Clean private bot interface

2. **🔐 Access Control System**
   - Admin-based access control
   - Channel membership requirements (ANY of multiple channels)
   - User whitelist/ban system
   - Fail-secure access control with proper error handling

3. **🎬 Dynamic Quality Selection**
   - Per-video YouTube format selection with inline keyboards
   - User platform quality settings for non-YouTube sites
   - Only `/start` command - all navigation via keyboards
   - Format extraction with file size estimates

4. **👨‍💼 Enhanced Admin Interface**
   - Complete user and channel management
   - User search by ID and listing
   - Confirmation dialogs for destructive actions
   - Access status display and management

5. **📊 Advanced Statistics Dashboard**
   - Download analytics (success rates, platform breakdown, file sizes)
   - User activity tracking (starts, downloads, settings changes)
   - System performance monitoring with background logging
   - Real-time stats with 7-day and 30-day views

6. **🛡️ Production-Ready Error Handling**
   - Comprehensive logging system (bot.log, errors.log, access.log, downloads.log)
   - Graceful error recovery with user notifications
   - Admin error reporting with detailed context
   - Download failure tracking and statistics

### Environment Configuration

Create a `.env` file in the project root:

```env
# Required - Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
APP_ID=your_app_id_here
APP_HASH=your_app_hash_here

# Required - Admin Configuration
ADMIN_IDS=123456789,987654321  # Comma-separated admin user IDs

# Optional - Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ytdlbot

# Optional - Download Configuration
ENABLE_ARIA2=true
ENABLE_FFMPEG=true
M3U8_SUPPORT=false

# Optional - Advanced Settings
ACCESS_CONTROL_ENABLED=true
MAX_DOWNLOAD_SIZE=500MB
DOWNLOAD_TIMEOUT=300
```

### Database Setup

The bot uses PostgreSQL with SQLAlchemy. Make sure you have PostgreSQL installed and create a database:

```sql
CREATE DATABASE ytdlbot;
CREATE USER ytdlbot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ytdlbot TO ytdlbot_user;
```

The bot will automatically create all required tables on first run.

### Installation Steps

1. **Clone and Setup**
   ```bash
   git clone <repository_url>
   cd ytdlbot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # OR using PDM
   pdm install
   ```

3. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Fill in your Telegram bot credentials
   - Add your admin user IDs
   - Configure database connection

4. **Run the Bot**
   ```bash
   python src/main.py
   ```

### Admin Usage Guide

#### Initial Setup

1. **Start the bot** and send `/start` to initialize your admin account
2. **Use `/admin`** to access the admin panel
3. **Add required channels** for user access control
4. **Configure access settings** as needed

#### Admin Panel Features

**📢 Manage Channels**
- Add channels users must join for access
- Remove channels from requirements
- View channel member counts and status

**👤 Manual Access**
- Whitelist users (permanent access)
- Ban users (deny access)
- Check user access status
- Search users by ID

**📊 Statistics Dashboard**
- View access control statistics
- Monitor download analytics (success rates, platforms, file sizes)
- Track user activity and engagement
- System performance monitoring

#### Access Control Logic

The bot uses a layered access control system:

1. **Admin Users**: Always have full access
2. **Whitelisted Users**: Have permanent access regardless of channels
3. **Normal Users**: Must be members of ANY required channel
4. **Banned Users**: Denied access regardless of other factors

#### Channel Management

- Users need to be members of **ANY** of the required channels (not all)
- The bot must be added as an admin to channels for membership verification
- Private channels are supported but require the bot to have admin access
- Channel access failures are logged for admin review

### User Features

#### Navigation
- Only `/start` command is available
- All navigation through reply keyboards and inline buttons
- Clean, intuitive interface

#### Download Features
- **YouTube**: Dynamic format selection per video with quality options
- **Other Platforms**: User-configurable quality settings (highest/balanced)
- **Special Downloads**: Instagram, Pixeldrain, Krakenfiles support
- **Direct Downloads**: aria2/requests for direct links

#### Settings
- Upload format (video/audio/document)
- YouTube quality preferences
- Platform quality for non-YouTube sites

### Statistics and Analytics

#### Download Analytics
- Total downloads with success/failure rates
- Platform breakdown (YouTube, Instagram, etc.)
- Average file sizes and download speeds
- Error tracking and categorization

#### User Analytics
- Active user counts (daily/weekly/monthly)
- Activity breakdown (starts, downloads, settings)
- User engagement patterns
- Growth tracking

#### System Monitoring
- CPU, memory, and disk usage tracking
- Performance metrics and error rates
- Background logging every 5 minutes
- Automated alerts for critical issues

### File Structure

```
ytdlbot/
├── src/
│   ├── main.py                 # Main bot application
│   ├── config/
│   │   ├── config.py           # Configuration management
│   │   └── constant.py         # Constants and text
│   ├── database/
│   │   ├── model.py            # Database models and functions
│   │   └── cache.py            # Caching utilities
│   ├── engine/
│   │   ├── youtube_formats.py  # YouTube format extraction
│   │   ├── base.py             # Base download engine
│   │   ├── direct.py           # Direct download engine
│   │   ├── generic.py          # Generic download engine
│   │   ├── instagram.py        # Instagram engine
│   │   ├── pixeldrain.py       # Pixeldrain engine
│   │   └── krakenfiles.py      # Krakenfiles engine
│   ├── handlers/
│   │   └── admin.py            # Admin interface handlers
│   ├── keyboards/
│   │   └── main.py             # Keyboard layouts
│   └── utils/
│       ├── access_control.py   # Access control logic
│       ├── error_handling.py   # Error handling and logging
│       └── stats_logger.py     # Statistics logging service
├── requirements.txt            # Python dependencies
├── pyproject.toml             # PDM configuration
├── docker-compose.yml         # Docker setup
├── Dockerfile                 # Docker image
└── README.md                  # This documentation
```

### Logging System

The bot creates several log files:

- **`bot.log`**: All bot activities and debug information
- **`errors.log`**: Error events and exceptions
- **`access.log`**: Access control events and decisions
- **`downloads.log`**: Download attempts, successes, and failures

Log files rotate automatically and include detailed context for troubleshooting.

### Security Features

- **Fail-secure access control**: Denies access on any error
- **Admin alerts**: Critical errors are reported to admins
- **Input validation**: All user inputs are validated
- **Rate limiting**: Pyrogram built-in flood protection
- **Database security**: Parameterized queries prevent injection
- **Error masking**: Sensitive information not exposed to users

### Performance Optimization

- **Async/await**: Full asynchronous operation
- **Connection pooling**: Database connection management
- **Background tasks**: Statistics logging doesn't block operations
- **Memory management**: Automatic cleanup of temporary data
- **Resource monitoring**: System performance tracking

### Troubleshooting

#### Common Issues

**Bot not responding:**
- Check bot token and permissions
- Verify admin IDs are correct
- Check network connectivity and Telegram API access

**Access control not working:**
- Verify bot is admin in required channels
- Check channel IDs are correct
- Review access.log for detailed error information

**Downloads failing:**
- Check yt-dlp is updated
- Verify aria2 installation if enabled
- Review downloads.log for specific errors

**Database errors:**
- Verify PostgreSQL is running
- Check database connection string
- Ensure database user has proper permissions

#### Debug Mode

Enable debug logging by setting the log level:

```python
logging.getLogger().setLevel(logging.DEBUG)
```

This provides detailed information about all bot operations.

### Deployment

#### Docker Deployment

```bash
# Build the image
docker-compose build

# Run the bot
docker-compose up -d

# View logs
docker-compose logs -f ytdlbot
```

#### Systemd Service (Linux)

Create `/etc/systemd/system/ytdlbot.service`:

```ini
[Unit]
Description=YouTube Download Bot
After=network.target

[Service]
Type=simple
User=ytdlbot
WorkingDirectory=/opt/ytdlbot
ExecStart=/opt/ytdlbot/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ytdlbot
sudo systemctl start ytdlbot
```

### Maintenance

#### Regular Tasks

1. **Monitor logs** for errors and performance issues
2. **Update yt-dlp** regularly for platform compatibility
3. **Review statistics** for usage patterns and optimization
4. **Backup database** regularly
5. **Clean old log files** to manage disk space

#### Updates

To update the bot:

1. **Backup database** and configuration
2. **Pull latest changes** from repository
3. **Update dependencies** if needed
4. **Restart bot** with new code
5. **Monitor logs** for any issues

### Support and Development

#### Architecture Overview

The bot follows a modular architecture:

- **Main Application**: `src/main.py` - Bot initialization and core handlers
- **Access Control**: `src/utils/access_control.py` - Authentication and authorization
- **Admin Interface**: `src/handlers/admin.py` - Administrative functions
- **Database Layer**: `src/database/model.py` - Data persistence and statistics
- **Download Engines**: `src/engine/` - Platform-specific download logic
- **Error Handling**: `src/utils/error_handling.py` - Comprehensive error management

#### Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive error handling to new features
3. Update statistics tracking for new functionality
4. Include proper logging for debugging
5. Test all access control scenarios
6. Update documentation for new features

### License

This bot is configured for private use only. Remove any remaining public references before deployment.

---

**Private YouTube Download Bot - Production Ready Edition**

Complete feature set with enterprise-grade reliability, security, and monitoring.
