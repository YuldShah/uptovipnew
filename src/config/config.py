#!/usr/local/bin/python3
# coding: utf-8

import os


def get_env(name: str, default=None):
    val = os.getenv(name, default)
    if val is None:
        return None
    if isinstance(val, str):
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        if val.isdigit():
            return int(val)
    return val


# general settings
WORKERS: int = get_env("WORKERS", 100)
APP_ID: int = get_env("APP_ID")
APP_HASH = get_env("APP_HASH")
BOT_TOKEN = get_env("BOT_TOKEN")

# admin settings - only admins, no separate owner concept
ADMIN_IDS = get_env("ADMIN_IDS", "")  # comma-separated admin user IDs

# database settings
DB_DSN = get_env("DB_DSN")
REDIS_HOST = get_env("REDIS_HOST")

ENABLE_FFMPEG = get_env("ENABLE_FFMPEG")
AUDIO_FORMAT = get_env("AUDIO_FORMAT", "m4a")
M3U8_SUPPORT = get_env("M3U8_SUPPORT")
ENABLE_ARIA2 = get_env("ENABLE_ARIA2")

RCLONE_PATH = get_env("RCLONE")

# access control settings
ACCESS_CONTROL_ENABLED = get_env("ACCESS_CONTROL_ENABLED", True)  # enable access control

# For advance users
# Please do not change, if you don't know what these are.
TG_NORMAL_MAX_SIZE = 2000 * 1024 * 1024
CAPTION_URL_LENGTH_LIMIT = 150

# This will set the value for the tmpfile path(engine path). If not, will return None and use system’s default path.
# Please ensure that the directory exists and you have necessary permissions to write to it.
TMPFILE_PATH = get_env("TMPFILE_PATH")
