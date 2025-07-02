#!/usr/bin/env python3
# coding: utf-8

import re
import asyncio
import logging
from typing import List, Dict

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserNotParticipant, ChannelPrivate, ChatAdminRequired

from config.config import ADMIN_IDS
from database.model import (
    add_channel, remove_channel, get_required_channels, 
    set_user_access_status, get_user_access_status,
    session_manager, User
)
from utils.access_control import get_admin_list

logger = logging.getLogger(__name__)


def admin_only(func):
    """Decorator to restrict commands to admins only"""
    async def wrapper(client: Client, message: Message):
        admin_ids = get_admin_list()
        if message.from_user.id not in admin_ids:
            await message.reply("❌ This command is for administrators only.")
            return
        return await func(client, message)
    return wrapper


def admin_callback_only(func):
    """Decorator to restrict callbacks to admins only"""
    async def wrapper(client: Client, callback_query: CallbackQuery):
        admin_ids = get_admin_list()
        if callback_query.from_user.id not in admin_ids:
            await callback_query.answer("❌ This action is for administrators only.", show_alert=True)
            return
        return await func(client, callback_query)
    return wrapper


def create_access_menu():
    """Create main access management menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")],
        [InlineKeyboardButton("👤 Manual Access", callback_data="manual_access")],
        [InlineKeyboardButton("📊 Access Stats", callback_data="access_stats")],
        [InlineKeyboardButton("❌ Close", callback_data="close_admin")]
    ])


def create_channels_menu(channels: List[Dict]):
    """Create channels management menu"""
    keyboard = []
    
    if channels:
        keyboard.append([InlineKeyboardButton("🗑 Remove All Channels", callback_data="remove_all_channels")])
        keyboard.append([InlineKeyboardButton("─" * 20, callback_data="separator")])
        
        for channel in channels[:10]:  # Limit to 10 channels
            # Use helper function to construct proper channel URL
            channel_url = get_channel_url(channel)
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📢 {channel['channel_name'] or ('ID: ' + str(channel['channel_id']))}",
                    url=channel_url
                ),
                InlineKeyboardButton("🗑", callback_data=f"remove_channel_{channel['id']}")
            ])
    
    keyboard.extend([
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
        [InlineKeyboardButton("🔙 Back", callback_data="access_menu")]
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_manual_access_menu():
    """Create manual access management menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Whitelist User", callback_data="whitelist_user")],
        [InlineKeyboardButton("❌ Ban User", callback_data="ban_user")],
        [InlineKeyboardButton("🔍 Check User Status", callback_data="check_user")],
        [InlineKeyboardButton("🔙 Back", callback_data="access_menu")]
    ])


def create_confirm_keyboard(action: str, data: str = ""):
    """Create confirmation keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}_{data}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="access_menu")]
    ])


# Temporary storage for admin operations
admin_sessions = {}


@admin_only
async def admin_command(client: Client, message: Message):
    """Main admin command handler"""
    await message.reply(
        "🔧 **Admin Panel**\n\n"
        "Here you can manage bot access control:\n"
        "• Manage required channels\n"
        "• Manually whitelist/ban users\n"
        "• View access statistics",
        reply_markup=create_access_menu()
    )


@admin_callback_only
async def admin_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle admin panel callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "access_menu":
        await callback_query.edit_message_text(
            "🔧 **Admin Panel**\n\n"
            "Here you can manage bot access control:\n"
            "• Manage required channels\n"
            "• Manually whitelist/ban users\n"
            "• View access statistics",
            reply_markup=create_access_menu()
        )
    
    elif data == "manage_channels":
        channels = get_required_channels()
        channel_count = len(channels)
        
        text = "📢 **Channel Management**\n\n"
        if channels:
            text += f"Currently managing {channel_count} required channel(s).\n"
            text += "Users need to be members of **ANY** of these channels to access the bot.\n\n"
            for i, ch in enumerate(channels[:5], 1):
                text += f"{i}. {ch['channel_name'] or f'ID: {ch['channel_id']}'}\n"
            if channel_count > 5:
                text += f"... and {channel_count - 5} more\n"
        else:
            text += "No required channels set. All users (except banned) will have access.\n"
        
        await callback_query.edit_message_text(text, reply_markup=create_channels_menu(channels))
    
    elif data == "manual_access":
        await callback_query.edit_message_text(
            "👤 **Manual Access Management**\n\n"
            "You can manually control user access:\n"
            "• **Whitelist**: User gets access without channel membership\n"
            "• **Ban**: User is denied access regardless of channels\n"
            "• **Check**: View user's current access status",
            reply_markup=create_manual_access_menu()
        )
    
    elif data == "add_channel":
        admin_sessions[user_id] = {"action": "add_channel", "step": "waiting_forward"}
        await callback_query.edit_message_text(
            "📢 **Add Required Channel**\n\n"
            "Forward a message from the channel you want to add, or send the channel username/ID.\n\n"
            "**Supported formats:**\n"
            "• `@channelname`\n"
            "• `channelname`\n"
            "• `https://t.me/channelname`\n"
            "• `-1001234567890` (channel ID)\n\n"
            "**Note:** The bot must be an admin in the channel to verify membership.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="manage_channels")]])
        )
    
    elif data.startswith("remove_channel_"):
        channel_id = int(data.split("_")[2])
        admin_sessions[user_id] = {"action": "remove_channel", "channel_id": channel_id}
        
        # Get channel info
        channels = get_required_channels()
        channel = next((ch for ch in channels if ch['id'] == channel_id), None)
        
        if channel:
            await callback_query.edit_message_text(
                f"🗑 **Remove Channel**\n\n"
                f"Are you sure you want to remove this channel?\n\n"
                f"**Channel:** {channel['channel_name'] or ('ID: ' + str(channel['channel_id']))}\n\n"
                f"Users will no longer need to be members of this channel.",
                reply_markup=create_confirm_keyboard("remove_channel", str(channel_id))
            )
    
    elif data == "remove_all_channels":
        admin_sessions[user_id] = {"action": "remove_all_channels"}
        channels_count = len(get_required_channels())
        
        await callback_query.edit_message_text(
            f"🗑 **Remove All Channels**\n\n"
            f"⚠️ **Warning:** This will remove all {channels_count} required channels!\n\n"
            f"After this action, all users (except banned) will have access to the bot.\n\n"
            f"This action cannot be undone.",
            reply_markup=create_confirm_keyboard("remove_all_channels")
        )
    
    elif data.startswith("confirm_remove_channel_"):
        channel_id = int(data.split("_")[3])
        success = remove_channel(channel_id)
        
        if success:
            await callback_query.answer("✅ Channel removed successfully", show_alert=True)
        else:
            await callback_query.answer("❌ Failed to remove channel", show_alert=True)
        
        # Return to channels menu
        channels = get_required_channels()
        await callback_query.edit_message_text(
            "📢 **Channel Management**\n\n"
            f"Currently managing {len(channels)} required channel(s).",
            reply_markup=create_channels_menu(channels)
        )
    
    elif data == "confirm_remove_all_channels":
        # Remove all channels
        channels = get_required_channels()
        for channel in channels:
            remove_channel(channel['id'])
        
        await callback_query.answer("✅ All channels removed", show_alert=True)
        await callback_query.edit_message_text(
            "📢 **Channel Management**\n\n"
            "No required channels set. All users (except banned) will have access.",
            reply_markup=create_channels_menu([])
        )
    
    elif data in ["whitelist_user", "ban_user", "check_user"]:
        action_text = {
            "whitelist_user": "✅ **Whitelist User**\n\nSend the user ID or forward a message from the user you want to whitelist.",
            "ban_user": "❌ **Ban User**\n\nSend the user ID or forward a message from the user you want to ban.",
            "check_user": "🔍 **Check User Status**\n\nSend the user ID or forward a message from the user you want to check."
        }
        
        admin_sessions[user_id] = {"action": data, "step": "waiting_user"}
        await callback_query.edit_message_text(
            action_text[data],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="manual_access")]])
        )
    
    elif data == "access_stats":
        # Get basic stats
        with session_manager() as session:
            total_users = session.query(User).count()
            whitelisted = session.query(User).filter(User.access_status == 1).count()
            banned = session.query(User).filter(User.access_status == -1).count()
            normal = session.query(User).filter(User.access_status == 0).count()
        
        channels = get_required_channels()
        admin_count = len(get_admin_list())
        
        stats_text = (
            "📊 **Access Control Statistics**\n\n"
            f"👥 **Total Users:** {total_users}\n"
            f"✅ **Whitelisted:** {whitelisted}\n"
            f"❌ **Banned:** {banned}\n"
            f"👤 **Normal:** {normal}\n\n"
            f"📢 **Required Channels:** {len(channels)}\n"
            f"👨‍💼 **Administrators:** {admin_count}\n"
        )
        
        await callback_query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="access_menu")]])
        )
    
    elif data == "close_admin":
        await callback_query.message.delete()


async def handle_admin_message(client: Client, message: Message):
    """Handle admin session messages"""
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in get_admin_list():
        return
    
    # Check if user has active session
    if user_id not in admin_sessions:
        return
    
    session = admin_sessions[user_id]
    action = session.get("action")
    
    if action == "add_channel":
        await handle_add_channel_message(client, message, session)
    elif action in ["whitelist_user", "ban_user", "check_user"]:
        await handle_user_management_message(client, message, session)


def admin_session_filter(_, __, message):
    """Custom filter for admin messages with active sessions"""
    if not message.from_user:
        return False
    
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in get_admin_list():
        return False
    
    # Check if user has active session
    if user_id not in admin_sessions:
        return False
    
    # Don't process commands
    if message.text and message.text.startswith('/'):
        return False
    
    return True


# Create the custom filter
admin_session = filters.create(admin_session_filter)


async def handle_add_channel_message(client: Client, message: Message, session: dict):
    """Handle channel addition process"""
    user_id = message.from_user.id
    
    try:
        channel_id = None
        channel_name = None
        channel_link = None
        
        # Check if forwarded message
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_name = message.forward_from_chat.title
            if message.forward_from_chat.username:
                channel_link = f"https://t.me/{message.forward_from_chat.username}"
        
        # Check if text message with channel info
        elif message.text:
            text = message.text.strip()
            username = None  # Initialize username variable
            
            # Pattern matching for different formats
            if text.startswith("@"):
                username = text[1:]
                channel_link = f"https://t.me/{username}"
            elif text.startswith("https://t.me/"):
                username = text.replace("https://t.me/", "")
                channel_link = text
            elif re.match(r'^[a-zA-Z][\w\d_]{4,31}$', text):  # Username without @
                username = text
                channel_link = f"https://t.me/{text}"
            elif text.lstrip('-').isdigit():  # Channel ID
                channel_id = int(text)
            else:
                await message.reply("❌ Invalid format. Please try again with a valid channel username, ID, or forward a message.")
                return
            
            # Get chat info if we have username
            if not channel_id and username is not None:
                try:
                    chat = await client.get_chat(f"@{username}")
                    channel_id = chat.id
                    channel_name = chat.title
                except Exception as e:
                    await message.reply(f"❌ Could not find channel. Make sure the channel exists and the bot has access.\nError: {str(e)}")
                    return
        
        if not channel_id:
            await message.reply("❌ Could not determine channel ID. Please try again.")
            return
        
        # Verify bot can access the channel
        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title or channel_name
            
            # Try to get member count to verify bot access
            await client.get_chat_member_count(channel_id)
            
        except Exception as e:
            await message.reply(
                f"❌ Bot cannot access this channel.\n\n"
                f"Please make sure:\n"
                f"• The channel exists\n"
                f"• The bot is added as an admin\n"
                f"• The bot has permission to view members\n\n"
                f"Error: {str(e)}"
            )
            return
        
        # Add channel to database
        success = add_channel(channel_id, channel_name, channel_link, user_id)
        
        if success:
            await message.reply(
                f"✅ **Channel Added Successfully**\n\n"
                f"**Name:** {channel_name}\n"
                f"**ID:** `{channel_id}`\n"
                f"**Link:** {channel_link or 'Private channel'}\n\n"
                f"Users now need to be members of this channel (or any other required channel) to access the bot.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Manage Channels", callback_data="manage_channels")]])
            )
        else:
            await message.reply("❌ Channel already exists or failed to add.")
        
        # Clear session
        if user_id in admin_sessions:
            del admin_sessions[user_id]
    
    except Exception as e:
        await message.reply(f"❌ An error occurred: {str(e)}")
        logger.error(f"Error adding channel: {e}")


async def handle_user_management_message(client: Client, message: Message, session: dict):
    """Handle user management operations"""
    user_id = message.from_user.id
    action = session.get("action")
    
    try:
        target_user_id = None
        target_username = None
        target_mention = None
        
        # Check if forwarded message
        if message.forward_from:
            target_user_id = message.forward_from.id
            target_username = message.forward_from.username
            target_mention = message.forward_from.mention
        
        # Check if user ID in text
        elif message.text and message.text.strip().isdigit():
            target_user_id = int(message.text.strip())
            target_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>"
        
        else:
            await message.reply("❌ Please forward a message from the user or send their user ID.")
            return
        
        if not target_user_id:
            await message.reply("❌ Could not determine user ID.")
            return
        
        # Perform action
        if action == "check_user":
            current_status = get_user_access_status(target_user_id)
            status_text = {
                -1: "❌ **Banned**",
                0: "👤 **Normal** (subject to channel membership)",
                1: "✅ **Whitelisted** (always has access)"
            }
            
            await message.reply(
                f"🔍 **User Access Status**\n\n"
                f"**User:** {target_mention}\n"
                f"**ID:** `{target_user_id}`\n"
                f"**Status:** {status_text.get(current_status, 'Unknown')}\n",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="manual_access")]])
            )
        
        elif action == "whitelist_user":
            set_user_access_status(target_user_id, 1)
            await message.reply(
                f"✅ **User Whitelisted**\n\n"
                f"**User:** {target_mention}\n"
                f"**ID:** `{target_user_id}`\n\n"
                f"This user now has permanent access to the bot, regardless of channel membership.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Manage Users", callback_data="manual_access")]])
            )
        
        elif action == "ban_user":
            set_user_access_status(target_user_id, -1)
            await message.reply(
                f"❌ **User Banned**\n\n"
                f"**User:** {target_mention}\n"
                f"**ID:** `{target_user_id}`\n\n"
                f"This user is now denied access to the bot.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Manage Users", callback_data="manual_access")]])
            )
        
        # Clear session
        if user_id in admin_sessions:
            del admin_sessions[user_id]
    
    except Exception as e:
        await message.reply(f"❌ An error occurred: {str(e)}")
        logger.error(f"Error in user management: {e}")


def get_channel_url(channel: Dict) -> str:
    """
    Construct a proper channel URL based on available information.
    
    Args:
        channel: Dictionary containing channel information
        
    Returns:
        str: A valid Telegram channel URL
    """
    # Use stored channel link if available and valid
    if channel.get('channel_link') and channel['channel_link'].startswith('https://t.me/'):
        return channel['channel_link']
    
    channel_id = channel['channel_id']
    channel_id_str = str(channel_id)
    
    # For supergroup/channel IDs that start with -100
    if channel_id_str.startswith('-100') and len(channel_id_str) > 4:
        # Remove the -100 prefix to get the actual channel ID for t.me/c/ links
        clean_id = channel_id_str[4:]
        return f"https://t.me/c/{clean_id}"
    
    # For positive IDs (shouldn't happen for channels, but handle gracefully)
    elif channel_id > 0:
        return f"https://t.me/joinchat/{channel_id}"
    
    # For other negative IDs, try using absolute value
    else:
        return f"https://t.me/joinchat/{abs(channel_id)}"


# Register handlers
def register_admin_handlers(app):
    """Register all admin handlers"""
    app.on_message(filters.command("admin") & filters.private)(admin_command)
    app.on_callback_query(filters.regex(r"^(access_menu|manage_channels|manual_access|add_channel|remove_channel_|remove_all_channels|confirm_|whitelist_user|ban_user|check_user|access_stats|close_admin).*"))(admin_callback_handler)
    app.on_message(filters.private & admin_session)(handle_admin_message)
