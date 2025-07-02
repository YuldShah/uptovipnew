#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - stats_logger.py
# Statistics logging functionality

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Global variables for stats logging
_stats_thread: Optional[threading.Thread] = None
_stats_running = False


def start_stats_logging():
    """Start the statistics logging thread"""
    global _stats_thread, _stats_running
    
    if _stats_running:
        logger.warning("Stats logging is already running")
        return
    
    _stats_running = True
    _stats_thread = threading.Thread(target=_stats_worker, daemon=True)
    _stats_thread.start()
    logger.info("Stats logging started")


def stop_stats_logging():
    """Stop the statistics logging thread"""
    global _stats_thread, _stats_running
    
    if not _stats_running:
        logger.warning("Stats logging is not running")
        return
    
    _stats_running = False
    if _stats_thread and _stats_thread.is_alive():
        _stats_thread.join(timeout=5.0)
    
    logger.info("Stats logging stopped")


def _stats_worker():
    """Background worker for statistics logging"""
    logger.info("Stats logging worker started")
    
    while _stats_running:
        try:
            # Log basic stats every 5 minutes
            time.sleep(300)  # 5 minutes
            
            if _stats_running:
                _log_system_stats()
                
        except Exception as e:
            logger.error(f"Error in stats worker: {e}")
            time.sleep(60)  # Wait 1 minute before retrying


def _log_system_stats():
    """Log basic system statistics"""
    try:
        import psutil
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        logger.info(
            f"System Stats - "
            f"Memory: {memory.percent:.1f}% used ({memory.used // (1024**3):.1f}GB), "
            f"CPU: {cpu_percent:.1f}%, "
            f"Disk: {disk.percent:.1f}% used ({disk.used // (1024**3):.1f}GB)"
        )
        
    except Exception as e:
        logger.error(f"Error logging system stats: {e}")


def log_download_stats(user_id: int, url: str, success: bool, file_size: int = None, duration: float = None):
    """Log download statistics"""
    status = "SUCCESS" if success else "FAILED"
    size_str = f", Size: {file_size // (1024**2):.1f}MB" if file_size else ""
    duration_str = f", Duration: {duration:.1f}s" if duration else ""
    
    logger.info(f"Download {status} - User: {user_id}, URL: {url[:50]}...{size_str}{duration_str}")


def log_user_activity(user_id: int, activity: str, details: dict = None):
    """Log user activity"""
    details_str = f", Details: {details}" if details else ""
    logger.info(f"User Activity - User: {user_id}, Activity: {activity}{details_str}")


def get_stats_status() -> dict:
    """Get current statistics logging status"""
    global _stats_thread, _stats_running
    
    return {
        'running': _stats_running,
        'thread_alive': _stats_thread.is_alive() if _stats_thread else False
    }
