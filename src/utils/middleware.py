#!/usr/bin/env python3
# coding: utf-8

import logging
from typing import Union

from pyrogram import Client, types, enums
from pyrogram.types import Message, CallbackQuery

from utils.access_control import check_full_user_access, get_access_denied_message, get_admin_list
from database.model import init_user, get_required_channels

logger = logging.getLogger(__name__)


async def access_control_middleware(client: Client, update: Union[Message, CallbackQuery], handler_func=None):
    """
    Comprehensive access control middleware for all user interactions.
    
    This middleware:
    1. Initializes new users in database
    2. Checks access permissions (admin, whitelist, banned, channel membership)
    3. Blocks access for unauthorized users
    4. Provides appropriate error messages
    5. Allows admins full access
    """
    
    # Extract user info
    if isinstance(update, Message):
        user = update.from_user
        chat = update.chat
    elif isinstance(update, CallbackQuery):
        user = update.from_user
        chat = update.message.chat if update.message else None
    else:
        return  # Unknown update type
    
    if not user:
        return  # No user info
    
    user_id = user.id
    
    # Only process private chats
    if chat and chat.type != enums.ChatType.PRIVATE:
        logger.debug(f"Ignoring non-private chat: {chat.type}")
        return
    
    # Initialize user in database if needed
    try:
        init_user(user_id)
    except Exception as e:
        logger.error(f"Failed to initialize user {user_id}: {e}")
    
    # Check user access
    try:
        access_result = await check_full_user_access(client, user_id)
        
        if not access_result['has_access']:
            # User doesn't have access - send denial message
            denial_message = get_access_denied_message(access_result)
            
            if isinstance(update, Message):
                await update.reply(denial_message, quote=True)
            elif isinstance(update, CallbackQuery):
                await update.answer("❌ Access denied", show_alert=True)
                # Also send a message explaining the denial
                if update.message:
                    try:
                        await update.message.edit_text(denial_message)
                    except:
                        await client.send_message(user_id, denial_message)
            
            logger.info(f"Access denied for user {user_id}: {access_result['reason']}")
            return  # Block the handler from executing
        
        # User has access - log and continue
        logger.debug(f"Access granted for user {user_id}: {access_result['reason']}")
        
        # Add access info to update for handler use
        if hasattr(update, '_access_info'):
            update._access_info = access_result
        else:
            setattr(update, '_access_info', access_result)
        
        # Continue to handler if provided
        if handler_func:
            return await handler_func(client, update)
    
    except Exception as e:
        logger.error(f"Error in access control middleware for user {user_id}: {e}")
        
        # In case of error, deny access to be safe
        error_message = (
            "❌ **Access Control Error**\n\n"
            "An error occurred while checking your access permissions. "
            "Please try again later or contact an administrator."
        )
        
        if isinstance(update, Message):
            await update.reply(error_message, quote=True)
        elif isinstance(update, CallbackQuery):
            await update.answer("❌ Access control error", show_alert=True)


def create_access_middleware(handler_func):
    """
    Decorator factory to create access control middleware for handlers.
    
    Usage:
        @create_access_middleware
        async def my_handler(client, message):
            # This handler will only execute if user has access
            pass
    """
    async def middleware_wrapper(client: Client, update: Union[Message, CallbackQuery]):
        return await access_control_middleware(client, update, handler_func)
    
    return middleware_wrapper


async def admin_only_middleware(client: Client, update: Union[Message, CallbackQuery], handler_func=None):
    """
    Middleware specifically for admin-only functions.
    """
    # Extract user info
    if isinstance(update, Message):
        user = update.from_user
    elif isinstance(update, CallbackQuery):
        user = update.from_user
    else:
        return
    
    if not user:
        return
    
    user_id = user.id
    admin_ids = get_admin_list()
    
    if user_id not in admin_ids:
        error_message = "❌ **Admin Only**\n\nThis feature is restricted to administrators only."
        
        if isinstance(update, Message):
            await update.reply(error_message, quote=True)
        elif isinstance(update, CallbackQuery):
            await update.answer("❌ Admin access required", show_alert=True)
        
        logger.warning(f"Non-admin user {user_id} attempted to access admin function")
        return
    
    # User is admin - continue to handler
    logger.debug(f"Admin access granted for user {user_id}")
    
    if handler_func:
        return await handler_func(client, update)


def admin_only(handler_func):
    """
    Decorator for admin-only handlers.
    
    Usage:
        @admin_only
        async def admin_handler(client, message):
            # This handler will only execute for admins
            pass
    """
    async def wrapper(client: Client, update: Union[Message, CallbackQuery]):
        return await admin_only_middleware(client, update, handler_func)
    
    return wrapper


async def get_channel_join_buttons():
    """
    Generate inline keyboard with buttons to join required channels.
    """
    channels = get_required_channels()
    if not channels:
        return None
    
    buttons = []
    for channel in channels[:5]:  # Limit to 5 channels to avoid button overflow
        channel_name = channel['channel_name'] or f"Channel {channel['channel_id']}"
        
        # Create join button with proper URL
        if channel.get('channel_link'):
            url = channel['channel_link']
        else:
            # Try to construct URL for channel ID
            channel_id_str = str(channel['channel_id'])
            if channel_id_str.startswith('-100'):
                # Remove -100 prefix for t.me/c/ links
                clean_id = channel_id_str[4:]
                url = f"https://t.me/c/{clean_id}"
            else:
                url = f"https://t.me/joinchat/{abs(channel['channel_id'])}"
        
        buttons.append([types.InlineKeyboardButton(f"📢 Join {channel_name}", url=url)])
    
    # Add refresh button
    buttons.append([types.InlineKeyboardButton("🔄 Check Access", callback_data="check_access")])
    
    return types.InlineKeyboardMarkup(buttons)


def get_comprehensive_denial_message(access_result: dict) -> tuple:
    """
    Get comprehensive denial message with join buttons if applicable.
    
    Returns:
        tuple: (message_text, inline_keyboard_or_none)
    """
    reason = access_result.get('reason', 'unknown')
    
    if reason == 'banned':
        message = (
            "❌ **Access Denied**\n\n"
            "Your account has been banned from using this bot.\n"
            "If you believe this is an error, please contact an administrator."
        )
        return message, None
    
    elif reason == 'no_channel_membership':
        channel_info = access_result.get('channel_info', {})
        required_channels = channel_info.get('required_channels', [])
        
        if required_channels:
            message = (
                "🔒 **Channel Membership Required**\n\n"
                "To use this bot, you need to be a member of **at least one** of the following channels:\n\n"
            )
            
            for i, channel in enumerate(required_channels[:5], 1):
                channel_name = channel['channel_name'] or f"Channel {channel['channel_id']}"
                message += f"{i}. **{channel_name}**\n"
            
            if len(required_channels) > 5:
                message += f"... and {len(required_channels) - 5} more channels\n"
            
            message += "\nPlease join any of the channels below and try again:"
            
            # Get join buttons
            keyboard = get_channel_join_buttons()
            return message, keyboard
        
        else:
            message = (
                "🔒 **Access Denied**\n\n"
                "Channel membership is required but no channels are configured.\n"
                "Please contact an administrator."
            )
            return message, None
    
    else:
        message = (
            "❌ **Access Denied**\n\n"
            "You don't have permission to use this bot.\n"
            "Please contact an administrator if you believe this is an error."
        )
        return message, None
