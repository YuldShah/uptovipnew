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
