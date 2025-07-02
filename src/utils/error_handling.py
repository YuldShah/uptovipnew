#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - error_handling.py
# Error handling and logging utilities

import functools
import logging
import sys
import traceback
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def setup_comprehensive_logging(log_level: str = "INFO"):
    """Setup comprehensive logging configuration"""
    
    # Convert string log level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level_int = level_map.get(log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level_int,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
    # Set specific loggers to reduce noise
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("kurigram").setLevel(logging.WARNING)
    logging.getLogger("yt-dlp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {log_level}")


def error_handler(func: Callable) -> Callable:
    """Decorator for general error handling"""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def download_error_handler(func: Callable) -> Callable:
    """Decorator for download-specific error handling"""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific download errors
            if "Video unavailable" in error_msg:
                logger.warning(f"Video unavailable in {func.__name__}: {error_msg}")
            elif "Private video" in error_msg:
                logger.warning(f"Private video in {func.__name__}: {error_msg}")
            elif "This video is not available" in error_msg:
                logger.warning(f"Video not available in {func.__name__}: {error_msg}")
            elif "HTTP Error 429" in error_msg:
                logger.warning(f"Rate limited in {func.__name__}: {error_msg}")
            else:
                logger.error(f"Download error in {func.__name__}: {error_msg}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific download errors
            if "Video unavailable" in error_msg:
                logger.warning(f"Video unavailable in {func.__name__}: {error_msg}")
            elif "Private video" in error_msg:
                logger.warning(f"Private video in {func.__name__}: {error_msg}")
            elif "This video is not available" in error_msg:
                logger.warning(f"Video not available in {func.__name__}: {error_msg}")
            elif "HTTP Error 429" in error_msg:
                logger.warning(f"Rate limited in {func.__name__}: {error_msg}")
            else:
                logger.error(f"Download error in {func.__name__}: {error_msg}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
            
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def handle_telegram_error(error: Exception) -> str:
    """Handle Telegram-specific errors and return user-friendly messages"""
    error_msg = str(error)
    
    if "flood" in error_msg.lower():
        return "⏰ **Rate Limited**\n\nToo many requests. Please wait a moment and try again."
    
    elif "chat not found" in error_msg.lower():
        return "❌ **Chat Not Found**\n\nThe chat or channel could not be found."
    
    elif "user not found" in error_msg.lower():
        return "❌ **User Not Found**\n\nThe specified user could not be found."
    
    elif "message not modified" in error_msg.lower():
        return None  # Silently ignore message not modified errors
    
    elif "forbidden" in error_msg.lower():
        return "🚫 **Access Forbidden**\n\nThe bot doesn't have permission to perform this action."
    
    elif "bad request" in error_msg.lower():
        return "❌ **Invalid Request**\n\nThe request was invalid. Please check your input and try again."
    
    else:
        logger.error(f"Unhandled Telegram error: {error_msg}")
        return "❌ **Unexpected Error**\n\nAn unexpected error occurred. Please try again later."


def handle_download_error(error: Exception) -> str:
    """Handle download-specific errors and return user-friendly messages"""
    error_msg = str(error)
    
    if "Video unavailable" in error_msg or "Private video" in error_msg:
        return "❌ **Video Unavailable**\n\nThis video is private, unavailable, or has been removed."
    
    elif "This video is not available" in error_msg:
        return "❌ **Video Not Available**\n\nThis video is not available in your region or has been restricted."
    
    elif "HTTP Error 429" in error_msg:
        return "⏰ **Rate Limited**\n\nToo many requests to the video platform. Please wait and try again later."
    
    elif "No video formats found" in error_msg:
        return "❌ **No Formats Available**\n\nNo downloadable formats were found for this video."
    
    elif "Unsupported URL" in error_msg:
        return "❌ **Unsupported Platform**\n\nThis platform or URL format is not supported."
    
    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
        return "🌐 **Network Error**\n\nNetwork connection failed. Please check your internet connection and try again."
    
    elif "timeout" in error_msg.lower():
        return "⏰ **Timeout Error**\n\nThe download timed out. The video might be too large or the server is slow."
    
    else:
        logger.error(f"Unhandled download error: {error_msg}")
        return "❌ **Download Failed**\n\nThe download failed due to an unexpected error. Please try again."


class BotError(Exception):
    """Base exception for bot-specific errors"""
    pass


class AccessDeniedError(BotError):
    """Raised when user access is denied"""
    pass


class DownloadError(BotError):
    """Raised when download fails"""
    pass


class ConfigurationError(BotError):
    """Raised when there's a configuration issue"""
    pass
