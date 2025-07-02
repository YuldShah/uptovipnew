#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - keyboards/main.py
# Keyboard layouts for the Telegram bot

try:
    from pyrogram import types
except ImportError:
    from kurigram import types

from engine.youtube_formats import get_format_display_name


def create_main_keyboard():
    """Create the main keyboard layout."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [types.InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [types.InlineKeyboardButton("❓ Help", callback_data="help")],
    ])
    return keyboard


def create_admin_keyboard():
    """Create the admin keyboard layout."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("📊 User Statistics", callback_data="admin_stats")],
        [types.InlineKeyboardButton("👥 Access Control", callback_data="access_menu")],
        [types.InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings")],
        [types.InlineKeyboardButton("❌ Close", callback_data="close_admin")],
    ])
    return keyboard


def create_settings_keyboard():
    """Create the settings keyboard layout."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("🎬 Format Settings", callback_data="format_settings")],
        [types.InlineKeyboardButton("🎯 Quality Settings", callback_data="quality_settings")],
        [types.InlineKeyboardButton("🎵 Platform Quality", callback_data="platform_quality")],
        [types.InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ])
    return keyboard


def create_format_settings_keyboard():
    """Create the format settings keyboard layout."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("📹 Video", callback_data="format_video")],
        [types.InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [types.InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [types.InlineKeyboardButton("🔙 Back", callback_data="settings")],
    ])
    return keyboard


def create_youtube_quality_keyboard():
    """Create the YouTube quality settings keyboard."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("🔥 High (1080p+)", callback_data="youtube_quality_high")],
        [types.InlineKeyboardButton("⚡ Medium (720p)", callback_data="youtube_quality_medium")],
        [types.InlineKeyboardButton("💾 Low (480p)", callback_data="youtube_quality_low")],
        [types.InlineKeyboardButton("🔙 Back", callback_data="quality_settings")],
    ])
    return keyboard


def create_platform_quality_keyboard():
    """Create the platform quality settings keyboard."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("🎬 YouTube", callback_data="platform_youtube")],
        [types.InlineKeyboardButton("📱 Instagram", callback_data="platform_instagram")],
        [types.InlineKeyboardButton("🎵 Twitter", callback_data="platform_twitter")],
        [types.InlineKeyboardButton("🔙 Back", callback_data="settings")],
    ])
    return keyboard


def create_youtube_format_keyboard(formats_dict: dict):
    """
    Create a keyboard for YouTube format selection.
    
    Args:
        formats_dict (dict): Dictionary containing video_formats and audio_formats
        
    Returns:
        types.InlineKeyboardMarkup: Keyboard with format options
    """
    buttons = []
    
    # Add video formats (limit to top 8 to avoid too many buttons)
    video_formats = formats_dict.get('video_formats', [])
    shown_video = 0
    for i, fmt in enumerate(video_formats):
        if shown_video >= 8:  # Limit number of options
            break
            
        # Skip if no height info or duplicate heights
        if not fmt.get('height'):
            continue
            
        # Check if we already have this height
        heights_shown = [v.get('height') for v in video_formats[:i] if v.get('height')]
        if fmt.get('height') in heights_shown:
            continue
            
        display_name = f"📽️ {get_format_display_name(fmt)}"
        if len(display_name) > 30:  # Limit button text length
            display_name = display_name[:27] + "..."
            
        callback_data = f"ytfmt_v_{fmt['format_id']}"
        buttons.append([types.InlineKeyboardButton(display_name, callback_data=callback_data)])
        shown_video += 1
    
    # Add audio formats (limit to top 3)
    audio_formats = formats_dict.get('audio_formats', [])
    if audio_formats:
        
        
        for i, fmt in enumerate(audio_formats[:3]):
            display_name = f"🎵 {get_format_display_name(fmt)}"
            if len(display_name) > 30:
                display_name = display_name[:27] + "..."
                
            callback_data = f"ytfmt_a_{fmt['format_id']}"
            buttons.append([types.InlineKeyboardButton(display_name, callback_data=callback_data)])
    
    # Add cancel button
    buttons.append([
        types.InlineKeyboardButton("❌ Cancel", callback_data="ytfmt_cancel")
    ])
    
    return types.InlineKeyboardMarkup(buttons)


def create_back_keyboard(callback_data: str = "main_menu"):
    """Create a simple back button keyboard."""
    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("🔙 Back", callback_data=callback_data)]
    ])
    return keyboard


def create_confirmation_keyboard(action: str, item_id: str = ""):
    """Create a confirmation keyboard for dangerous actions."""
    keyboard = types.InlineKeyboardMarkup([
        [
            types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}_{item_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        ]
    ])
    return keyboard


def create_pagination_keyboard(current_page: int, total_pages: int, prefix: str):
    """Create a pagination keyboard."""
    buttons = []
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"{prefix}_page_{current_page-1}"))
    
    nav_buttons.append(types.InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="page_info"))
    
    if current_page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("➡️ Next", callback_data=f"{prefix}_page_{current_page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([types.InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    return types.InlineKeyboardMarkup(buttons)
