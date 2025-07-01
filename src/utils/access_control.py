#!/usr/bin/env python3
# coding: utf-8

import asyncio
import logging
from typing import List, Tuple

from pyrogram import Client
from pyrogram.errors import FloodWait, UserNotParticipant, ChannelPrivate, ChatAdminRequired

from config.config import ADMIN_IDS, ACCESS_CONTROL_ENABLED
from database.model import check_user_access, get_required_channels

logger = logging.getLogger(__name__)


def get_admin_list() -> List[int]:
    """Get list of admin user IDs from environment"""
    if not ADMIN_IDS:
        return []
    
    try:
        return [int(uid.strip()) for uid in ADMIN_IDS.split(",") if uid.strip().isdigit()]
    except (ValueError, AttributeError):
        logger.error("Invalid ADMIN_IDS format in environment")
        return []


def get_env_required_channels() -> List[int]:
    """Get list of required channel IDs from database only"""
    # Channels are now managed through admin interface, not environment
    return []


async def check_channel_membership(client: Client, user_id: int, channel_id: int) -> bool:
    """Check if user is a member of a specific channel"""
    max_retries = 3
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            # Consider all non-kicked statuses as membership
            return member.status not in ["kicked", "banned"]
        except UserNotParticipant:
            return False
        except (ChannelPrivate, ChatAdminRequired):
            logger.error(f"SECURITY: Bot cannot access channel {channel_id} - lacks permissions. Denying access for user {user_id}")
            log_channel_access_issue(channel_id, "PERMISSION_DENIED", "Bot lacks admin access to channel")
            return False  # Fail secure - deny access when can't verify
        except FloodWait as e:
            if retry_count >= max_retries:
                logger.error(f"SECURITY: Max retries ({max_retries}) reached for FloodWait in channel {channel_id} membership check for user {user_id}")
                log_channel_access_issue(channel_id, "REPEATED_FLOOD_WAIT", f"Max retries reached, last wait: {e.value}s")
                return False  # Fail secure - deny access after max retries
            
            logger.warning(f"FloodWait {e.value} seconds for channel membership check (attempt {retry_count + 1}/{max_retries + 1})")
            await asyncio.sleep(e.value)
            retry_count += 1
        except Exception as e:
            logger.error(f"SECURITY: Unexpected error checking membership for user {user_id} in channel {channel_id}: {e}")
            log_channel_access_issue(channel_id, "UNEXPECTED_ERROR", str(e))
            return False  # Fail secure - deny access on unexpected errors
    
    # This should not be reached due to the loop structure, but included for safety
    logger.error(f"SECURITY: Unexpected code path reached in channel membership check for user {user_id}, channel {channel_id}")
    return False  # Fail secure


async def check_user_channel_access(client: Client, user_id: int) -> Tuple[bool, List[int]]:
    """
    Check if user is member of ANY required channel
    Returns: (has_access, list_of_missing_channels)
    """
    # Get channels from database only (managed by admins)
    db_channels = [ch['channel_id'] for ch in get_required_channels()]
    
    if not db_channels:
        return True, []  # No channels required
    
    missing_channels = []
    
    for channel_id in db_channels:
        is_member = await check_channel_membership(client, user_id, channel_id)
        if is_member:
            return True, []  # User is member of at least one channel
        else:
            missing_channels.append(channel_id)
    
    return False, missing_channels


async def check_full_user_access(client: Client, user_id: int) -> dict:
    """
    Comprehensive access check for a user
    Returns: {
        'has_access': bool,
        'reason': str,
        'user_status': int,
        'missing_channels': list,
        'is_admin': bool
    }
    """
    if not ACCESS_CONTROL_ENABLED:
        return {
            'has_access': True,
            'reason': 'access_control_disabled',
            'user_status': 0,
            'missing_channels': [],
            'is_admin': False
        }
    
    admins = get_admin_list()
    is_admin = user_id in admins
    
    # Basic access check (admin, whitelist, banned)
    basic_check = check_user_access(user_id, admins)
    
    if basic_check['has_access']:
        return {
            'has_access': True,
            'reason': basic_check['reason'],
            'user_status': basic_check['user_status'],
            'missing_channels': [],
            'is_admin': is_admin
        }
    
    if basic_check['reason'] == 'banned':
        return {
            'has_access': False,
            'reason': 'banned',
            'user_status': basic_check['user_status'],
            'missing_channels': [],
            'is_admin': is_admin
        }
    
    # Check channel membership for normal users
    if basic_check['reason'] == 'needs_channel_check':
        has_channel_access, missing_channels = await check_user_channel_access(client, user_id)
        
        if has_channel_access:
            return {
                'has_access': True,
                'reason': 'channel_member',
                'user_status': basic_check['user_status'],
                'missing_channels': [],
                'is_admin': is_admin
            }
        else:
            return {
                'has_access': False,
                'reason': 'no_channel_membership',
                'user_status': basic_check['user_status'],
                'missing_channels': missing_channels,
                'is_admin': is_admin
            }
    
    return {
        'has_access': False,
        'reason': 'unknown',
        'user_status': basic_check['user_status'],
        'missing_channels': [],
        'is_admin': is_admin
    }


def get_access_denied_message(access_result: dict) -> str:
    """Generate appropriate access denied message"""
    reason = access_result.get('reason', 'unknown')
    
    if reason == 'banned':
        return "❌ **Access Denied**\n\nYou have been banned from using this bot."
    
    elif reason == 'no_channel_membership':
        missing_channels = access_result.get('missing_channels', [])
        if missing_channels:
            channel_list = '\n'.join([f"• Channel ID: `{ch_id}`" for ch_id in missing_channels[:5]])
            return (
                "🔒 **Access Denied**\n\n"
                "You need to be a member of at least one of the required channels to use this bot.\n\n"
                f"**Required Channels:**\n{channel_list}"
                f"{' and more...' if len(missing_channels) > 5 else ''}\n\n"
                "Please join any of the required channels and try again.\n\n"
                "⚠️ _Note: If you believe you are already a member of a required channel, "
                "there may be a technical issue. Please contact an administrator._"
            )
        else:
            return (
                "🔒 **Access Denied**\n\n"
                "You need to be a member of at least one required channel to use this bot.\n"
                "Please contact an administrator for more information.\n\n"
                "⚠️ _There may be a technical issue with channel verification._"
            )
    
    else:
        return (
            "❌ **Access Denied**\n\n"
            "You don't have permission to use this bot.\n"
            "Please contact an administrator if you believe this is an error.\n\n"
            "⚠️ _If this issue persists, there may be a technical problem that requires admin attention._"
        )


def log_channel_access_issue(channel_id: int, issue_type: str, details: str = ""):
    """Log channel access issues for admin attention"""
    logger.critical(
        f"CHANNEL ACCESS ISSUE - ID: {channel_id}, TYPE: {issue_type}, "
        f"DETAILS: {details}, ACTION: Admin review required"
    )
    # In a real implementation, you might also:
    # - Send notification to admin chat
    # - Store in database for admin dashboard
    # - Send email notification


async def is_admin(client: Client, user_id: int) -> bool:
    """Simple admin check function"""
    admins = get_admin_list()
    return user_id in admins
