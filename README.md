# YouTube Download Bot - Private Edition

**Production-Ready Private Bot with Advanced Access Control & Analytics**

A completely refactored YouTube download bot designed for private use with enterprise-grade features including dynamic quality selection, comprehensive access control, advanced statistics dashboard, and robust error handling.

## 🌟 Features

### ✅ **Completed & Production Ready**

- **🚫 Payment System Removal**: All VIP/quota/payment features completely removed
- **🔐 Advanced Access Control**: Admin, channel membership (ANY), whitelist/ban system
- **🎬 Dynamic Quality Selection**: Per-video YouTube format selection with inline keyboards
- **⌨️ Keyboard-Only Navigation**: Only `/start` command, all navigation via reply/inline keyboards
- **👨‍💼 Enhanced Admin Interface**: Complete user/channel management with search and pagination
- **📊 Statistics Dashboard**: Download analytics, user activity tracking, system monitoring
- **🛡️ Production Error Handling**: Comprehensive logging, graceful recovery, admin alerts
- **📈 Real-time Analytics**: 7-day and 30-day views with platform breakdowns
- **🔄 Background Monitoring**: Automated system stats logging and performance tracking

### 🎯 **Key Capabilities**

- **Private Bot Only**: No public features, designed for controlled access
- **Fail-Secure Access**: Denies access on any error, with detailed logging
- **Multi-Platform Support**: YouTube (dynamic), Instagram, Pixeldrain, Krakenfiles
- **Quality Control**: User-configurable settings for all platforms
- **Admin Dashboard**: Real-time statistics, user management, error monitoring
- **Enterprise Logging**: Separate logs for bot activity, errors, access control, downloads

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token and API credentials
- Admin Telegram user IDs

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd ytdlbot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Setup database**
   ```bash
   # Create PostgreSQL database
   createdb ytdlbot
   ```

5. **Run the bot**
   ```bash
   python src/main.py
   ```

### Environment Configuration

```env
# Required - Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
APP_ID=your_app_id_here
APP_HASH=your_app_hash_here

# Required - Admin Configuration
ADMIN_IDS=123456789,987654321  # Comma-separated admin user IDs

# Optional - Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ytdlbot

# Optional - Feature Toggles
ENABLE_ARIA2=true
ENABLE_FFMPEG=true
ACCESS_CONTROL_ENABLED=true
```

## 📖 Usage Guide

### For Admins

1. **Start the bot**: Send `/start` to initialize
2. **Access admin panel**: Send `/admin` to open management interface
3. **Setup access control**:
   - Add required channels for user access
   - Manage user whitelist/ban status
   - Monitor statistics and performance

### Admin Panel Features

- **📢 Manage Channels**: Add/remove required channels for access
- **👤 Manual Access**: Whitelist/ban users, search by ID
- **📊 Access Stats**: View user counts and access patterns
- **📈 Download Analytics**: Success rates, platform breakdown, file sizes
- **👥 User Analytics**: Activity tracking, engagement metrics

### For Users

- **Navigation**: Only `/start` command, all navigation via keyboards
- **YouTube Downloads**: Dynamic format selection per video
- **Other Platforms**: Configurable quality settings
- **Settings**: Upload format, quality preferences
- **Statistics**: Personal usage stats

## 🔐 Access Control System

### Access Levels

1. **Admin Users**: Full access to bot and admin panel
2. **Whitelisted Users**: Permanent access regardless of channels
3. **Normal Users**: Must be members of ANY required channel
4. **Banned Users**: Denied access regardless of other factors

### Channel Membership

- Users need membership in **ANY** of the required channels (not all)
- Bot must be admin in channels for membership verification
- Supports private channels with proper bot permissions
- Automatic verification with detailed error logging

## 📊 Statistics & Analytics

### Download Analytics
- **Success Rates**: Track successful vs failed downloads
- **Platform Breakdown**: Usage by platform (YouTube, Instagram, etc.)
- **File Metrics**: Average sizes, download speeds, quality distribution
- **Error Tracking**: Categorized failure analysis

### User Analytics
- **Activity Tracking**: Starts, downloads, settings changes
- **Engagement Metrics**: Daily/weekly/monthly active users
- **Usage Patterns**: Platform preferences, quality choices
- **Growth Tracking**: User acquisition and retention

### System Monitoring
- **Performance Metrics**: CPU, memory, disk usage
- **Error Rates**: System-wide error tracking
- **Background Logging**: Automated 5-minute intervals
- **Health Monitoring**: Automated alerts for critical issues

## 🛡️ Error Handling & Security

### Comprehensive Error Handling
- **Graceful Recovery**: All errors handled without crashing
- **User Notifications**: Friendly error messages for users
- **Admin Alerts**: Detailed error reports for administrators
- **Logging System**: Separate logs for different error types

### Security Features
- **Fail-Secure Access**: Denies access on any error
- **Input Validation**: All user inputs sanitized
- **Rate Limiting**: Pyrogram built-in flood protection
- **Database Security**: Parameterized queries prevent injection
- **Error Masking**: Sensitive information not exposed

### Logging System
- **`bot.log`**: All bot activities and debug information
- **`errors.log`**: Error events and exceptions
- **`access.log`**: Access control decisions and events
- **`downloads.log`**: Download attempts and results

## 🏗️ Architecture

### Core Components

- **Main Application**: Bot initialization and core handlers
- **Access Control**: Authentication and authorization system
- **Admin Interface**: Administrative functions and statistics
- **Database Layer**: Data persistence and analytics
- **Download Engines**: Platform-specific download logic
- **Error Handling**: Comprehensive error management

### Database Models

- **Users**: Access status, settings, relationships
- **Channels**: Required channels for access control
- **DownloadStats**: Download tracking and analytics
- **UserActivity**: User interaction logging
- **SystemStats**: Performance monitoring data

## 🐳 Deployment

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f ytdlbot
```

### Systemd Service

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

[Install]
WantedBy=multi-user.target
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_bot.py
```

Tests include:
- Database models and functions
- Access control logic
- Statistics system
- Error handling
- Configuration validation

## 📁 Project Structure

```
ytdlbot/
├── src/
│   ├── main.py                 # Main bot application
│   ├── config/                 # Configuration management
│   ├── database/               # Database models and functions
│   ├── engine/                 # Download engines
│   ├── handlers/               # Admin interface
│   ├── keyboards/              # UI keyboards
│   └── utils/                  # Utilities and helpers
├── test_bot.py                 # Comprehensive test suite
├── DEPLOYMENT_GUIDE.md         # Detailed deployment guide
├── requirements.txt            # Dependencies
├── docker-compose.yml          # Docker configuration
└── README.md                   # This file
```

## 📋 Commands

### User Commands
- `start` - Initialize bot and show main menu

### Admin Commands
- `admin` - Access admin panel for bot management

### Admin Panel Features
- **📢 Manage Channels**: Add/remove required channels for user access
- **👤 Manual Access**: Whitelist or ban users manually
- **📊 Advanced Statistics**: Comprehensive analytics dashboard

## 🔧 Maintenance

### Regular Tasks
1. Monitor logs for errors and performance issues
2. Update yt-dlp regularly for platform compatibility
3. Review statistics for usage patterns
4. Backup database regularly
5. Clean old log files

### Health Monitoring
- System performance tracking every 5 minutes
- Error rate monitoring with automatic alerts
- Database performance and growth tracking
- User activity and engagement analysis

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Complete setup and configuration guide
- **[test_bot.py](test_bot.py)**: Comprehensive testing suite
- **Inline Documentation**: Detailed code comments and docstrings

## 🤝 Support

### Architecture Overview
The bot uses a modular, production-ready architecture with:
- Async/await for all operations
- Comprehensive error handling
- Database connection pooling
- Background task management
- Real-time monitoring and alerting

### Contributing
1. Follow existing code patterns
2. Add comprehensive error handling
3. Update statistics tracking
4. Include proper logging
5. Test all access control scenarios
6. Update documentation

## 📄 License

Configured for private use only. All public references removed for private deployment.

---

**YouTube Download Bot - Private Edition**
*Enterprise-grade reliability with comprehensive analytics and security*
