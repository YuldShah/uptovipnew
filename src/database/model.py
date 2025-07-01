#!/usr/bin/env python3
# coding: utf-8

import logging
import math
import os
from contextlib import contextmanager
from typing import Literal, List
from datetime import datetime, timedelta

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)  # telegram user id
    access_status = Column(Integer, default=0)  # -1: banned, 0: normal, 1: whitelisted
    config = Column(JSON)

    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan", uselist=False)
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quality = Column(Enum("high", "medium", "low", "audio", "custom"), nullable=False, default="high")
    format = Column(Enum("video", "audio", "document"), nullable=False, default="video")
    platform_quality = Column(Enum("highest", "balanced"), nullable=False, default="balanced")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="settings")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, unique=True, nullable=False)  # telegram channel id
    channel_name = Column(String, nullable=True)  # optional channel name
    channel_link = Column(String, nullable=True)  # optional channel link
    is_active = Column(Boolean, default=True)
    added_by = Column(BigInteger, nullable=False)  # admin who added it
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="channels")


class YouTubeFormatSession(Base):
    __tablename__ = "youtube_format_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    available_formats = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class DownloadStats(Base):
    __tablename__ = "download_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)  # telegram user id
    url = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # youtube, instagram, etc.
    format_requested = Column(String, nullable=True)  # format selected by user
    file_size = Column(BigInteger, nullable=True)  # in bytes
    duration = Column(Float, nullable=True)  # download duration in seconds
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Quality/format info
    video_quality = Column(String, nullable=True)  # 1080p, 720p, etc.
    audio_quality = Column(String, nullable=True)  # bitrate info
    
    # Performance metrics
    download_speed = Column(Float, nullable=True)  # MB/s


class UserActivity(Base):
    __tablename__ = "user_activity"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    activity_type = Column(String, nullable=False)  # 'start', 'download', 'settings', 'admin'
    details = Column(JSON, nullable=True)  # additional activity data
    timestamp = Column(DateTime, default=datetime.utcnow)


class SystemStats(Base):
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)  # percentage
    disk_usage = Column(Float, nullable=False)  # percentage
    active_users = Column(Integer, default=0)  # users active in last hour
    downloads_per_hour = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)  # percentage of failed downloads
    timestamp = Column(DateTime, default=datetime.utcnow)


def create_session():
    engine = create_engine(
        os.getenv("DB_DSN"),
        pool_size=50,
        max_overflow=100,
        pool_timeout=30,
        pool_recycle=1800,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


SessionFactory = create_session()


@contextmanager
def session_manager():
    s = SessionFactory()
    try:
        yield s
        s.commit()
    except Exception as e:
        s.rollback()
        raise
    finally:
        s.close()


def get_quality_settings(tgid) -> Literal["high", "medium", "low", "audio", "custom"]:
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == tgid).first()
        if user and user.settings:
            return user.settings.quality

        return "high"


def get_format_settings(tgid) -> Literal["video", "audio", "document"]:
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == tgid).first()
        if user and user.settings:
            return user.settings.format
        return "video"


def set_user_settings(tgid: int, key: str, value: str):
    # set quality or format settings
    with session_manager() as session:
        # find user first
        user = session.query(User).filter(User.user_id == tgid).first()
        # upsert
        setting = session.query(Setting).filter(Setting.user_id == user.id).first()
        if setting:
            setattr(setting, key, value)
        else:
            session.add(Setting(user_id=user.id, **{key: value}))


def init_user(uid: int):
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == uid).first()
        if not user:
            session.add(User(user_id=uid))


def get_user_access_status(uid: int) -> int:
    """Get user access status: -1=banned, 0=normal, 1=whitelisted"""
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == uid).first()
        if user:
            return user.access_status
        return 0  # Normal access for new users


def set_user_access_status(uid: int, status: int):
    """Set user access status: -1=banned, 0=normal, 1=whitelisted"""
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == uid).first()
        if user:
            user.access_status = status
        else:
            session.add(User(user_id=uid, access_status=status))


# Channel Management Functions
def add_required_channel(channel_id: int, channel_name: str = None, added_by: int = None) -> bool:
    """Add a channel to the required channels list"""
    with session_manager() as session:
        existing = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if existing:
            existing.is_active = True
            existing.channel_name = channel_name or existing.channel_name
            return True
        else:
            session.add(Channel(
                channel_id=channel_id,
                channel_name=channel_name,
                added_by=added_by or 0,
                is_active=True
            ))
            return True


def remove_required_channel(channel_id: int) -> bool:
    """Remove a channel from the required channels list"""
    with session_manager() as session:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            channel.is_active = False
            return True
        return False


def add_channel(channel_id: int, channel_name: str = None, channel_link: str = None, added_by: int = None) -> bool:
    """Add a required channel"""
    with session_manager() as session:
        # Check if channel already exists
        existing = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if existing:
            return False
        
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_link=channel_link,
            added_by=added_by
        )
        session.add(channel)
        return True


def remove_channel(channel_db_id: int) -> bool:
    """Remove a required channel by database ID"""
    with session_manager() as session:
        channel = session.query(Channel).filter(Channel.id == channel_db_id).first()
        if channel:
            session.delete(channel)
            return True
        return False


def get_required_channels() -> List[dict]:
    """Get all required channels"""
    with session_manager() as session:
        channels = session.query(Channel).filter(Channel.is_active == True).all()
        return [
            {
                'id': ch.id,
                'channel_id': ch.channel_id,
                'channel_name': ch.channel_name,
                'channel_link': ch.channel_link,
                'added_by': ch.added_by,
                'created_at': ch.created_at
            }
            for ch in channels
        ]


def get_channel_by_id(channel_id: int) -> dict:
    """Get channel information by channel ID"""
    with session_manager() as session:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            return {
                'id': channel.id,
                'channel_id': channel.channel_id,
                'channel_name': channel.channel_name,
                'added_by': channel.added_by,
                'created_at': channel.created_at,
                'is_active': channel.is_active
            }
        return None


# Access Control Functions
def check_user_access(uid: int, admins: List[int] = None) -> dict:
    """
    Check if user has access to the bot
    Returns: {
        'has_access': bool,
        'reason': str,  # 'admin', 'whitelisted', 'channel_member', 'banned', 'no_access'
        'user_status': int
    }
    """
    # Check if user is banned
    user_status = get_user_access_status(uid)
    if user_status == -1:
        return {'has_access': False, 'reason': 'banned', 'user_status': user_status}
    
    # Check if user is admin
    if admins and uid in admins:
        return {'has_access': True, 'reason': 'admin', 'user_status': user_status}
    
    # Check if user is whitelisted
    if user_status == 1:
        return {'has_access': True, 'reason': 'whitelisted', 'user_status': user_status}
    
    # For normal users (status 0), they need channel membership
    return {'has_access': False, 'reason': 'needs_channel_check', 'user_status': user_status}


def get_user_info(uid: int) -> dict:
    """Get comprehensive user information"""
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == uid).first()
        if user:
            return {
                'user_id': user.user_id,
                'access_status': user.access_status,
                'access_status_text': {
                    -1: 'Banned',
                    0: 'Normal',
                    1: 'Whitelisted'
                }.get(user.access_status, 'Unknown'),
                'has_settings': user.settings is not None,
                'config': user.config
            }
        return None


def get_platform_quality_setting(tgid: int) -> str:
    """Get user's platform quality setting: 'highest' or 'balanced'"""
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == tgid).first()
        if user and user.settings:
            return user.settings.platform_quality
        return "balanced"


def set_platform_quality_setting(tgid: int, quality: str):
    """Set user's platform quality setting"""
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == tgid).first()
        if not user:
            init_user(tgid)
            user = session.query(User).filter(User.user_id == tgid).first()
        
        setting = session.query(Setting).filter(Setting.user_id == user.id).first()
        if setting:
            setting.platform_quality = quality
        else:
            session.add(Setting(user_id=user.id, platform_quality=quality))


def store_youtube_session(user_id: int, message_id: int, url: str, formats: dict):
    """Store YouTube format selection session"""
    with session_manager() as session:
        # Remove any existing session for this user
        session.query(YouTubeFormatSession).filter(YouTubeFormatSession.user_id == user_id).delete()
        
        # Create new session
        youtube_session = YouTubeFormatSession(
            user_id=user_id,
            message_id=message_id,
            url=url,
            available_formats=formats
        )
        session.add(youtube_session)


def get_youtube_session(user_id: int) -> dict:
    """Get YouTube format selection session"""
    with session_manager() as session:
        youtube_session = session.query(YouTubeFormatSession).filter(
            YouTubeFormatSession.user_id == user_id
        ).first()
        
        if youtube_session:
            return {
                'message_id': youtube_session.message_id,
                'url': youtube_session.url,
                'available_formats': youtube_session.available_formats
            }
        return None


def clear_youtube_session(user_id: int):
    """Clear YouTube format selection session"""
    with session_manager() as session:
        session.query(YouTubeFormatSession).filter(YouTubeFormatSession.user_id == user_id).delete()


# Statistics tracking functions
def log_download_attempt(user_id: int, url: str, platform: str, format_requested: str = None):
    """Log a download attempt"""
    try:
        with session_manager() as session:
            download_stat = DownloadStats(
                user_id=user_id,
                url=url,
                platform=platform,
                format_requested=format_requested,
                timestamp=datetime.utcnow()
            )
            session.add(download_stat)
            session.commit()
            return download_stat.id
    except Exception as e:
        logging.error(f"Error logging download attempt: {e}")
        return None


def log_download_completion(download_id: int, success: bool, file_size: int = None, 
                          duration: float = None, error_message: str = None,
                          video_quality: str = None, audio_quality: str = None):
    """Log download completion with results"""
    try:
        with session_manager() as session:
            download_stat = session.query(DownloadStats).filter(DownloadStats.id == download_id).first()
            if download_stat:
                download_stat.success = success
                download_stat.file_size = file_size
                download_stat.duration = duration
                download_stat.error_message = error_message
                download_stat.video_quality = video_quality
                download_stat.audio_quality = audio_quality
                
                # Calculate download speed if we have both size and duration
                if file_size and duration and duration > 0:
                    download_stat.download_speed = (file_size / (1024 * 1024)) / duration  # MB/s
                
                session.commit()
    except Exception as e:
        logging.error(f"Error logging download completion: {e}")


def log_user_activity(user_id: int, activity_type: str, details: dict = None):
    """Log user activity"""
    try:
        with session_manager() as session:
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                details=details,
                timestamp=datetime.utcnow()
            )
            session.add(activity)
            session.commit()
    except Exception as e:
        logging.error(f"Error logging user activity: {e}")


def log_system_stats(cpu_usage: float, memory_usage: float, disk_usage: float):
    """Log system performance statistics"""
    try:
        with session_manager() as session:
            # Calculate additional metrics
            now = datetime.utcnow()
            hour_ago = now.replace(minute=0, second=0, microsecond=0)
            
            # Active users in last hour
            active_users = session.query(UserActivity).filter(
                UserActivity.timestamp >= hour_ago
            ).distinct(UserActivity.user_id).count()
            
            # Downloads per hour
            downloads_per_hour = session.query(DownloadStats).filter(
                DownloadStats.timestamp >= hour_ago
            ).count()
            
            # Error rate
            failed_downloads = session.query(DownloadStats).filter(
                DownloadStats.timestamp >= hour_ago,
                DownloadStats.success == False
            ).count()
            
            error_rate = (failed_downloads / downloads_per_hour * 100) if downloads_per_hour > 0 else 0
            
            system_stat = SystemStats(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                active_users=active_users,
                downloads_per_hour=downloads_per_hour,
                error_rate=error_rate,
                timestamp=now
            )
            session.add(system_stat)
            session.commit()
    except Exception as e:
        logging.error(f"Error logging system stats: {e}")


def get_download_statistics(days: int = 7) -> dict:
    """Get download statistics for the last N days"""
    try:
        with session_manager() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total downloads
            total_downloads = session.query(DownloadStats).filter(
                DownloadStats.timestamp >= start_date
            ).count()
            
            # Successful downloads
            successful_downloads = session.query(DownloadStats).filter(
                DownloadStats.timestamp >= start_date,
                DownloadStats.success == True
            ).count()
            
            # Failed downloads
            failed_downloads = total_downloads - successful_downloads
            
            # Success rate
            success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
            
            # Platform breakdown
            platform_stats = session.query(
                DownloadStats.platform,
                session.query(DownloadStats).filter(
                    DownloadStats.timestamp >= start_date,
                    DownloadStats.platform == DownloadStats.platform
                ).count().label('count')
            ).filter(DownloadStats.timestamp >= start_date).group_by(DownloadStats.platform).all()
            
            # Average file size
            avg_file_size = session.query(DownloadStats.file_size).filter(
                DownloadStats.timestamp >= start_date,
                DownloadStats.file_size.isnot(None)
            ).all()
            
            avg_size = sum(size[0] for size in avg_file_size) / len(avg_file_size) if avg_file_size else 0
            
            return {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'success_rate': round(success_rate, 2),
                'platform_stats': {platform: count for platform, count in platform_stats},
                'average_file_size': avg_size,
                'period_days': days
            }
    except Exception as e:
        logging.error(f"Error getting download statistics: {e}")
        return {}


def get_user_activity_statistics(days: int = 7) -> dict:
    """Get user activity statistics for the last N days"""
    try:
        with session_manager() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Active users
            active_users = session.query(UserActivity.user_id).filter(
                UserActivity.timestamp >= start_date
            ).distinct().count()
            
            # Activity breakdown
            activity_stats = session.query(
                UserActivity.activity_type,
                session.query(UserActivity).filter(
                    UserActivity.timestamp >= start_date,
                    UserActivity.activity_type == UserActivity.activity_type
                ).count().label('count')
            ).filter(UserActivity.timestamp >= start_date).group_by(UserActivity.activity_type).all()
            
            # Daily active users
            daily_users = {}
            for i in range(days):
                day_start = datetime.utcnow() - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_users = session.query(UserActivity.user_id).filter(
                    UserActivity.timestamp >= day_start,
                    UserActivity.timestamp < day_end
                ).distinct().count()
                
                daily_users[day_start.strftime('%Y-%m-%d')] = day_users
            
            return {
                'active_users': active_users,
                'activity_breakdown': {activity: count for activity, count in activity_stats},
                'daily_active_users': daily_users,
                'period_days': days
            }
    except Exception as e:
        logging.error(f"Error getting user activity statistics: {e}")
        return {}
