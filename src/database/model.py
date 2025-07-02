#!/usr/bin/env python3
# coding: utf-8

import logging
import math
import os
from contextlib import contextmanager
from typing import Literal, List
from datetime import datetime

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
    func,
    desc,
    distinct,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.attributes import flag_modified


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)  # telegram user id
    access_status = Column(Integer, default=0)  # -1: banned, 0: normal, 1: whitelisted
    config = Column(JSON)

    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan", uselist=False)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quality = Column(Enum("high", "medium", "low", "audio", "custom", name="quality_enum"), nullable=False, default="high")
    format = Column(Enum("video", "audio", "document", name="format_enum"), nullable=False, default="video")
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


class DownloadStats(Base):
    __tablename__ = "download_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    platform = Column(String, nullable=False)  # youtube, instagram, pixeldrain, etc.
    url = Column(String, nullable=False)
    success = Column(Boolean, nullable=False)
    file_size = Column(BigInteger, nullable=True)  # in bytes
    download_time = Column(Float, nullable=True)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)


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
    # set quality or format settings with validation
    
    # Validate enum values
    valid_quality = ["high", "medium", "low", "audio", "custom"]
    valid_format = ["video", "audio", "document"]
    
    if key == "quality" and value not in valid_quality:
        logging.warning(f"Invalid quality value '{value}' for user {tgid}. Ignoring.")
        return False
        
    if key == "format" and value not in valid_format:
        logging.warning(f"Invalid format value '{value}' for user {tgid}. Ignoring.")
        return False
    
    with session_manager() as session:
        # find user first
        user = session.query(User).filter(User.user_id == tgid).first()
        if not user:
            # Create user if doesn't exist
            user = User(user_id=tgid)
            session.add(user)
            session.flush()  # Get the user ID
            
        # upsert setting
        setting = session.query(Setting).filter(Setting.user_id == user.id).first()
        if setting:
            setattr(setting, key, value)
        else:
            session.add(Setting(user_id=user.id, **{key: value}))
    
    return True


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
    
    # Check if user is whitelisted (manual access)
    if user_status == 1:
        return {'has_access': True, 'reason': 'whitelisted', 'user_status': user_status}
    
    # For normal users (status 0), they need channel membership
    return {'has_access': False, 'reason': 'needs_channel_check', 'user_status': user_status}


async def check_channel_membership(client, uid: int) -> dict:
    """
    Check if user is member of ANY required channel (not ALL)
    Returns: {
        'is_member': bool,
        'channels_checked': int,
        'member_of': List[str],  # channel names user is member of
        'required_channels': List[dict]
    }
    """
    try:
        required_channels = get_required_channels()
        if not required_channels:
            # No required channels = everyone has access
            return {
                'is_member': True,
                'channels_checked': 0,
                'member_of': [],
                'required_channels': []
            }
        
        member_of = []
        
        for channel in required_channels:
            try:
                # Try to get user's membership status
                member = await client.get_chat_member(channel['channel_id'], uid)
                if member.status in ['creator', 'administrator', 'member']:
                    member_of.append(channel['channel_name'] or str(channel['channel_id']))
                    # User is member of at least one channel - grant access
                    return {
                        'is_member': True,
                        'channels_checked': len(required_channels),
                        'member_of': member_of,
                        'required_channels': required_channels
                    }
            except Exception as e:
                # User is not a member or channel is inaccessible
                logging.debug(f"User {uid} not member of channel {channel['channel_id']}: {e}")
                continue
        
        # User is not member of any required channel
        return {
            'is_member': False,
            'channels_checked': len(required_channels),
            'member_of': member_of,
            'required_channels': required_channels
        }
        
    except Exception as e:
        logging.error(f"Error checking channel membership for user {uid}: {e}")
        return {
            'is_member': False,
            'channels_checked': 0,
            'member_of': [],
            'required_channels': []
        }


async def check_full_user_access(client, uid: int, admins: List[int] = None) -> dict:
    """
    Complete access check including channel membership
    """
    # First check user status and admin
    basic_check = check_user_access(uid, admins)
    
    if basic_check['reason'] in ['admin', 'whitelisted', 'banned']:
        return basic_check
    
    # Need to check channel membership
    channel_check = await check_channel_membership(client, uid)
    
    if channel_check['is_member']:
        return {
            'has_access': True,
            'reason': 'channel_member',
            'user_status': basic_check['user_status'],
            'channel_info': channel_check
        }
    else:
        return {
            'has_access': False,
            'reason': 'no_channel_membership',
            'user_status': basic_check['user_status'],
            'channel_info': channel_check
        }


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


def get_user_platform_quality(uid: int, platform: str = 'youtube') -> str:
    """Get user's quality preference for specific platform"""
    quality = get_quality_settings(uid)
    return quality


def set_user_platform_quality(uid: int, quality: str, platform: str = 'youtube') -> bool:
    """Set user's quality preference for specific platform"""
    return set_user_settings(uid, quality=quality)


def create_youtube_format_session(uid: int, url: str, formats: dict) -> bool:
    """Create a YouTube format selection session for user"""
    import time
    import uuid
    import logging
    
    with session_manager() as session:
        # First, delete any existing session for this user to prevent contamination
        user = session.query(User).filter(User.user_id == uid).first()
        if user and user.config:
            # Clear any existing YouTube session data
            user.config.pop('youtube_formats', None)
            user.config.pop('youtube_url', None)
            user.config.pop('youtube_session_time', None)
            user.config.pop('youtube_session_id', None)
            session.flush()  # Ensure the deletion is applied
            logging.info(f"[SESSION_CREATE] User {uid}: Cleared existing session data")
        
        if not user:
            user = User(user_id=uid, config={})
            session.add(user)
        
        if not user.config:
            user.config = {}
        
        # Create a unique session ID for this format selection
        session_id = uuid.uuid4().hex[:8]
        current_time = time.time()
        
        # Set new session data
        user.config['youtube_formats'] = formats
        user.config['youtube_url'] = url
        user.config['youtube_session_time'] = current_time
        user.config['youtube_session_id'] = session_id
        
        # Mark the user as dirty to force SQLAlchemy to update
        flag_modified(user, 'config')
        
        # Force flush and commit to ensure data is saved immediately
        session.flush()
        session.commit()
        
        # Verify the data was actually saved by re-querying
        session.refresh(user)
        actual_url = user.config.get('youtube_url', 'NOT_FOUND')
        actual_session_id = user.config.get('youtube_session_id', 'NOT_FOUND')
        
        logging.info(f"[SESSION_CREATE] User {uid}: URL={url}, session_id={session_id}, time={current_time}")
        logging.info(f"[SESSION_CREATE] User {uid}: Verification - actual_url={actual_url}, actual_session_id={actual_session_id}")
        
        if actual_url != url:
            logging.error(f"[SESSION_CREATE] User {uid}: CRITICAL - URL mismatch! Expected {url}, got {actual_url}")
            return False
            
        return True


def get_youtube_format_session(uid: int) -> dict:
    """Get YouTube format selection session for user"""
    import time
    import logging
    
    with session_manager() as session:
        # Use a fresh query to ensure we get the latest data
        user = session.query(User).filter(User.user_id == uid).first()
        
        if user and user.config and 'youtube_formats' in user.config and 'youtube_url' in user.config:
            # Check if session is stale (older than 30 minutes)
            session_time = user.config.get('youtube_session_time', 0)
            current_time = time.time()
            time_diff = current_time - session_time
            
            logging.info(f"[SESSION_RETRIEVE] User {uid}: session_time={session_time}, current_time={current_time}, diff={time_diff} seconds")
            logging.info(f"[SESSION_RETRIEVE] User {uid}: Found session_id={user.config.get('youtube_session_id', 'unknown')}")
            logging.info(f"[SESSION_RETRIEVE] User {uid}: URL in session={user.config['youtube_url']}")
            logging.info(f"[SESSION_RETRIEVE] User {uid}: Config keys={list(user.config.keys())}")
            
            # TEMPORARILY DISABLE EXPIRY CHECK FOR DEBUGGING
            # if time_diff > 1800:  # 30 minutes
            #     logging.info(f"Session expired for user {uid} (age: {time_diff} seconds)")
            #     # Clean up stale session
            #     if 'youtube_formats' in user.config:
            #         del user.config['youtube_formats']
            #     if 'youtube_url' in user.config:
            #         del user.config['youtube_url']
            #     if 'youtube_session_time' in user.config:
            #         del user.config['youtube_session_time']
            #     if 'youtube_session_id' in user.config:
            #         del user.config['youtube_session_id']
            #     flag_modified(user, 'config')
            #     session.commit()
            #     return {}
                
            logging.info(f"[SESSION_RETRIEVE] Session valid for user {uid}, returning session data for URL: {user.config['youtube_url']}")
            return {
                'formats': user.config['youtube_formats'],
                'url': user.config['youtube_url'],
                'session_id': user.config.get('youtube_session_id', 'unknown')
            }
        
        logging.info(f"[SESSION_RETRIEVE] No session found for user {uid}")
        if user and user.config:
            logging.info(f"[SESSION_RETRIEVE] User {uid} config keys: {list(user.config.keys())}")
        return {}


def delete_youtube_format_session(uid: int) -> bool:
    """Delete YouTube format selection session for user"""
    import logging
    with session_manager() as session:
        user = session.query(User).filter(User.user_id == uid).first()
        if user and user.config:
            # Log what's being deleted
            url_being_deleted = user.config.get('youtube_url', 'NO_URL')
            session_id_being_deleted = user.config.get('youtube_session_id', 'NO_SESSION_ID')
            logging.info(f"[SESSION_DELETE] User {uid}: Deleting session with URL={url_being_deleted}, session_id={session_id_being_deleted}")
            
            deleted = False
            if 'youtube_formats' in user.config:
                del user.config['youtube_formats']
                deleted = True
            if 'youtube_url' in user.config:
                del user.config['youtube_url']
                deleted = True
            if 'youtube_session_time' in user.config:
                del user.config['youtube_session_time']
                deleted = True
            if 'youtube_session_id' in user.config:
                del user.config['youtube_session_id']
                deleted = True
            
            if deleted:
                flag_modified(user, 'config')
                session.commit()
                logging.info(f"[SESSION_DELETE] User {uid}: Session deleted and committed")
            return deleted
        
        logging.info(f"[SESSION_DELETE] User {uid}: No session found to delete")
        return False


def log_user_activity(uid: int, activity: str, details: dict = None) -> bool:
    """Log user activity (simplified implementation)"""
    logging.info(f"User {uid} activity: {activity} - {details}")
    return True


def log_download_attempt(uid: int, url: str, format_requested: str = None) -> int:
    """Log download attempt and return ID for tracking"""
    logging.info(f"User {uid} download attempt: {url} (format: {format_requested})")
    # For now, return a simple ID - we'll enhance this later
    return True


def log_download_completion(uid: int, url: str, success: bool, file_size: int = None, platform: str = None, download_time: float = None) -> bool:
    """Log download completion with statistics"""
    try:
        with session_manager() as session:
            stats = DownloadStats(
                user_id=uid,
                platform=platform or 'unknown',
                url=url,
                success=success,
                file_size=file_size,
                download_time=download_time
            )
            session.add(stats)
            
        status = "success" if success else "failed"
        logging.info(f"User {uid} download {status}: {url} (size: {file_size}, time: {download_time}s)")
        return True
    except Exception as e:
        logging.error(f"Failed to log download completion: {e}")
        return False


def get_download_statistics() -> dict:
    """Get comprehensive download statistics"""
    try:
        with session_manager() as session:
            from sqlalchemy import func, distinct
            
            # Total stats
            total_downloads = session.query(DownloadStats).count()
            successful_downloads = session.query(DownloadStats).filter(DownloadStats.success == True).count()
            
            # Platform stats - fixed SQL query
            platform_stats = session.query(
                DownloadStats.platform,
                func.count(DownloadStats.id).label('count'),
                func.avg(DownloadStats.download_time).label('avg_time'),
                func.sum(DownloadStats.file_size).label('total_size')
            ).group_by(DownloadStats.platform).all()
            
            # User stats
            total_users = session.query(User).count()
            active_users = session.query(distinct(DownloadStats.user_id)).count()
            whitelisted_users = session.query(User).filter(User.access_status == 1).count()
            banned_users = session.query(User).filter(User.access_status == -1).count()
            
            # Recent stats (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_downloads = session.query(DownloadStats).filter(DownloadStats.created_at >= yesterday).count()
            recent_users = session.query(distinct(DownloadStats.user_id)).filter(DownloadStats.created_at >= yesterday).count()
            
            return {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': total_downloads - successful_downloads,
                'success_rate': round((successful_downloads / total_downloads * 100), 2) if total_downloads > 0 else 0,
                'total_users': total_users,
                'active_users': active_users,
                'whitelisted_users': whitelisted_users,
                'banned_users': banned_users,
                'normal_users': total_users - whitelisted_users - banned_users,
                'recent_downloads_24h': recent_downloads,
                'recent_users_24h': recent_users,
                'platform_stats': {
                    stat.platform: {
                        'count': stat.count,
                        'avg_time': round(stat.avg_time or 0, 2),
                        'total_size': stat.total_size or 0,
                        'avg_size': round((stat.total_size or 0) / stat.count / 1024 / 1024, 2) if stat.count > 0 else 0  # MB
                    } for stat in platform_stats
                }
            }
    except Exception as e:
        logging.error(f"Failed to get download statistics: {e}")
        return {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'success_rate': 0,
            'total_users': 0,
            'active_users': 0,
            'whitelisted_users': 0,
            'banned_users': 0,
            'normal_users': 0,
            'recent_downloads_24h': 0,
            'recent_users_24h': 0,
            'platform_stats': {}
        }


def get_user_download_stats(uid: int) -> dict:
    """Get download statistics for specific user"""
    try:
        with session_manager() as session:
            from sqlalchemy import func
            
            user_stats = session.query(
                func.count(DownloadStats.id).label('total'),
                func.count(DownloadStats.id).filter(DownloadStats.success == True).label('successful'),
                func.avg(DownloadStats.download_time).label('avg_time'),
                func.sum(DownloadStats.file_size).label('total_size')
            ).filter(DownloadStats.user_id == uid).first()
            
            platform_stats = session.query(
                DownloadStats.platform,
                func.count(DownloadStats.id).label('count')
            ).filter(DownloadStats.user_id == uid).group_by(DownloadStats.platform).all()
            
            return {
                'total_downloads': user_stats.total or 0,
                'successful_downloads': user_stats.successful or 0,
                'success_rate': round((user_stats.successful / user_stats.total * 100), 2) if user_stats.total > 0 else 0,
                'avg_download_time': round(user_stats.avg_time or 0, 2),
                'total_downloaded_size': user_stats.total_size or 0,
                'platform_breakdown': {stat.platform: stat.count for stat in platform_stats}
            }
    except Exception as e:
        logging.error(f"Failed to get user download statistics for {uid}: {e}")
        return {
            'total_downloads': 0,
            'successful_downloads': 0,
            'success_rate': 0,
            'avg_download_time': 0,
            'total_downloaded_size': 0,
            'platform_breakdown': {}
        }


def get_top_users(limit: int = 10) -> list:
    """Get top users by download count"""
    try:
        with session_manager() as session:
            from sqlalchemy import func, desc
            
            top_users = session.query(
                DownloadStats.user_id,
                func.count(DownloadStats.id).label('download_count'),
                func.count(DownloadStats.id).filter(DownloadStats.success == True).label('successful_count')
            ).group_by(DownloadStats.user_id).order_by(desc('download_count')).limit(limit).all()
            
            return [
                {
                    'user_id': user.user_id,
                    'download_count': user.download_count,
                    'successful_count': user.successful_count,
                    'success_rate': round((user.successful_count / user.download_count * 100), 2) if user.download_count > 0 else 0
                }
                for user in top_users
            ]
    except Exception as e:
        logging.error(f"Failed to get top users: {e}")
        return []


def search_users(search_term: str = None, status_filter: int = None, limit: int = 50) -> list:
    """Search users by ID or status"""
    try:
        with session_manager() as session:
            query = session.query(User)
            
            # Filter by status if provided
            if status_filter is not None:
                query = query.filter(User.access_status == status_filter)
            
            # Filter by user ID if search term is numeric
            if search_term and search_term.isdigit():
                query = query.filter(User.user_id == int(search_term))
            
            users = query.limit(limit).all()
            
            result = []
            for user in users:
                # Get download count for each user
                download_count = session.query(DownloadStats).filter(DownloadStats.user_id == user.user_id).count()
                
                result.append({
                    'user_id': user.user_id,
                    'access_status': user.access_status,
                    'access_status_text': {
                        -1: 'Banned',
                        0: 'Normal',
                        1: 'Whitelisted'
                    }.get(user.access_status, 'Unknown'),
                    'download_count': download_count,
                    'has_settings': user.settings is not None
                })
            
            return result
    except Exception as e:
        logging.error(f"Failed to search users: {e}")
        return []
