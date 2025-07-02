# Quick Database Fix for ENUM Error

## 🚨 The Problem
Your database has ENUM types without names, which causes PostgreSQL errors.

## ✅ Quick Fix Options

### Option 1: Reset Database (Recommended for fresh start)

```bash
# Run the reset script
python reset_database.py

# Then start your bot
python src/main.py
```

### Option 2: Manual Database Fix

Connect to your PostgreSQL database and run:

```sql
-- Connect to your database
psql -h localhost -U ytdlbot -d ytdlbot

-- Drop existing ENUM types and tables
DROP TABLE IF EXISTS channels CASCADE;
DROP TABLE IF EXISTS settings CASCADE; 
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS quality_enum CASCADE;
DROP TYPE IF EXISTS format_enum CASCADE;

-- Exit psql
\q
```

Then restart your bot:
```bash
python src/main.py
```

### Option 3: One-Line Database Reset

```bash
# Quick reset command
psql -h localhost -U ytdlbot -d ytdlbot -c "
DROP TABLE IF EXISTS channels CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS quality_enum CASCADE;
DROP TYPE IF EXISTS format_enum CASCADE;
"

# Then start bot
python src/main.py
```

## 🔧 What Was Fixed

I updated your `src/database/model.py` to add proper names to ENUM types:

```python
# Before (causing error):
quality = Column(Enum("high", "medium", "low", "audio", "custom"), ...)

# After (fixed):
quality = Column(Enum("high", "medium", "low", "audio", "custom", name="quality_enum"), ...)
format = Column(Enum("video", "audio", "document", name="format_enum"), ...)
```

## 🎯 Recommended Approach

1. **Use the reset script** (safest):
   ```bash
   python reset_database.py
   ```

2. **Or manual PostgreSQL reset** (if script doesn't work):
   ```bash
   psql -h localhost -U ytdlbot -d ytdlbot -c "
   DROP TABLE IF EXISTS channels CASCADE;
   DROP TABLE IF EXISTS settings CASCADE;
   DROP TABLE IF EXISTS users CASCADE;
   DROP TYPE IF EXISTS quality_enum CASCADE;
   DROP TYPE IF EXISTS format_enum CASCADE;
   "
   ```

3. **Start your bot**:
   ```bash
   python src/main.py
   ```

The bot will automatically create fresh tables with properly named ENUM types! 🎉

## ⚠️ Note

This will delete any existing data (users, settings, channels). Since you're setting up the bot for the first time, this shouldn't be an issue.
