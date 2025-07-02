#!/usr/bin/env python3
"""
YouTube Download Test Script for YTDLBot
Tests different extraction methods and formats
"""

import os
import yt_dlp
from pathlib import Path

def test_youtube_extraction():
    """Test YouTube extraction with different configurations"""
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    cookie_file = "youtube-cookies.txt"
    
    print("🧪 Testing YouTube Extraction Methods\n")
    
    # Test 1: With cookies file
    print("1️⃣ Testing with youtube-cookies.txt")
    if os.path.isfile(cookie_file) and os.path.getsize(cookie_file) > 100:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'cookiefile': cookie_file,
                'extract_flat': False,
                'format': 'best[height<=720]/best',
                'extractor_args': {
                    'youtube': [
                        'player-client=web,default',
                        'player-skip=webpage,configs',
                        'comment-sort=top',
                        'max-comments=0'
                    ]
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                formats = len(info.get('formats', []))
                print(f"   ✅ Success: {title}")
                print(f"   📹 Duration: {duration}s, Formats: {formats}")
                return True
                
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
    else:
        print(f"   ⚠️  Cookie file not found or empty")
    
    # Test 2: Without cookies
    print("\n2️⃣ Testing without cookies")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
            'format': 'best[height<=480]/best',
            'extractor_args': {
                'youtube': [
                    'player-client=web,default',
                    'player-skip=webpage,configs'
                ]
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            title = info.get('title', 'Unknown')
            print(f"   ✅ Success: {title}")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
    
    # Test 3: With different client
    print("\n3️⃣ Testing with mobile client")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': False,
            'cookiefile': cookie_file if os.path.isfile(cookie_file) else None,
            'format': 'best[height<=480]/worst',
            'extractor_args': {
                'youtube': [
                    'player-client=android,web',
                    'player-skip=configs'
                ]
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            title = info.get('title', 'Unknown')
            print(f"   ✅ Success: {title}")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
    
    # Test 4: List formats
    print("\n4️⃣ Testing format listing")
    try:
        ydl_opts = {
            'quiet': True,
            'listformats': True,
            'cookiefile': cookie_file if os.path.isfile(cookie_file) else None,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(test_url, download=False)
            formats = info.get('formats', [])
            print(f"   📋 Available formats: {len(formats)}")
            
            # Show some format details
            for fmt in formats[:5]:
                print(f"      • {fmt.get('format_id')}: {fmt.get('ext')} "
                      f"{fmt.get('resolution', 'audio')} "
                      f"{fmt.get('vcodec', 'none')} "
                      f"{fmt.get('acodec', 'none')}")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
    
    print("\n❌ All tests failed - YouTube extraction not working")
    return False

def check_environment():
    """Check environment setup"""
    print("🔍 Environment Check\n")
    
    # Check yt-dlp version
    try:
        import yt_dlp
        print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")
    except Exception as e:
        print(f"❌ yt-dlp issue: {e}")
        return False
    
    # Check cookie file
    cookie_file = "youtube-cookies.txt"
    if os.path.isfile(cookie_file):
        size = os.path.getsize(cookie_file)
        print(f"✅ Cookie file: {size} bytes")
    else:
        print("⚠️  No cookie file found")
    
    # Check environment variables
    browsers = os.getenv("BROWSERS", "")
    potoken = os.getenv("POTOKEN", "")
    print(f"📝 BROWSERS: {browsers or 'Not set'}")
    print(f"📝 POTOKEN: {potoken or 'Not set'}")
    
    return True

if __name__ == "__main__":
    print("🎬 YTDLBot YouTube Test Suite\n")
    
    if check_environment():
        print("\n" + "="*50)
        test_youtube_extraction()
    
    print("\n🎯 Recommendations:")
    print("1. Update yt-dlp: pip install --upgrade yt-dlp")
    print("2. Ensure cookie file has valid YouTube cookies")
    print("3. Leave BROWSERS empty in .env to use cookie file")
    print("4. Consider getting a PO token for better reliability")
