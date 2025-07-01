#!/usr/bin/env python3
# coding: utf-8

import logging
import psutil
import time
import asyncio
from datetime import datetime

from database.model import log_system_stats

logger = logging.getLogger(__name__)


class StatsLogger:
    """Background service to log system statistics"""
    
    def __init__(self, interval: int = 300):  # Log every 5 minutes
        self.interval = interval
        self.running = False
    
    async def start(self):
        """Start the stats logging service"""
        self.running = True
        logger.info("Starting system stats logging service")
        
        while self.running:
            try:
                await self.log_stats()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in stats logging: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop(self):
        """Stop the stats logging service"""
        self.running = False
        logger.info("Stopping system stats logging service")
    
    async def log_stats(self):
        """Log current system statistics"""
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Log to database
            log_system_stats(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent
            )
            
            logger.debug(f"Logged system stats: CPU={cpu_usage}%, Memory={memory.percent}%, Disk={disk.percent}%")
            
        except Exception as e:
            logger.error(f"Error logging system stats: {e}")


# Global instance
stats_logger = StatsLogger()


def start_stats_logging():
    """Start system statistics logging"""
    asyncio.create_task(stats_logger.start())


def stop_stats_logging():
    """Stop system statistics logging"""
    stats_logger.stop()
