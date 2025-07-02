#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - instagram.py

import time
import pathlib
import re

import filetype
import requests
from engine.base import BaseDownloader


class InstagramDownload(BaseDownloader):
    def extract_code(self):
        patterns = [
            # Instagram stories highlights
            r"/stories/highlights/([a-zA-Z0-9_-]+)/",
            # Posts
            r"/p/([a-zA-Z0-9_-]+)/",
            # Reels
            r"/reel/([a-zA-Z0-9_-]+)/",
            # TV
            r"/tv/([a-zA-Z0-9_-]+)/",
            # Threads post (both with @username and without)
            r"(?:https?://)?(?:www\.)?(?:threads\.net)(?:/[@\w.]+)?(?:/post)?/([\w-]+)(?:/?\?.*)?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, self._url)
            if match:
                if pattern == patterns[0]:  # Check if it's the stories highlights pattern
                    # Return the URL as it is
                    return self._url
                else:
                    # Return the code part (first group)
                    return match.group(1)

        return None

    def _setup_formats(self) -> list | None:
        pass

    async def _download(self, formats=None):
        # Use yt-dlp with Instagram cookies instead of external service
        try:
            import os
            import yt_dlp
            from pathlib import Path
            
            # Configure yt-dlp options for Instagram
            ydl_opts = {
                'outtmpl': str(Path(self._tempdir.name) / '%(title).70s.%(ext)s'),
                'progress_hooks': [lambda d: self.download_hook(d)],
                'quiet': True,
                'no_warnings': True,
            }
            
            # Try to use Instagram cookies
            cookie_files = ['instagram-cookies.txt', 'cookies.txt']
            cookie_found = False
            
            for cookie_file in cookie_files:
                if os.path.isfile(cookie_file) and os.path.getsize(cookie_file) > 50:
                    ydl_opts['cookiefile'] = cookie_file
                    cookie_found = True
                    break
            
            if not cookie_found:
                # Try browser cookies as fallback
                if browsers := os.getenv("BROWSERS"):
                    ydl_opts['cookiesfrombrowser'] = (browsers.split(",")[0], None)
                else:
                    await self._bot_msg.edit_text(
                        "❌ **Instagram Authentication Required**\n\n"
                        "Instagram downloads require authentication. Please:\n\n"
                        "**Option 1: Add Cookie File**\n"
                        "• Extract cookies from your browser\n"
                        "• Save as `instagram-cookies.txt` in bot directory\n\n"
                        "**Option 2: Set Browser in .env**\n"
                        "• Add `BROWSERS=chrome` to your .env file\n"
                        "• Make sure you're logged into Instagram in that browser\n\n"
                        "**Option 3: Use public content only**\n"
                        "• Try with public Instagram posts (some may work without auth)"
                    )
                    return []
            
            # Download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to check if it's accessible
                try:
                    info = ydl.extract_info(self._url, download=False)
                    if not info:
                        await self._bot_msg.edit_text(
                            "❌ **Instagram Content Not Accessible**\n\n"
                            "This Instagram content might be:\n"
                            "• Private account\n"
                            "• Deleted or unavailable\n"
                            "• Restricted in your region\n"
                            "• Requires login to view"
                        )
                        return []
                    
                    # Update progress message
                    await self._bot_msg.edit_text(f"📱 **Downloading Instagram content...**\n\n🎬 Title: {info.get('title', 'Unknown')[:50]}")
                    
                    # Now download
                    ydl.download([self._url])
                    
                except Exception as e:
                    await self._bot_msg.edit_text(
                        f"❌ **Instagram Download Failed**\n\n"
                        f"Error: {str(e)[:200]}\n\n"
                        "This might be due to:\n"
                        "• Authentication issues\n"
                        "• Private content\n"
                        "• Rate limiting\n"
                        "• Instagram restrictions"
                    )
                    return []
            
            # Get downloaded files
            files = list(Path(self._tempdir.name).glob("*"))
            if not files:
                await self._bot_msg.edit_text(
                    "❌ **No Files Downloaded**\n\n"
                    "Instagram download completed but no files were found. This could be due to:\n"
                    "• Content format not supported\n"
                    "• Download was blocked\n"
                    "• Authentication issues"
                )
                return []
            
            # Determine format based on file types
            video_files = [f for f in files if f.suffix.lower() in ['.mp4', '.mkv', '.webm']]
            image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
            
            if video_files:
                self._format = "video"
            elif image_files:
                self._format = "photo"
            else:
                self._format = "document"
            
            return [str(f) for f in files]
            
        except ImportError:
            await self._bot_msg.edit_text(
                "❌ **Missing Dependencies**\n\n"
                "yt-dlp is required for Instagram downloads. Please install it:\n"
                "`pip install yt-dlp`"
            )
            return []
        except Exception as e:
            await self._bot_msg.edit_text(
                f"❌ **Instagram Download Error**\n\n"
                f"Unexpected error: {str(e)[:200]}\n\n"
                "Please try again or contact admin if the issue persists."
            )
            return []

    async def _start(self):
        downloaded_files = await self._download()
        if downloaded_files:  # Only upload if download was successful
            await self._upload(files=downloaded_files)
