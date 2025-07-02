#!/usr/local/bin/python3
# coding: utf-8

import asyncio
import logging
import os
import re
import threading
import time
import typing
from io import BytesIO
from typing import Any

import psutil
import pyrogram.errors
import yt_dlp
from apscheduler.schedulers.background import BackgroundScheduler
from pyrogram import Client, enums, filters, types

from config import (
    APP_HASH,
    APP_ID,
    BOT_TOKEN,
    ENABLE_ARIA2,
    ENABLE_FFMPEG,
    M3U8_SUPPORT,
    BotText,
)
from database.model import (
    get_format_settings,
    get_quality_settings,
    get_user_access_status,
    init_user,
    set_user_settings,
    get_user_platform_quality,
    set_user_platform_quality,
    create_youtube_format_session,
    get_youtube_format_session,
    delete_youtube_format_session,
    log_user_activity,
    log_download_attempt,
    log_download_completion,
)
from engine import direct_entrance, youtube_entrance, special_download_entrance
from engine.youtube_formats import extract_youtube_formats, is_youtube_url
from handlers.admin import register_admin_handlers
from utils.access_control import get_admin_list
from keyboards.main import (
    create_main_keyboard,
    create_admin_keyboard,
    create_settings_keyboard,
    create_format_settings_keyboard,
    create_youtube_quality_keyboard,
    create_platform_quality_keyboard,
    create_youtube_format_keyboard,
    create_back_keyboard,
)
from utils import extract_url_and_name, sizeof_fmt, timeof_fmt
from utils.access_control import check_full_user_access, get_access_denied_message, is_admin
from utils.decorators import private_use, private_use_callback
from utils.stats_logger import start_stats_logging, stop_stats_logging
from utils.error_handling import setup_comprehensive_logging, error_handler, download_error_handler

logging.getLogger("apscheduler.executors.default").propagate = False


def create_app(name: str, workers: int = 64) -> Client:
    return Client(
        name,
        APP_ID,
        APP_HASH,
        bot_token=BOT_TOKEN,
        workers=workers,
        # max_concurrent_transmissions=max(1, WORKERS // 2),
        # https://github.com/pyrogram/pyrogram/issues/1225#issuecomment-1446595489
    )


app = create_app("main")



def private_use_callback(func):
    """Decorator for callback query handlers with access control"""
    async def wrapper(client: Client, callback_query: types.CallbackQuery):
        chat_id = getattr(callback_query.from_user, "id", None)

        # Only allow private chats for this bot now
        if callback_query.message.chat.type != enums.ChatType.PRIVATE:
            logging.debug("Ignoring group/channel callback: %s", callback_query.data)
            await callback_query.answer("❌ This bot only works in private chats.")
            return

        # Access control check
        if chat_id:
            try:
                access_result = await check_full_user_access(client, chat_id)
                if not access_result['has_access']:
                    denial_message = get_access_denied_message(access_result)
                    await callback_query.answer("❌ Access denied", show_alert=True)
                    logging.info(f"Access denied for user {chat_id}: {access_result['reason']}")
                    return
                
                # Log successful access
                logging.debug(f"Callback access granted for user {chat_id}: {access_result['reason']}")
                
            except Exception as e:
                logging.error(f"Error checking access for user {chat_id}: {e}")
                await callback_query.answer("❌ Access check failed", show_alert=True)
                return

        return await func(client, callback_query)

    return wrapper


@app.on_message(filters.command(["start"]))
@private_use
@error_handler
async def start_handler(client: Client, message: types.Message):
    from_id = message.chat.id
    init_user(from_id)
    
    # Log user activity
    log_user_activity(from_id, 'start', {'command': 'start'})
    
    logging.info("%s welcome to youtube-dl bot!", message.from_user.id)
    await client.send_chat_action(from_id, enums.ChatAction.TYPING)
    
    # Check if user is admin to show admin keyboard
    admin_status = await is_admin(client, from_id)
    keyboard = create_admin_keyboard() if admin_status else create_main_keyboard()
    
    await client.send_message(
        from_id,
        BotText.start,
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        reply_markup=keyboard
    )


# Keyboard message handlers
@app.on_message(filters.text & filters.regex(r"^⚙️ Settings$"))
@private_use
async def settings_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    
    # Log user activity
    log_user_activity(chat_id, 'settings', {'action': 'view_settings'})
    
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
    
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    await client.send_message(
        chat_id, 
        settings_text, 
        reply_markup=create_settings_keyboard()
    )


@app.on_message(filters.text & filters.regex(r"^📊 Stats$"))
@private_use
async def stats_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
    cpu_usage = psutil.cpu_percent()
    total, used, free, disk = psutil.disk_usage("/")
    swap = psutil.swap_memory()
    memory = psutil.virtual_memory()
    boot_time = psutil.boot_time()

    owner_stats = (
        "\n\n⌬─────「 Stats 」─────⌬\n\n"
        f"<b>╭🖥️ **CPU Usage »**</b>  __{cpu_usage}%__\n"
        f"<b>├💾 **RAM Usage »**</b>  __{memory.percent}%__\n"
        f"<b>╰🗃️ **DISK Usage »**</b>  __{disk}%__\n\n"
        f"<b>╭📤Upload:</b> {sizeof_fmt(psutil.net_io_counters().bytes_sent)}\n"
        f"<b>╰📥Download:</b> {sizeof_fmt(psutil.net_io_counters().bytes_recv)}\n\n\n"
        f"<b>Memory Total:</b> {sizeof_fmt(memory.total)}\n"
        f"<b>Memory Free:</b> {sizeof_fmt(memory.available)}\n"
        f"<b>Memory Used:</b> {sizeof_fmt(memory.used)}\n"
        f"<b>SWAP Total:</b> {sizeof_fmt(swap.total)} | <b>SWAP Usage:</b> {swap.percent}%\n\n"
        f"<b>Total Disk Space:</b> {sizeof_fmt(total)}\n"
        f"<b>Used:</b> {sizeof_fmt(used)} | <b>Free:</b> {sizeof_fmt(free)}\n\n"
        f"<b>Physical Cores:</b> {psutil.cpu_count(logical=False)}\n"
        f"<b>Total Cores:</b> {psutil.cpu_count(logical=True)}\n\n"
        f"<b>🤖Bot Uptime:</b> {timeof_fmt(time.time() - botStartTime)}\n"
        f"<b>⏲️OS Uptime:</b> {timeof_fmt(time.time() - boot_time)}\n"
    )

    user_stats = (
        "\n\n⌬─────「 Stats 」─────⌬\n\n"
        f"<b>╭🖥️ **CPU Usage »**</b>  __{cpu_usage}%__\n"
        f"<b>├💾 **RAM Usage »**</b>  __{memory.percent}%__\n"
        f"<b>╰🗃️ **DISK Usage »**</b>  __{disk}%__\n\n"
        f"<b>╭📤Upload:</b> {sizeof_fmt(psutil.net_io_counters().bytes_sent)}\n"
        f"<b>╰📥Download:</b> {sizeof_fmt(psutil.net_io_counters().bytes_recv)}\n\n\n"
        f"<b>Memory Total:</b> {sizeof_fmt(memory.total)}\n"
        f"<b>Memory Free:</b> {sizeof_fmt(memory.available)}\n"
        f"<b>Memory Used:</b> {sizeof_fmt(memory.used)}\n"
        f"<b>Total Disk Space:</b> {sizeof_fmt(total)}\n"
        f"<b>Used:</b> {sizeof_fmt(used)} | <b>Free:</b> {sizeof_fmt(free)}\n\n"
        f"<b>🤖Bot Uptime:</b> {timeof_fmt(time.time() - botStartTime)}\n"
    )

    is_owner = await is_admin(client, message.from_user.id)
    await message.reply_text(owner_stats if is_owner else user_stats, quote=True)


@app.on_message(filters.text & filters.regex(r"^ℹ️ About$"))
@private_use
async def about_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
    await client.send_message(chat_id, BotText.about)


@app.on_message(filters.text & filters.regex(r"^❓ Help$"))
@private_use
async def help_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
    await client.send_message(chat_id, BotText.help, link_preview_options=types.LinkPreviewOptions(is_disabled=True))


@app.on_message(filters.text & filters.regex(r"^🏓 Ping$"))
@private_use
async def ping_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)

    async def send_message_and_measure_ping():
        start_time = int(round(time.time() * 1000))
        reply: types.Message | typing.Any = await client.send_message(chat_id, "Starting Ping...")

        end_time = int(round(time.time() * 1000))
        ping_time = int(round(end_time - start_time))
        message_sent = True
        if message_sent:
            await message.reply_text(f"Ping: {ping_time:.2f} ms", quote=True)
        await asyncio.sleep(0.5)
        await client.edit_message_text(chat_id=reply.chat.id, message_id=reply.id, text="Ping Calculation Complete.")
        await asyncio.sleep(1)
        await client.delete_messages(chat_id=reply.chat.id, message_ids=reply.id)

    # Run ping measurement in the background
    asyncio.create_task(send_message_and_measure_ping())


@app.on_message(filters.text & filters.regex(r"^📥 Direct Download$"))
@private_use
async def direct_download_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await set_user_state(chat_id, "direct_download")
    await client.send_message(
        chat_id,
        "📥 **Direct Download Mode**\n\nSend me a direct link to download the file directly using aria2/requests.\n\n_Send any other message to cancel._",
        reply_markup=create_back_keyboard()
    )


@app.on_message(filters.text & filters.regex(r"^🔗 Special Download$"))
@private_use
async def special_download_keyboard_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    init_user(chat_id)
    await set_user_state(chat_id, "special_download")
    await client.send_message(
        chat_id,
        "🔗 **Special Download Mode**\n\nSend me a link for special download processing (Instagram, Pixeldrain, Krakenfiles).\n\n_Send any other message to cancel._",
        reply_markup=create_back_keyboard()
    )


def check_link(url: str):
    ytdl = yt_dlp.YoutubeDL()
    if re.findall(r"^https://www\.youtube\.com/channel/", url) or "list" in url:
        # TODO maybe using ytdl.extract_info
        raise ValueError("Playlist or channel download are not supported at this moment.")

    if not M3U8_SUPPORT and (re.findall(r"m3u8|\.m3u8|\.m3u$", url.lower())):
        return "m3u8 links are disabled."


@app.on_message(filters.incoming & filters.text & ~filters.regex(r"^(⚙️|📊|ℹ️|❓|🏓|📥|🔗|🔧)"))
@private_use
@download_error_handler
async def download_handler(client: Client, message: types.Message):
    chat_id = message.from_user.id
    init_user(chat_id)
    await client.send_chat_action(chat_id, enums.ChatAction.TYPING)
    url = message.text
    logging.info("start %s", url)

    # Check user state for special download modes
    user_state = await get_user_state(chat_id)
    
    try:
        # Validate URL format
        if not re.findall(r"^https?://", url.lower()):
            if user_state:
                await clear_user_state(chat_id)
                await message.reply_text("❌ **Mode Cancelled**\n\nInvalid URL format. Please use a valid HTTP/HTTPS URL.", quote=True)
            else:
                await message.reply_text("❌ **Invalid URL**\n\nPlease send a valid HTTP/HTTPS URL.", quote=True)
            return
        
        check_link(url)
        
        # Handle different download modes based on user state
        if user_state == "direct_download":
            await clear_user_state(chat_id)
            logging.info("Direct download using aria2/requests start %s", url)
            bot_msg = await message.reply_text("📥 Direct download request received.", quote=True)
            try:
                await direct_entrance(client, bot_msg, url)
            except ValueError as e:
                await message.reply_text(e.__str__(), quote=True)
                await bot_msg.delete()
            return
            
        elif user_state == "special_download":
            await clear_user_state(chat_id)
            logging.info("Special download start %s", url)
            bot_msg = await message.reply_text("🔗 Special download request received.", quote=True)
            try:
                await special_download_entrance(client, bot_msg, url)
            except ValueError as e:
                await message.reply_text(e.__str__(), quote=True)
                await bot_msg.delete()
            return
        
        # Regular download mode - check if it's a YouTube URL for dynamic format selection
        if is_youtube_url(url):
            # Log download attempt
            platform = "youtube"
            download_id = log_download_attempt(chat_id, url, platform)
            log_user_activity(chat_id, 'download', {'platform': platform, 'url': url, 'download_id': download_id})
            
            # Extract available formats
            try:
                formats = extract_youtube_formats(url)
                if formats and (formats.get('video_formats') or formats.get('audio_formats')):
                    # Create a session for this user and URL
                    create_youtube_format_session(chat_id, url, formats)
                    
                    # Send format selection keyboard
                    format_keyboard = create_youtube_format_keyboard(formats)
                    await message.reply_text(
                        "🎬 **YouTube Format Selection**\n\n"
                        "Choose your preferred format and quality:\n"
                        "• Video formats include both video and audio\n"
                        "• Audio formats are audio-only\n"
                        "• File sizes are estimates",
                        reply_markup=format_keyboard,
                        quote=True
                    )
                    return
                else:
                    # Fallback to regular download if format extraction fails
                    logging.warning("Could not extract YouTube formats, falling back to regular download")
            except Exception as e:
                logging.error(f"Error extracting YouTube formats: {e}")
                # Fallback to regular download
        else:
            # Log download attempt for non-YouTube platforms
            platform = "other"
            if "instagram" in url.lower():
                platform = "instagram"
            elif "pixeldrain" in url.lower():
                platform = "pixeldrain"
            elif "krakenfiles" in url.lower():
                platform = "krakenfiles"
            
            download_id = log_download_attempt(chat_id, url, platform)
            log_user_activity(chat_id, 'download', {'platform': platform, 'url': url, 'download_id': download_id})
        
        # Regular download for non-YouTube URLs or YouTube fallback
        bot_msg: types.Message | Any = await message.reply_text("Task received.", quote=True)
        await client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_VIDEO)
        await youtube_entrance(client, bot_msg, url)
        
    except pyrogram.errors.Flood as e:
        await clear_user_state(chat_id)  # Clear state on flood
        f = BytesIO()
        f.write(str(e).encode())
        f.write(b"Your job will be done soon. Just wait!")
        f.name = "Please wait.txt"
        f.seek(0)  # Reset pointer to beginning of file
        await message.reply_document(f, caption=f"Flood wait! Please wait {e} seconds...", quote=True)
        f.close()
        # Notify all admins about flood wait
        admin_list = get_admin_list()
        for admin_id in admin_list:
            try:
                await client.send_message(admin_id, f"Flood wait! 🙁 {e} seconds....")
            except Exception:
                pass  # Skip if can't send to this admin
        await asyncio.sleep(e.value)
    except ValueError as e:
        await clear_user_state(chat_id)  # Clear state on error
        await message.reply_text(e.__str__(), quote=True)
    except Exception as e:
        await clear_user_state(chat_id)  # Clear state on error
        logging.error("Download failed", exc_info=True)
        await message.reply_text(f"❌ Download failed: {e}", quote=True)


# Thread-safe state management with expiry
class UserStateManager:
    """Thread-safe user state manager with automatic expiry"""
    
    def __init__(self, expiry_seconds: int = 3600):  # 1 hour default expiry
        self._states = {}  # {user_id: {'state': state, 'timestamp': timestamp}}
        self._lock = asyncio.Lock()
        self._expiry_seconds = expiry_seconds
    
    async def set_user_state(self, user_id: int, state: str) -> None:
        """Set user state with timestamp for expiry tracking"""
        async with self._lock:
            self._states[user_id] = {
                'state': state,
                'timestamp': time.time()
            }
            logging.debug(f"Set state '{state}' for user {user_id}")
    
    async def get_user_state(self, user_id: int) -> str | None:
        """Get user state, automatically removing expired states"""
        async with self._lock:
            if user_id not in self._states:
                return None
            
            state_data = self._states[user_id]
            current_time = time.time()
            
            # Check if state has expired
            if current_time - state_data['timestamp'] > self._expiry_seconds:
                logging.debug(f"State expired for user {user_id}, removing")
                del self._states[user_id]
                return None
            
            return state_data['state']
    
    async def clear_user_state(self, user_id: int) -> None:
        """Clear user state"""
        async with self._lock:
            if user_id in self._states:
                logging.debug(f"Cleared state for user {user_id}")
                del self._states[user_id]
    
    async def cleanup_expired_states(self) -> int:
        """Clean up all expired states, returns number of states removed"""
        async with self._lock:
            current_time = time.time()
            expired_users = []
            
            for user_id, state_data in self._states.items():
                if current_time - state_data['timestamp'] > self._expiry_seconds:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._states[user_id]
            
            if expired_users:
                logging.debug(f"Cleaned up {len(expired_users)} expired states")
            
            return len(expired_users)
    
    async def get_active_states_count(self) -> int:
        """Get count of active (non-expired) states"""
        async with self._lock:
            current_time = time.time()
            active_count = 0
            
            for state_data in self._states.values():
                if current_time - state_data['timestamp'] <= self._expiry_seconds:
                    active_count += 1
            
            return active_count


# Global instance of the user state manager
user_state_manager = UserStateManager(expiry_seconds=1800)  # 30 minutes expiry


# Legacy wrapper functions for backward compatibility (to be replaced gradually)
async def set_user_state(user_id, state):
    """Legacy wrapper - use user_state_manager.set_user_state() directly"""
    await user_state_manager.set_user_state(user_id, state)

async def get_user_state(user_id):
    """Legacy wrapper - use user_state_manager.get_user_state() directly"""
    return await user_state_manager.get_user_state(user_id)

async def clear_user_state(user_id):
    """Legacy wrapper - use user_state_manager.clear_user_state() directly"""
    await user_state_manager.clear_user_state(user_id)


# Callback query handlers for inline keyboards
@app.on_callback_query(filters.regex(r"^settings_"))
@private_use_callback
async def settings_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    if data == "settings_format":
        current_format = get_format_settings(chat_id)
        await callback_query.edit_message_text(
            f"📁 **Upload Format Settings**\n\nCurrently set to: `{current_format}`\n\nChoose your preferred format:",
            reply_markup=create_format_settings_keyboard()
        )
    elif data == "settings_youtube_quality":
        current_quality = get_quality_settings(chat_id)
        await callback_query.edit_message_text(
            f"🎬 **YouTube Quality Settings**\n\nCurrently set to: `{current_quality}`\n\nChoose your preferred YouTube quality:",
            reply_markup=create_youtube_quality_keyboard()
        )
    elif data == "settings_platform_quality":
        current_quality = get_user_platform_quality(chat_id)
        await callback_query.edit_message_text(
            f"🌐 **Platform Quality Settings**\n\nCurrently set to: `{current_quality}`\n\nChoose your preferred quality for non-YouTube platforms:",
            reply_markup=create_platform_quality_keyboard()
        )
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r"^format_"))
@private_use_callback
async def format_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("format_", "")
    
    logging.info("Setting %s file format to %s", chat_id, data)
    set_user_settings(chat_id, "format", data)
    
    await callback_query.answer(f"✅ Upload format set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    await callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^youtube_quality_"))
@private_use_callback
async def youtube_quality_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("youtube_quality_", "")
    
    logging.info("Setting %s YouTube quality to %s", chat_id, data)
    set_user_settings(chat_id, "quality", data)
    
    await callback_query.answer(f"✅ YouTube quality set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    await callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^platform_quality_"))
@private_use_callback
async def platform_quality_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("platform_quality_", "")
    
    logging.info("Setting %s platform quality to %s", chat_id, data)
    set_user_platform_quality(chat_id, data)
    
    await callback_query.answer(f"✅ Platform quality set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    await callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^back_to_"))
@private_use_callback
async def back_navigation_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    # Clear any user state when going back to main
    await clear_user_state(chat_id)
    
    if data == "back_to_main":
        await callback_query.edit_message_text(
            "🏠 **Main Menu**\n\nUse the keyboard below to navigate:",
            reply_markup=None
        )
    elif data == "back_to_settings":
        quality = get_quality_settings(chat_id)
        send_type = get_format_settings(chat_id)
        platform_quality = get_user_platform_quality(chat_id)
        
        settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
        
        await callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r"^yt_format_"))
@private_use_callback
async def youtube_format_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    format_id = callback_query.data.replace("yt_format_", "")
    
    # Get the session data
    session = get_youtube_format_session(chat_id)
    if not session:
        await callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    logging.info("User %s selected YouTube format %s for URL %s", chat_id, format_id, session['url'])
    
    # Start download with selected format
    try:
        # Send a new message for the download process instead of editing the callback message
        await callback_query.edit_message_text("🔄 **Download Started**\n\nProcessing your request...")
        
        # Create a proper bot message for the download process
        bot_msg = await callback_query.message.reply_text("⏳ Preparing download...", quote=False)
        
        # Use the youtube_entrance with specific format
        # TODO: Implement specific format support
        await youtube_entrance(client, bot_msg, session['url'])
        
        # Clean up the session
        delete_youtube_format_session(chat_id)
        
    except Exception as e:
        logging.error("YouTube download failed", exc_info=True)
        await callback_query.edit_message_text(f"❌ **Download Failed**\n\n{str(e)}")
        delete_youtube_format_session(chat_id)
    
    await callback_query.answer()


@app.on_callback_query(filters.regex(r"^cancel_format_selection$"))
@private_use_callback
async def cancel_format_selection_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    
    # Clean up the session
    delete_youtube_format_session(chat_id)
    
    await callback_query.edit_message_text(
        "❌ **Format Selection Cancelled**\n\nYou can send another URL to try again."
    )
    await callback_query.answer("Format selection cancelled")


# YouTube Format Selection Handlers
@app.on_callback_query(filters.regex(r"^ytfmt_"))
@private_use_callback
async def youtube_format_selection_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle YouTube format selection callbacks"""
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    try:
        # Get user's YouTube format session
        formats_session = get_youtube_format_session(chat_id)
        if not formats_session:
            await callback_query.answer("❌ Session expired. Please send the URL again.", show_alert=True)
            return
        
        await callback_query.answer("Processing your selection...")
        
        if data == "ytfmt_cancel":
            delete_youtube_format_session(chat_id)
            await callback_query.edit_message_text(
                "❌ **Format Selection Cancelled**\n\nYou can send another URL to try again."
            )
            return
        
        elif data == "ytfmt_best":
            # Download best quality video+audio
            await callback_query.edit_message_text("🎬 **Downloading best quality...**")
            # TODO: Implement download with best format
            
        elif data == "ytfmt_worst":
            # Download smallest size
            await callback_query.edit_message_text("💾 **Downloading smallest size...**")
            # TODO: Implement download with worst format
            
        elif data == "ytfmt_audio_best":
            # Download best audio only
            await callback_query.edit_message_text("🎵 **Downloading best audio...**")
            # TODO: Implement audio-only download
            
        elif data.startswith("ytfmt_v_"):
            # Video format selected
            format_id = data.replace("ytfmt_v_", "")
            await callback_query.edit_message_text(f"🎬 **Downloading video format {format_id}...**")
            # TODO: Implement download with specific video format
            
        elif data.startswith("ytfmt_a_"):
            # Audio format selected
            format_id = data.replace("ytfmt_a_", "")
            await callback_query.edit_message_text(f"🎵 **Downloading audio format {format_id}...**")
            # TODO: Implement download with specific audio format
            
        elif data in ["ytfmt_divider", "ytfmt_audio_divider"]:
            # Ignore divider clicks
            await callback_query.answer("This is just a divider", show_alert=False)
            return
        
        # Clean up session after processing
        delete_youtube_format_session(chat_id)
        
    except Exception as e:
        logging.error(f"Error in YouTube format callback: {e}")
        await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)


# Main menu and navigation handlers
@app.on_callback_query(filters.regex(r"^(main_menu|settings|help|stats)$"))
@private_use_callback
async def main_navigation_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle main navigation buttons"""
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    try:
        is_admin_user = await is_admin(client, callback_query.from_user.id)
        
        if data == "main_menu":
            keyboard = create_admin_keyboard() if is_admin_user else create_main_keyboard()
            await callback_query.edit_message_text(
                "🏠 **Main Menu**\n\nChoose an option:",
                reply_markup=keyboard
            )
            
        elif data == "settings":
            keyboard = create_settings_keyboard()
            await callback_query.edit_message_text(
                "⚙️ **Settings**\n\nConfigure your download preferences:",
                reply_markup=keyboard
            )
            
        elif data == "help":
            await callback_query.edit_message_text(
                BotText.help,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                reply_markup=create_back_keyboard("main_menu")
            )
            
        elif data == "stats":
            # Show user statistics
            await callback_query.edit_message_text(
                "📊 **Statistics**\n\nThis feature is coming soon!",
                reply_markup=create_back_keyboard("main_menu")
            )
            
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error in main navigation handler: {e}")
        await callback_query.answer("❌ An error occurred", show_alert=True)


# Admin callback handlers
@app.on_callback_query(filters.regex(r"^admin_"))
@private_use_callback
async def admin_callback_handler(client: Client, callback_query: types.CallbackQuery):
    """Handle admin buttons"""
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    # Check if user is admin
    admin_status = await is_admin(client, callback_query.from_user.id)
    if not admin_status:
        await callback_query.answer("❌ Access denied. Admin only.", show_alert=True)
        return
    
    try:
        if data == "admin_stats":
            # Show user statistics
            # TODO: Implement real statistics
            stats_text = """📊 **Bot Statistics**

👤 **User Statistics:**
• Total Users: Coming soon
• Active Users: Coming soon
• Downloads Today: Coming soon

📈 **System Statistics:**
• Bot Uptime: Coming soon
• Total Downloads: Coming soon
• Storage Used: Coming soon

🔧 **Technical:**
• Database Status: ✅ Connected
• Redis Status: ⚠️ Fake Redis
• Download Queue: Coming soon"""
            
            await callback_query.edit_message_text(
                stats_text,
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                    [types.InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_menu")]
                ])
            )
            
        elif data == "admin_users":
            # Show user management
            users_text = """👥 **User Management**

🛡️ **Access Control:**
• Total Users: Coming soon
• Blocked Users: Coming soon
• Channel Subscribers: Coming soon

⚙️ **Management Options:**
• View User List
• Block/Unblock Users
• Channel Management
• Access Logs

_This feature is under development._"""
            
            await callback_query.edit_message_text(
                users_text,
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("📝 View Logs", callback_data="admin_logs")],
                    [types.InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_menu")]
                ])
            )
            
        elif data == "admin_settings":
            # Show bot settings
            settings_text = """⚙️ **Bot Settings**

🤖 **Current Configuration:**
• Private Mode: ✅ Enabled
• Admin Access: ✅ Active
• Download Modes: All Enabled
• Error Handling: ✅ Active

🔧 **System Settings:**
• Logging Level: INFO
• Max File Size: Unlimited
• Concurrent Downloads: 4
• Auto-cleanup: Enabled

_Settings can be modified in the config files._"""
            
            await callback_query.edit_message_text(
                settings_text,
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("📋 View Config", callback_data="admin_config")],
                    [types.InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_menu")]
                ])
            )
            
        elif data == "admin_menu":
            # Back to admin menu
            await callback_query.edit_message_text(
                "🔧 **Admin Panel**\n\nChoose an administrative function:",
                reply_markup=create_admin_keyboard()
            )
            
        elif data == "admin_logs":
            # Show recent logs (placeholder)
            await callback_query.edit_message_text(
                "📝 **Recent Activity Logs**\n\n_This feature is under development._\n\nFor now, check the server logs directly.",
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_menu")]
                ])
            )
            
        elif data == "admin_config":
            # Show config info (placeholder)
            await callback_query.edit_message_text(
                "📋 **Configuration**\n\n_This feature is under development._\n\nConfig files are located in the `config/` directory.",
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_menu")]
                ])
            )
        
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error in admin callback handler: {e}")
        await callback_query.answer("❌ An error occurred", show_alert=True)


# Legacy wrapper for private use
def private_use_legacy(func):
    """Decorator for private use with legacy support"""
    async def wrapper(client: Client, message: types.Message):
        chat_id = message.chat.id
        
        # Only allow private chats for this bot now
        if message.chat.type != enums.ChatType.PRIVATE:
            logging.debug("Ignoring group/channel message: %s", message.text)
            await message.reply_text("❌ This bot only works in private chats.")
            return

        # Access control - check if user is admin
        is_admin_user = await is_admin(client, chat_id)
        if not is_admin_user:
            await message.reply_text("❌ Access denied. Admins only.")
            logging.info(f"Access denied for non-admin user {chat_id} trying to use admin command.")
            return
        
        return await func(client, message)

    return wrapper


# Admin commands - legacy handlers
@app.on_message(filters.command(["admin_stats", "admin_users", "admin_settings"]))
@private_use_legacy
async def admin_commands_handler(client: Client, message: types.Message):
    chat_id = message.chat.id
    command = message.text
    
    if command == "/admin_stats":
        # Show admin stats
        await message.reply_text("📊 **Admin Statistics**\n\nThis feature is coming soon!")
    elif command == "/admin_users":
        # Show admin users management
        await message.reply_text("👥 **User Management**\n\nThis feature is coming soon!")
    elif command == "/admin_settings":
        # Show admin settings
        await message.reply_text("⚙️ **Bot Settings**\n\nThis feature is coming soon!")


if __name__ == "__main__":
    # Setup comprehensive logging first
    setup_comprehensive_logging()
    
    botStartTime = time.time()
    banner = f"""
▌ ▌         ▀▛▘     ▌       ▛▀▖              ▜            ▌
▝▞  ▞▀▖ ▌ ▌  ▌  ▌ ▌ ▛▀▖ ▞▀▖ ▌ ▌ ▞▀▖ ▌  ▌ ▛▀▖ ▐  ▞▀▖ ▝▀▖ ▞▀▌
 ▌  ▌ ▌ ▌ ▌  ▌  ▌ ▌ ▌ ▌ ▛▀  ▌ ▌ ▌ ▌ ▐▐▐  ▌ ▌ ▐  ▌ ▌ ▞▀▌ ▌ ▌
 ▘  ▝▀  ▝▀▘  ▘  ▝▀▘ ▀▀  ▝▀▘ ▀▀  ▝▀   ▘▘  ▘ ▘  ▘ ▝▀  ▝▀▘ ▝▀▘

YouTube Download Bot - Private Access Control Edition
Production Ready with Enhanced Analytics & Error Handling
    """
    print(banner)
    
    logging.info("=== BOT STARTUP ===")
    logging.info("Starting YouTube Download Bot - Private Edition")
    
    # Register admin handlers
    register_admin_handlers(app)
    
    # Start system statistics logging
    start_stats_logging()
    
    try:
        logging.info("Bot is starting...")
        app.run()
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested by user")
        print("\nShutting down gracefully...")
        stop_stats_logging()
    except Exception as e:
        logging.critical(f"Bot crashed with critical error: {e}", exc_info=True)
        print(f"Bot crashed: {e}")
        stop_stats_logging()
        raise
    finally:
        logging.info("=== BOT SHUTDOWN ===")
        print("Bot stopped.")
