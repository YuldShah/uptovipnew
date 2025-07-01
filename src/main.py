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
    AUTHORIZED_USER,
    BOT_TOKEN,
    ENABLE_ARIA2,
    ENABLE_FFMPEG,
    M3U8_SUPPORT,
    OWNER,
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
from utils.stats_logger import start_stats_logging, stop_stats_logging
from utils.error_handling import setup_comprehensive_logging, error_handler, download_error_handler

logging.info("Authorized users are %s", AUTHORIZED_USER)
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


def private_use(func):
    async def wrapper(client: Client, message: types.Message):
        chat_id = getattr(message.from_user, "id", None)

        # Only allow private chats for this bot now
        if message.chat.type != enums.ChatType.PRIVATE:
            logging.debug("Ignoring group/channel message: %s", message.text)
            return

        # Access control check
        if chat_id:
            try:
                access_result = await check_full_user_access(client, chat_id)
                if not access_result['has_access']:
                    denial_message = get_access_denied_message(access_result)
                    await message.reply_text(denial_message, quote=True)
                    logging.info(f"Access denied for user {chat_id}: {access_result['reason']}")
                    return
                
                # Log successful access
                logging.info(f"Access granted for user {chat_id}: {access_result['reason']}")
                
            except Exception as e:
                logging.error(f"Error checking access for user {chat_id}: {e}")
                await message.reply_text("❌ **Access Check Failed**\n\nThere was an error verifying your access. Please try again later.", quote=True)
                return

        return await func(client, message)

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
        disable_web_page_preview=True,
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
    await client.send_message(chat_id, BotText.help, disable_web_page_preview=True)


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
    set_user_state(chat_id, "direct_download")
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
    set_user_state(chat_id, "special_download")
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
    user_state = get_user_state(chat_id)
    
    try:
        # Validate URL format
        if not re.findall(r"^https?://", url.lower()):
            if user_state:
                clear_user_state(chat_id)
                await message.reply_text("❌ **Mode Cancelled**\n\nInvalid URL format. Please use a valid HTTP/HTTPS URL.", quote=True)
            else:
                await message.reply_text("❌ **Invalid URL**\n\nPlease send a valid HTTP/HTTPS URL.", quote=True)
            return
        
        check_link(url)
        
        # Handle different download modes based on user state
        if user_state == "direct_download":
            clear_user_state(chat_id)
            logging.info("Direct download using aria2/requests start %s", url)
            bot_msg = await message.reply_text("📥 Direct download request received.", quote=True)
            try:
                direct_entrance(client, bot_msg, url)
            except ValueError as e:
                await message.reply_text(e.__str__(), quote=True)
                await bot_msg.delete()
            return
            
        elif user_state == "special_download":
            clear_user_state(chat_id)
            logging.info("Special download start %s", url)
            bot_msg = await message.reply_text("🔗 Special download request received.", quote=True)
            try:
                special_download_entrance(client, bot_msg, url)
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
        youtube_entrance(client, bot_msg, url)
        
    except pyrogram.errors.Flood as e:
        clear_user_state(chat_id)  # Clear state on flood
        f = BytesIO()
        f.write(str(e).encode())
        f.write(b"Your job will be done soon. Just wait!")
        f.name = "Please wait.txt"
        await message.reply_document(f, caption=f"Flood wait! Please wait {e} seconds...", quote=True)
        f.close()
        await client.send_message(OWNER, f"Flood wait! 🙁 {e} seconds....")
        await asyncio.sleep(e.value)
    except ValueError as e:
        clear_user_state(chat_id)  # Clear state on error
        await message.reply_text(e.__str__(), quote=True)
    except Exception as e:
        clear_user_state(chat_id)  # Clear state on error
        logging.error("Download failed", exc_info=True)
        await message.reply_text(f"❌ Download failed: {e}", quote=True)


# Simple state management for user modes
user_states = {}

def set_user_state(user_id, state):
    """Set user state for mode tracking"""
    user_states[user_id] = state

def get_user_state(user_id):
    """Get user state"""
    return user_states.get(user_id, None)

def clear_user_state(user_id):
    """Clear user state"""
    user_states.pop(user_id, None)


# Callback query handlers for inline keyboards
@app.on_callback_query(filters.regex(r"^settings_"))
def settings_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    if data == "settings_format":
        current_format = get_format_settings(chat_id)
        callback_query.edit_message_text(
            f"📁 **Upload Format Settings**\n\nCurrently set to: `{current_format}`\n\nChoose your preferred format:",
            reply_markup=create_format_settings_keyboard()
        )
    elif data == "settings_youtube_quality":
        current_quality = get_quality_settings(chat_id)
        callback_query.edit_message_text(
            f"🎬 **YouTube Quality Settings**\n\nCurrently set to: `{current_quality}`\n\nChoose your preferred YouTube quality:",
            reply_markup=create_youtube_quality_keyboard()
        )
    elif data == "settings_platform_quality":
        current_quality = get_user_platform_quality(chat_id)
        callback_query.edit_message_text(
            f"🌐 **Platform Quality Settings**\n\nCurrently set to: `{current_quality}`\n\nChoose your preferred quality for non-YouTube platforms:",
            reply_markup=create_platform_quality_keyboard()
        )
    
    callback_query.answer()


@app.on_callback_query(filters.regex(r"^format_"))
def format_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("format_", "")
    
    logging.info("Setting %s file format to %s", chat_id, data)
    set_user_settings(chat_id, "format", data)
    
    callback_query.answer(f"✅ Upload format set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^youtube_quality_"))
def youtube_quality_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("youtube_quality_", "")
    
    logging.info("Setting %s YouTube quality to %s", chat_id, data)
    set_user_settings(chat_id, "quality", data)
    
    callback_query.answer(f"✅ YouTube quality set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^platform_quality_"))
def platform_quality_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data.replace("platform_quality_", "")
    
    logging.info("Setting %s platform quality to %s", chat_id, data)
    set_user_platform_quality(chat_id, data)
    
    callback_query.answer(f"✅ Platform quality set to {data}")
    
    # Go back to settings
    quality = get_quality_settings(chat_id)
    send_type = get_format_settings(chat_id)
    platform_quality = get_user_platform_quality(chat_id)
    
    settings_text = f"""⚙️ **Current Settings**

📁 **Upload Format:** `{send_type}`
🎬 **YouTube Quality:** `{quality}`
🌐 **Platform Quality:** `{platform_quality}`

Select an option to change:"""
    
    callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())


@app.on_callback_query(filters.regex(r"^back_to_"))
def back_navigation_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    # Clear any user state when going back to main
    clear_user_state(chat_id)
    
    if data == "back_to_main":
        callback_query.edit_message_text(
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
        
        callback_query.edit_message_text(settings_text, reply_markup=create_settings_keyboard())
    
    callback_query.answer()


@app.on_callback_query(filters.regex(r"^yt_format_"))
def youtube_format_callback_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    format_id = callback_query.data.replace("yt_format_", "")
    
    # Get the session data
    session = get_youtube_format_session(chat_id)
    if not session:
        callback_query.answer("❌ Session expired. Please send the URL again.")
        return
    
    logging.info("User %s selected YouTube format %s for URL %s", chat_id, format_id, session.url)
    
    # Start download with selected format
    try:
        callback_query.edit_message_text("🔄 **Download Started**\n\nProcessing your request...")
        
        # Create a pseudo bot message for the download process
        bot_msg = callback_query.message
        
        # Use the youtube_entrance with specific format
        youtube_entrance(client, bot_msg, session.url, specific_format=format_id)
        
        # Clean up the session
        delete_youtube_format_session(chat_id)
        
    except Exception as e:
        logging.error("YouTube download failed", exc_info=True)
        callback_query.edit_message_text(f"❌ **Download Failed**\n\n{str(e)}")
        delete_youtube_format_session(chat_id)
    
    callback_query.answer()


@app.on_callback_query(filters.regex(r"^cancel_format_selection$"))
def cancel_format_selection_handler(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    
    # Clean up the session
    delete_youtube_format_session(chat_id)
    
    callback_query.edit_message_text(
        "❌ **Format Selection Cancelled**\n\nYou can send another URL to try again."
    )
    callback_query.answer("Format selection cancelled")


# Legacy callback handlers for compatibility
@app.on_callback_query(filters.regex(r"document|video|audio"))
def legacy_format_callback(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    logging.info("Setting %s file type to %s", chat_id, data)
    callback_query.answer(f"Your send type was set to {callback_query.data}")
    set_user_settings(chat_id, "format", data)


@app.on_callback_query(filters.regex(r"high|medium|low"))
def legacy_quality_callback(client: Client, callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    logging.info("Setting %s download quality to %s", chat_id, data)
    callback_query.answer(f"Your default engine quality was set to {callback_query.data}")
    set_user_settings(chat_id, "quality", data)


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
