#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - generic.py

import logging
import os
import time
from pathlib import Path

import yt_dlp

from config import AUDIO_FORMAT
from utils import is_youtube
from database.model import get_format_settings, get_quality_settings, log_download_completion
from engine.base import BaseDownloader


def match_filter(info_dict):
    if info_dict.get("is_live"):
        raise NotImplementedError("Skipping live video")
    return None  # Allow download for non-live videos


class YoutubeDownload(BaseDownloader):
    @staticmethod
    def get_format(m):
        return [
            f"bestvideo[ext=mp4][height={m}]+bestaudio[ext=m4a]",
            f"bestvideo[vcodec^=avc][height={m}]+bestaudio[acodec^=mp4a]/best[vcodec^=avc]/best",
        ]

    def _setup_formats(self) -> list | None:
        if not is_youtube(self._url):
            return [None]

        quality, format_ = get_quality_settings(self._chat_id), get_format_settings(self._chat_id)
        # quality: high, medium, low, custom
        # format: audio, video, document
        formats = []
        defaults = [
            # webm , vp9 and av01 are not streamable on telegram, so we'll extract only mp4
            "bestvideo[ext=mp4][vcodec!*=av01][vcodec!*=vp09]+bestaudio[ext=m4a]/bestvideo+bestaudio",
            "bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/best[vcodec^=avc]/best",
            None,
        ]
        audio = AUDIO_FORMAT or "m4a"
        maps = {
            "high-audio": [f"bestaudio[ext={audio}]"],
            "high-video": defaults,
            "high-document": defaults,
            "medium-audio": [f"bestaudio[ext={audio}]"],  # no mediumaudio :-(
            "medium-video": self.get_format(720),
            "medium-document": self.get_format(720),
            "low-audio": [f"bestaudio[ext={audio}]"],
            "low-video": self.get_format(480),
            "low-document": self.get_format(480),
            "custom-audio": "",
            "custom-video": "",
            "custom-document": "",
        }

        if quality == "custom":
            pass
            # TODO not supported yet
            # get format from ytdlp, send inlinekeyboard button to user so they can choose
            # another callback will be triggered to download the video
            # available_options = {
            #     "480P": "best[height<=480]",
            #     "720P": "best[height<=720]",
            #     "1080P": "best[height<=1080]",
            # }
            # markup, temp_row = [], []
            # for quality, data in available_options.items():
            #     temp_row.append(types.InlineKeyboardButton(quality, callback_data=data))
            #     if len(temp_row) == 3:  # Add a row every 3 buttons
            #         markup.append(temp_row)
            #         temp_row = []
            # # Add any remaining buttons as the last row
            # if temp_row:
            #     markup.append(temp_row)
            # self._bot_msg.edit_text("Choose the format", reply_markup=types.InlineKeyboardMarkup(markup))
            # return None

        formats.extend(maps[f"{quality}-{format_}"])
        # extend default formats if not high*
        if quality != "high":
            formats.extend(defaults)
        return formats

    def _download(self, formats) -> list:
        output = Path(self._tempdir.name, "%(title).70s.%(ext)s").as_posix()
        ydl_opts = {
            "progress_hooks": [lambda d: self.download_hook(d)],
            "outtmpl": output,
            "restrictfilenames": False,
            "quiet": True,
            "match_filter": match_filter,
        }
        # setup cookies for youtube only
        if is_youtube(self._url):
            # Use cookie file first (more reliable than browser extraction)
            if os.path.isfile("youtube-cookies.txt") and os.path.getsize("youtube-cookies.txt") > 100:
                ydl_opts["cookiefile"] = "youtube-cookies.txt"
            # fallback to browser cookies if no cookie file
            elif browsers := os.getenv("BROWSERS"):
                ydl_opts["cookiesfrombrowser"] = browsers.split(",")
            
            # Add extractor args for better YouTube compatibility
            extractor_args = {"youtube": ["player-client=web,default"]}
            
            # Add PO token if available
            if potoken := os.getenv("POTOKEN"):
                extractor_args["youtube"].append(f"po_token=web+{potoken}")
            
            # Add other YouTube-specific options for better compatibility
            extractor_args["youtube"].extend([
                "player-skip=webpage,configs",
                "comment-sort=top",
                "max-comments=0"
            ])
            
            ydl_opts["extractor_args"] = extractor_args

        if self._url.startswith("https://drive.google.com"):
            # Always use the `source` format for Google Drive URLs.
            formats = ["source"] + formats

        files = None
        for f in formats:
            ydl_opts["format"] = f
            logging.info("yt-dlp options: %s", ydl_opts)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self._url])
                files = list(Path(self._tempdir.name).glob("*"))
                if files:  # Successfully downloaded files
                    break
                else:
                    logging.warning(f"No files downloaded with format {f}")
            except Exception as e:
                logging.error(f"Download failed with format {f}: {e}")
                # Continue to next format
                continue

        return files

    async def _start(self, formats=None):
        # start download and upload, no cache hit
        # user can choose format by clicking on the button(custom config)
        default_formats = self._setup_formats()
        if formats is not None:
            # formats according to user choice
            default_formats = formats + self._setup_formats()
        
        try:
            files = self._download(default_formats)
            
            # Check if download was successful
            if not files:
                error_msg = "No files were downloaded"
                await self._bot_msg.edit_text(
                    "❌ **Download Failed**\n\n"
                    "No files were downloaded. This could be due to:\n"
                    "• **Authentication required** (login/cookies needed)\n"
                    "• **Content not available** or private\n"
                    "• **Rate limiting** from the platform\n"
                    "• **Network issues**\n\n"
                    "For Instagram, try:\n"
                    "• Using a public post URL\n"
                    "• Adding cookies for authentication\n"
                    "• Trying again later if rate-limited"
                )
                
                # Log download failure for stats
                if self._download_id:
                    try:
                        download_time = time.time() - self._download_start_time
                        log_download_completion(self._download_id, False, error_message=error_msg, download_time=download_time)
                        logging.info(f"Logged failed download (no files) for download_id: {self._download_id} (took {download_time:.2f}s)")
                    except Exception as log_e:
                        logging.error(f"Failed to log download failure: {log_e}")
                
                return
            
            await self._upload()
            
        except Exception as e:
            logging.error(f"Download failed for {self._url}: {e}")
            error_msg = str(e)
            
            # Provide specific error messages for common issues
            if "login required" in error_msg.lower() or "authentication" in error_msg.lower():
                await self._bot_msg.edit_text(
                    "🔐 **Authentication Required**\n\n"
                    "This content requires login to access.\n\n"
                    "**For Instagram:**\n"
                    "• Make sure the post is public\n"
                    "• Try a different URL format\n"
                    "• Contact admin if cookies need to be configured"
                )
            elif "rate" in error_msg.lower() and "limit" in error_msg.lower():
                await self._bot_msg.edit_text(
                    "⏱️ **Rate Limited**\n\n"
                    "Too many requests to the platform.\n\n"
                    "Please try again in a few minutes."
                )
            elif "not available" in error_msg.lower() or "private" in error_msg.lower():
                await self._bot_msg.edit_text(
                    "🚫 **Content Not Available**\n\n"
                    "The requested content is:\n"
                    "• Private or restricted\n"
                    "• Deleted or moved\n"
                    "• Not accessible from this region\n\n"
                    "Please check the URL and try again."
                )
            else:
                await self._bot_msg.edit_text(f"❌ **Download Error**\n\n{error_msg}")
            
            # Log download failure for stats
            if self._download_id:
                try:
                    download_time = time.time() - self._download_start_time
                    log_download_completion(self._download_id, False, error_message=error_msg, download_time=download_time)
                    logging.info(f"Logged failed download completion for download_id: {self._download_id} (took {download_time:.2f}s)")
                except Exception as log_e:
                    logging.error(f"Failed to log download failure: {log_e}")
            
            raise  # Re-raise for logging purposes
