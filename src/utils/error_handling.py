#!/usr/bin/env python3
# coding: utf-8

import logging
import functools
import traceback
from typing import Callable, Any
from datetime import datetime

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery

# Configure comprehensive logging
def setup_comprehensive_logging():
    """Setup comprehensive logging for the bot"""
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler for all logs
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Error file handler
    error_handler = logging.FileHandler('errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Access control log handler
    access_handler = logging.FileHandler('access.log', encoding='utf-8')
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(simple_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Configure access control logger
    access_logger = logging.getLogger('access_control')
    access_logger.addHandler(access_handler)
    
    # Configure download logger
    download_logger = logging.getLogger('downloads')
    download_handler = logging.FileHandler('downloads.log', encoding='utf-8')
    download_handler.setFormatter(detailed_formatter)
    download_logger.addHandler(download_handler)
    
    logging.info("Comprehensive logging system initialized")


def error_handler(func: Callable) -> Callable:
    """Decorator for comprehensive error handling"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log the error with full traceback
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            
            # Try to send error message to user if possible
            if args and len(args) >= 2:
                client_or_query = args[0]
                message_or_callback = args[1]
                
                try:
                    if isinstance(message_or_callback, Message):
                        await message_or_callback.reply_text(
                            "❌ **An error occurred**\n\n"
                            "The operation could not be completed. "
                            "Please try again later or contact support if the issue persists.",
                            quote=True
                        )
                    elif isinstance(message_or_callback, CallbackQuery):
                        await message_or_callback.answer(
                            "❌ An error occurred. Please try again later.",
                            show_alert=True
                        )
                except Exception as notify_error:
                    logging.error(f"Failed to notify user of error: {notify_error}")
            
            # Re-raise for debugging in development
            if logging.getLogger().level == logging.DEBUG:
                raise
    
    return wrapper


def admin_error_handler(func: Callable) -> Callable:
    """Decorator for admin function error handling with detailed reporting"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log the error with full context
            error_msg = f"Admin function error in {func.__name__}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            
            # Send detailed error to admin
            if args and len(args) >= 2:
                callback_query = args[1] if len(args) > 1 else None
                
                if isinstance(callback_query, CallbackQuery):
                    try:
                        error_details = (
                            f"🚨 **Admin Function Error**\n\n"
                            f"**Function:** `{func.__name__}`\n"
                            f"**Error:** `{str(e)}`\n"
                            f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"Check logs for full details."
                        )
                        
                        await callback_query.edit_message_text(
                            error_details,
                            reply_markup=None
                        )
                    except Exception:
                        await callback_query.answer(
                            f"❌ Admin Error: {str(e)[:100]}",
                            show_alert=True
                        )
            
            # Re-raise for debugging
            if logging.getLogger().level == logging.DEBUG:
                raise
    
    return wrapper


def download_error_handler(func: Callable) -> Callable:
    """Decorator for download function error handling"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log download-specific error
            download_logger = logging.getLogger('downloads')
            download_logger.error(f"Download error in {func.__name__}: {str(e)}", exc_info=True)
            
            # Try to update download statistics if possible
            try:
                from database.model import log_download_completion
                # Extract download_id if available in kwargs or context
                download_id = kwargs.get('download_id')
                if download_id:
                    log_download_completion(
                        download_id=download_id,
                        success=False,
                        error_message=str(e)[:500]  # Limit error message length
                    )
            except Exception as stats_error:
                logging.error(f"Failed to log download error statistics: {stats_error}")
            
            # Notify user of download failure
            if args and len(args) >= 2:
                message = args[1] if len(args) > 1 else None
                
                if isinstance(message, Message):
                    try:
                        await message.reply_text(
                            "❌ **Download Failed**\n\n"
                            f"Error: {str(e)[:200]}\n\n"
                            "Please check the URL and try again. "
                            "If the issue persists, the content might not be available or supported.",
                            quote=True
                        )
                    except Exception:
                        pass  # Don't fail if we can't send the error message
            
            # Re-raise for debugging
            if logging.getLogger().level == logging.DEBUG:
                raise
    
    return wrapper


class ErrorReporter:
    """Centralized error reporting and monitoring"""
    
    def __init__(self):
        self.error_counts = {}
        self.critical_errors = []
    
    def report_error(self, error_type: str, error_msg: str, user_id: int = None):
        """Report an error for monitoring"""
        timestamp = datetime.now()
        
        # Count errors by type
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Log critical errors
        if error_type in ['access_control_failure', 'database_error', 'admin_error']:
            self.critical_errors.append({
                'type': error_type,
                'message': error_msg,
                'user_id': user_id,
                'timestamp': timestamp
            })
            
            # Keep only last 100 critical errors
            if len(self.critical_errors) > 100:
                self.critical_errors = self.critical_errors[-100:]
        
        logging.error(f"Reported error [{error_type}]: {error_msg} (User: {user_id})")
    
    def get_error_summary(self) -> dict:
        """Get error summary for admin dashboard"""
        return {
            'error_counts': self.error_counts.copy(),
            'critical_errors': self.critical_errors[-10:],  # Last 10 critical errors
            'total_errors': sum(self.error_counts.values())
        }
    
    def clear_old_errors(self, days: int = 7):
        """Clear old error records"""
        cutoff = datetime.now() - timedelta(days=days)
        self.critical_errors = [
            error for error in self.critical_errors 
            if error['timestamp'] > cutoff
        ]


# Global error reporter instance
error_reporter = ErrorReporter()
