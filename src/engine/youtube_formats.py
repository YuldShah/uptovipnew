#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - youtube_formats.py
# YouTube format extraction and URL validation functions

import logging
import yt_dlp
from urllib.parse import urlparse
from utils import is_youtube


def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a YouTube URL.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if it's a YouTube URL, False otherwise
    """
    return is_youtube(url)


def extract_youtube_formats(url: str) -> dict:
    """
    Extract available video and audio formats from a YouTube URL.
    
    Args:
        url (str): YouTube URL
        
    Returns:
        dict: Dictionary containing 'video_formats' and 'audio_formats' lists
    """
    if not is_youtube_url(url):
        return {'video_formats': [], 'audio_formats': []}
    
    try:
        # Configure yt-dlp options for format extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'listformats': False,
            'extract_flat': False,
        }
        
        # Add cookies if available
        import os
        if os.path.isfile("youtube-cookies.txt") and os.path.getsize("youtube-cookies.txt") > 100:
            ydl_opts["cookiefile"] = "youtube-cookies.txt"
        
        # Add extractor args for better YouTube compatibility
        extractor_args = {"youtube": ["player-client=web,default"]}
        ydl_opts["extractor_args"] = extractor_args
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(url, download=False)
            
            if not info or 'formats' not in info:
                return {'video_formats': [], 'audio_formats': []}
            
            video_formats = []
            audio_formats = []
            
            # Process available formats
            for fmt in info['formats']:
                if not fmt.get('url'):
                    continue
                    
                format_info = {
                    'format_id': fmt.get('format_id', ''),
                    'ext': fmt.get('ext', ''),
                    'quality': fmt.get('quality', ''),
                    'format_note': fmt.get('format_note', ''),
                    'filesize': fmt.get('filesize'),
                    'filesize_approx': fmt.get('filesize_approx'),
                    'vcodec': fmt.get('vcodec', 'none'),
                    'acodec': fmt.get('acodec', 'none'),
                    'height': fmt.get('height'),
                    'width': fmt.get('width'),
                    'fps': fmt.get('fps'),
                    'abr': fmt.get('abr'),  # Audio bitrate
                    'vbr': fmt.get('vbr'),  # Video bitrate
                    'tbr': fmt.get('tbr'),  # Total bitrate
                }
                
                # Categorize formats
                if fmt.get('vcodec') and fmt.get('vcodec') != 'none':
                    if fmt.get('acodec') and fmt.get('acodec') != 'none':
                        # Combined video+audio format
                        format_info['type'] = 'video+audio'
                        video_formats.append(format_info)
                    else:
                        # Video-only format
                        format_info['type'] = 'video-only'
                        video_formats.append(format_info)
                elif fmt.get('acodec') and fmt.get('acodec') != 'none':
                    # Audio-only format
                    format_info['type'] = 'audio-only'
                    audio_formats.append(format_info)
            
            # Sort formats by quality (highest first)
            video_formats.sort(key=lambda x: (
                x.get('height', 0) or 0,
                x.get('tbr', 0) or 0,
                x.get('vbr', 0) or 0
            ), reverse=True)
            
            audio_formats.sort(key=lambda x: (
                x.get('abr', 0) or 0,
                x.get('tbr', 0) or 0
            ), reverse=True)
            
            return {
                'video_formats': video_formats,
                'audio_formats': audio_formats,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count'),
            }
            
    except Exception as e:
        logging.error(f"Error extracting YouTube formats: {e}")
        return {'video_formats': [], 'audio_formats': []}


def get_format_display_name(format_info: dict) -> str:
    """
    Generate a user-friendly display name for a format.
    
    Args:
        format_info (dict): Format information dictionary
        
    Returns:
        str: Display name for the format
    """
    parts = []
    
    # Add quality info
    if format_info.get('height'):
        parts.append(f"{format_info['height']}p")
    elif format_info.get('format_note'):
        parts.append(format_info['format_note'])
    
    # Add codec info
    if format_info.get('vcodec') and format_info['vcodec'] != 'none':
        parts.append(format_info['vcodec'])
    
    if format_info.get('acodec') and format_info['acodec'] != 'none':
        parts.append(format_info['acodec'])
    
    # Add extension
    if format_info.get('ext'):
        parts.append(format_info['ext'])
    
    # Add file size if available
    filesize = format_info.get('filesize') or format_info.get('filesize_approx')
    if filesize:
        from utils import sizeof_fmt
        parts.append(sizeof_fmt(filesize))
    
    # Add type indicator
    format_type = format_info.get('type', '')
    if format_type == 'video+audio':
        parts.append('📹🔊')
    elif format_type == 'video-only':
        parts.append('📹')
    elif format_type == 'audio-only':
        parts.append('🔊')
    
    return ' | '.join(filter(None, parts))


def get_best_format_ids(formats_dict: dict) -> dict:
    """
    Get the best format IDs for different quality levels.
    
    Args:
        formats_dict (dict): Dictionary containing video_formats and audio_formats
        
    Returns:
        dict: Dictionary with best format IDs for different qualities
    """
    video_formats = formats_dict.get('video_formats', [])
    audio_formats = formats_dict.get('audio_formats', [])
    
    best_formats = {
        'best_video': None,
        'best_audio': None,
        'worst_video': None,
        'worst_audio': None,
    }
    
    # Find best video format (highest quality)
    if video_formats:
        best_formats['best_video'] = video_formats[0]['format_id']
        best_formats['worst_video'] = video_formats[-1]['format_id']
    
    # Find best audio format (highest quality)
    if audio_formats:
        best_formats['best_audio'] = audio_formats[0]['format_id']
        best_formats['worst_audio'] = audio_formats[-1]['format_id']
    
    return best_formats
