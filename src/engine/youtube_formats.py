#!/usr/bin/env python3
# coding: utf-8

import logging
from typing import Dict, List

import yt_dlp

logger = logging.getLogger(__name__)


def get_youtube_available_formats(url: str) -> Dict:
    """
    Get ACTUAL available formats for specific YouTube video
    Only returns formats that exist for this video
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format_sort': ['res', 'ext:mp4:m4a', 'proto'],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            video_formats = []
            audio_formats = []
            
            # Process actual available formats
            for f in formats:
                if not f.get('format_id'):
                    continue
                
                # Video + Audio format (preferred)
                if (f.get('vcodec') != 'none' and f.get('acodec') != 'none' and 
                    f.get('height') and f.get('ext')):
                    video_formats.append({
                        'format_id': f['format_id'],
                        'resolution': f.get('height'),
                        'ext': f.get('ext', 'mp4'),
                        'note': f"{f.get('height')}p ({f.get('ext', 'mp4')})",
                        'filesize': f.get('filesize') or f.get('filesize_approx', 0),
                        'fps': f.get('fps'),
                        'vcodec': f.get('vcodec'),
                        'acodec': f.get('acodec')
                    })
                
                # Audio only format
                elif (f.get('acodec') != 'none' and f.get('vcodec') == 'none' and 
                      f.get('abr') and f.get('ext')):
                    audio_formats.append({
                        'format_id': f['format_id'],
                        'quality': f.get('abr'),
                        'ext': f.get('ext', 'm4a'),
                        'note': f"Audio Only ({f.get('abr')}kbps {f.get('ext', 'm4a')})",
                        'filesize': f.get('filesize') or f.get('filesize_approx', 0),
                        'acodec': f.get('acodec')
                    })
            
            # Remove duplicates and sort
            video_formats = _deduplicate_formats(video_formats, 'resolution')
            audio_formats = _deduplicate_formats(audio_formats, 'quality')
            
            # Sort by quality (highest first)
            video_formats.sort(key=lambda x: x['resolution'] or 0, reverse=True)
            audio_formats.sort(key=lambda x: x['quality'] or 0, reverse=True)
            
            # Limit to reasonable number of options
            return {
                'video_formats': video_formats[:8],  # Limit to 8 video options
                'audio_formats': audio_formats[:4],  # Limit to 4 audio options
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader')
            }
            
    except Exception as e:
        logger.error(f"Error extracting YouTube formats for {url}: {e}")
        return {
            'video_formats': [],
            'audio_formats': [],
            'title': 'Unknown',
            'duration': None,
            'uploader': None,
            'error': str(e)
        }


def _deduplicate_formats(formats: List[Dict], key: str) -> List[Dict]:
    """Remove duplicate formats based on key"""
    seen = set()
    unique_formats = []
    
    for fmt in formats:
        value = fmt.get(key)
        if value not in seen:
            seen.add(value)
            unique_formats.append(fmt)
    
    return unique_formats


def create_youtube_format_keyboard(formats: Dict) -> List[List[Dict]]:
    """Create inline keyboard for YouTube format selection"""
    keyboard = []
    
    # Video formats
    if formats.get('video_formats'):
        keyboard.append([{'text': '🎬 Video Quality Options:', 'callback_data': 'separator'}])
        for fmt in formats['video_formats']:
            size_info = ""
            if fmt.get('filesize') and fmt['filesize'] > 0:
                size_mb = fmt['filesize'] / (1024 * 1024)
                size_info = f" (~{size_mb:.0f}MB)"
            
            keyboard.append([{
                'text': f"🎬 {fmt['note']}{size_info}",
                'callback_data': f"yt_format_{fmt['format_id']}"
            }])
    
    # Audio formats
    if formats.get('audio_formats'):
        if keyboard:  # Add separator if we have video formats
            keyboard.append([{'text': '━━━━━━━━━━━━━━━━━━━━', 'callback_data': 'separator'}])
        keyboard.append([{'text': '🎵 Audio Only Options:', 'callback_data': 'separator'}])
        for fmt in formats['audio_formats']:
            size_info = ""
            if fmt.get('filesize') and fmt['filesize'] > 0:
                size_mb = fmt['filesize'] / (1024 * 1024)
                size_info = f" (~{size_mb:.0f}MB)"
            
            keyboard.append([{
                'text': f"🎵 {fmt['note']}{size_info}",
                'callback_data': f"yt_format_{fmt['format_id']}"
            }])
    
    # Cancel button
    keyboard.append([{'text': '❌ Cancel', 'callback_data': 'cancel_format_selection'}])
    
    return keyboard


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to"""
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'pixeldrain.com' in url_lower:
        return 'pixeldrain'
    elif 'krakenfiles.com' in url_lower:
        return 'krakenfiles'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    else:
        return 'other'


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL"""
    return detect_platform(url) == 'youtube'
