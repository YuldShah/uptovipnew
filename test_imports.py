#!/usr/bin/env python3
# Import test script - checks all imports from main.py

print("Testing imports...")

# Test standard library imports
try:
    import asyncio
    import logging
    import os
    import re
    import threading
    import time
    import typing
    from io import BytesIO
    from typing import Any
    print("✓ Standard library imports OK")
except Exception as e:
    print(f"✗ Standard library imports failed: {e}")

# Test third-party imports
try:
    import psutil
    print("✓ psutil import OK")
except Exception as e:
    print(f"✗ psutil import failed: {e}")

try:
    import pyrogram.errors
    import yt_dlp
    from apscheduler.schedulers.background import BackgroundScheduler
    from pyrogram import Client, enums, filters, types
    print("✓ pyrogram/yt-dlp/apscheduler imports OK")
except Exception as e:
    print(f"✗ pyrogram/yt-dlp/apscheduler imports failed: {e}")

# Test local config imports
try:
    from config import (
        APP_HASH,
        APP_ID,
        BOT_TOKEN,
        ENABLE_ARIA2,
        ENABLE_FFMPEG,
        M3U8_SUPPORT,
        BotText,
    )
    print("✓ Config imports OK")
except Exception as e:
    print(f"✗ Config imports failed: {e}")

# Test database imports
try:
    from database.model import (
        get_format_settings,
        get_quality_settings,
        get_user_access_status,
        init_user,
        set_user_settings,
        get_user_platform_quality,
        set_user_platform_quality,
        create_youtube_format_session,
        get_youtube_format_session,
        delete_youtube_format_session,
        log_user_activity,
        log_download_attempt,
        log_download_completion,
    )
    print("✓ Database model imports OK")
except Exception as e:
    print(f"✗ Database model imports failed: {e}")

# Test engine imports
try:
    from engine import direct_entrance, youtube_entrance, special_download_entrance
    print("✓ Engine imports OK")
except Exception as e:
    print(f"✗ Engine imports failed: {e}")

# Test youtube_formats imports
try:
    from engine.youtube_formats import extract_youtube_formats, is_youtube_url
    print("✓ YouTube formats imports OK")
except Exception as e:
    print(f"✗ YouTube formats imports failed: {e}")

# Test admin handlers imports
try:
    from handlers.admin import register_admin_handlers
    print("✓ Admin handlers imports OK")
except Exception as e:
    print(f"✗ Admin handlers imports failed: {e}")

# Test access_control imports
try:
    from utils.access_control import get_admin_list
    from utils.access_control import check_full_user_access, get_access_denied_message, is_admin
    print("✓ Access control imports OK")
except Exception as e:
    print(f"✗ Access control imports failed: {e}")

# Test keyboard imports
try:
    from keyboards.main import (
        create_main_keyboard,
        create_admin_keyboard,
        create_settings_keyboard,
        create_format_settings_keyboard,
        create_youtube_quality_keyboard,
        create_platform_quality_keyboard,
        create_youtube_format_keyboard,
        create_back_keyboard,
    )
    print("✓ Keyboard imports OK")
except Exception as e:
    print(f"✗ Keyboard imports failed: {e}")

# Test utils imports
try:
    from utils import extract_url_and_name, sizeof_fmt, timeof_fmt
    print("✓ Utils imports OK")
except Exception as e:
    print(f"✗ Utils imports failed: {e}")

# Test stats_logger imports
try:
    from utils.stats_logger import start_stats_logging, stop_stats_logging
    print("✓ Stats logger imports OK")
except Exception as e:
    print(f"✗ Stats logger imports failed: {e}")

# Test error_handling imports
try:
    from utils.error_handling import setup_comprehensive_logging, error_handler, download_error_handler
    print("✓ Error handling imports OK")
except Exception as e:
    print(f"✗ Error handling imports failed: {e}")

print("\nImport test completed!")
