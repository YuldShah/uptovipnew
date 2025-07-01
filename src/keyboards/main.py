#!/usr/bin/env python3
# coding: utf-8

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def create_main_keyboard():
    """Create main reply keyboard with primary options"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("⚙️ Settings"), KeyboardButton("📊 Stats")],
        [KeyboardButton("📥 Direct Download"), KeyboardButton("🔗 Special Download")],
        [KeyboardButton("ℹ️ About"), KeyboardButton("❓ Help")],
        [KeyboardButton("🏓 Ping")]
    ], resize_keyboard=True, one_time_keyboard=False)


def create_admin_keyboard():
    """Create admin reply keyboard with admin options"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("⚙️ Settings"), KeyboardButton("📊 Stats")],
        [KeyboardButton("📥 Direct Download"), KeyboardButton("🔗 Special Download")],
        [KeyboardButton("🔧 Admin Panel"), KeyboardButton("ℹ️ About")],
        [KeyboardButton("❓ Help"), KeyboardButton("🏓 Ping")]
    ], resize_keyboard=True, one_time_keyboard=False)


def create_settings_keyboard():
    """Create settings inline keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Upload Format", callback_data="settings_format")],
        [InlineKeyboardButton("🎬 YouTube Quality", callback_data="settings_youtube_quality")],
        [InlineKeyboardButton("🌐 Platform Quality", callback_data="settings_platform_quality")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ])


def create_format_settings_keyboard():
    """Create upload format selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Document", callback_data="format_document")],
        [InlineKeyboardButton("🎬 Video", callback_data="format_video")],
        [InlineKeyboardButton("🎵 Audio", callback_data="format_audio")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
    ])


def create_youtube_quality_keyboard():
    """Create YouTube quality selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 High Quality", callback_data="youtube_quality_high")],
        [InlineKeyboardButton("⚖️ Medium Quality", callback_data="youtube_quality_medium")],
        [InlineKeyboardButton("💾 Low Quality", callback_data="youtube_quality_low")],
        [InlineKeyboardButton("🎵 Audio Only", callback_data="youtube_quality_audio")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
    ])


def create_platform_quality_keyboard():
    """Create platform quality selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Highest Quality", callback_data="platform_quality_highest")],
        [InlineKeyboardButton("⚖️ Balanced Quality", callback_data="platform_quality_balanced")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
    ])


def create_youtube_format_keyboard(formats):
    """Create dynamic YouTube format selection keyboard"""
    keyboard = []
    
    # Video formats
    if formats.get('video_formats'):
        for fmt in formats['video_formats']:
            size_info = ""
            if fmt.get('filesize') and fmt['filesize'] > 0:
                size_mb = fmt['filesize'] / (1024 * 1024)
                size_info = f" (~{size_mb:.0f}MB)"
            
            keyboard.append([InlineKeyboardButton(
                f"🎬 {fmt['note']}{size_info}",
                callback_data=f"yt_format_{fmt['format_id']}"
            )])
    
    # Audio formats
    if formats.get('audio_formats'):
        if keyboard:  # Add separator if we have video formats
            keyboard.append([InlineKeyboardButton("─" * 25, callback_data="separator")])
        
        for fmt in formats['audio_formats']:
            size_info = ""
            if fmt.get('filesize') and fmt['filesize'] > 0:
                size_mb = fmt['filesize'] / (1024 * 1024)
                size_info = f" (~{size_mb:.0f}MB)"
            
            keyboard.append([InlineKeyboardButton(
                f"🎵 {fmt['note']}{size_info}",
                callback_data=f"yt_format_{fmt['format_id']}"
            )])
    
    # Cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_format_selection")])
    
    return InlineKeyboardMarkup(keyboard)


def create_back_keyboard():
    """Create simple back keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ])
