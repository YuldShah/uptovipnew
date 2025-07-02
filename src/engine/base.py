#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - types.py

import hashlib
import json
import logging
import re
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import final

import ffmpeg
import filetype
from pyrogram import enums, types
from tqdm import tqdm

from config import TG_NORMAL_MAX_SIZE, Types
from database import Redis
from database.model import (
    get_format_settings,
    get_quality_settings,
    log_download_completion,
)
from engine.helper import debounce, sizeof_fmt


def generate_input_media(file_paths: list, cap: str) -> list:
    input_media = []
    for path in file_paths:
        mime = filetype.guess_mime(path)
        if "video" in mime:
            input_media.append(types.InputMediaVideo(media=path))
        elif "image" in mime:
            input_media.append(types.InputMediaPhoto(media=path))
        elif "audio" in mime:
            input_media.append(types.InputMediaAudio(media=path))
        else:
            input_media.append(types.InputMediaDocument(media=path))

    input_media[0].caption = cap
    return input_media


class BaseDownloader(ABC):
    def __init__(self, client: Types.Client, bot_msg: Types.Message, url: str, download_id: int = None):
        logging.info(f"BaseDownloader initialized with URL: {url}, download_id: {download_id}")
        self._client = client
        self._url = url
        self._download_id = download_id
        self._download_start_time = time.time()  # Track download start time
        # chat id is the same for private chat
        self._chat_id = self._from_user = bot_msg.chat.id
        if bot_msg.chat.type == enums.ChatType.GROUP or bot_msg.chat.type == enums.ChatType.SUPERGROUP:
            # if in group, we need to find out who send the message
            self._from_user = bot_msg.reply_to_message.from_user.id
        self._id = bot_msg.id
        self._tempdir = tempfile.TemporaryDirectory(prefix="ytdl-")
        self._bot_msg: Types.Message = bot_msg
        self._redis = Redis()
        self._quality = get_quality_settings(self._chat_id)
        self._format = get_format_settings(self._chat_id)

    def __del__(self):
        self._tempdir.cleanup()

    def _record_usage(self):
        # Access control will be handled elsewhere - no quota system
        logging.info("User %s is downloading content", self._from_user)

    @staticmethod
    def __remove_bash_color(text):
        return re.sub(r"\u001b|\[0;94m|\u001b\[0m|\[0;32m|\[0m|\[0;33m", "", text)

    @staticmethod
    def __tqdm_progress(desc, total, finished, speed="", eta=""):
        def more(title, initial):
            if initial:
                return f"{title} {initial}"
            else:
                return ""

        f = StringIO()
        tqdm(
            total=total,
            initial=finished,
            file=f,
            ascii=False,
            unit_scale=True,
            ncols=30,
            bar_format="{l_bar}{bar} |{n_fmt}/{total_fmt} ",
        )
        raw_output = f.getvalue()
        tqdm_output = raw_output.split("|")
        progress = f"`[{tqdm_output[1]}]`"
        detail = tqdm_output[2].replace("[A", "")
        text = f"""
    {desc}

    {progress}
    {detail}
    {more("Speed:", speed)}
    {more("ETA:", eta)}
        """
        f.close()
        return text

    def download_hook(self, d: dict):
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

            if total > TG_NORMAL_MAX_SIZE:
                msg = f"Your download file size {sizeof_fmt(total)} is too large for Telegram."
                raise Exception(msg)

            # percent = remove_bash_color(d.get("_percent_str", "N/A"))
            speed = self.__remove_bash_color(d.get("_speed_str", "N/A"))
            eta = self.__remove_bash_color(d.get("_eta_str", d.get("eta")))
            text = self.__tqdm_progress("Downloading...", total, downloaded, speed, eta)
            self.edit_text(text)

    def upload_hook(self, current, total):
        text = self.__tqdm_progress("Uploading...", total, current)
        self.edit_text(text)

    @debounce(5)
    def edit_text(self, text: str):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule coroutine to run in the background
                asyncio.create_task(self._bot_msg.edit_text(text))
            else:
                loop.run_until_complete(self._bot_msg.edit_text(text))
        except Exception as e:
            logging.warning(f"Failed to edit message: {e}")

    @abstractmethod
    def _setup_formats(self) -> list | None:
        pass

    @abstractmethod
    def _download(self, formats) -> list:
        # responsible for get format and download it
        pass

    @property
    def _methods(self):
        return {
            "document": self._client.send_document,
            "audio": self._client.send_audio,
            "video": self._client.send_video,
            "animation": self._client.send_animation,
            "photo": self._client.send_photo,
        }

    async def send_something(self, *, chat_id, files, _type, caption=None, thumb=None, **kwargs):
        try:
            await self._client.send_chat_action(chat_id, enums.ChatAction.UPLOAD_DOCUMENT)
        except Exception as e:
            logging.warning(f"Failed to send chat action: {e}")
            
        is_cache = kwargs.pop("cache", False)
        if len(files) > 1 and is_cache == False:
            inputs = generate_input_media(files, caption)
            media_group_result = await self._client.send_media_group(chat_id, inputs)
            return media_group_result[0]
        else:
            file_arg_name = None
            if _type == "photo":
                file_arg_name = "photo"
            elif _type == "video":
                file_arg_name = "video"
            elif _type == "animation":
                file_arg_name = "animation"
            elif _type == "document":
                file_arg_name = "document"
            elif _type == "audio":
                file_arg_name = "audio"
            else:
                logging.error("Unknown _type encountered: %s", _type)
                # You might want to raise an error or return None here
                return None

            send_args = {
                "chat_id": chat_id,
                file_arg_name: files[0],
                "caption": caption,
                "progress": self.upload_hook,
                **kwargs,
            }

            if _type in ["video", "animation", "document", "audio"] and thumb is not None:
                send_args["thumb"] = thumb

            return await self._methods[_type](**send_args)

    def get_metadata(self):
        files = list(Path(self._tempdir.name).glob("*"))
        if not files:
            logging.error("No files found in download directory")
            raise FileNotFoundError("Download failed - no files were downloaded")
        
        # Filter out partial/temporary files for metadata extraction
        valid_files = [f for f in files if not f.name.endswith(('.part', '.tmp', '.download'))]
        if not valid_files:
            logging.error("No valid files found for metadata extraction")
            raise FileNotFoundError("Download failed - only partial/temporary files found")
        
        video_path = valid_files[0]
        filename = Path(video_path).name
        width = height = duration = 0
        is_corrupted = False
        
        try:
            # Check if file is readable before attempting ffprobe
            if video_path.stat().st_size < 100:
                raise Exception(f"File too small ({video_path.stat().st_size} bytes), likely corrupted")
            
            # Try to read file header to detect corruption early
            with open(video_path, 'rb') as f:
                header = f.read(1024)
                if len(header) < 100:
                    raise Exception("File header too small, likely corrupted")
            
            video_streams = ffmpeg.probe(video_path, select_streams="v")
            for item in video_streams.get("streams", []):
                height = item.get("height", 0)
                width = item.get("width", 0)
            duration = int(float(video_streams.get("format", {}).get("duration", 0)))
        except Exception as e:
            logging.error("Error while getting metadata: %s", e)
            is_corrupted = True
            # For corrupted files, we'll force document upload
            logging.info("File appears corrupted, will force upload as document")
            # Override format to document for corrupted files
            if hasattr(self, '_format') and self._format == "video":
                self._format = "document"
                logging.info("Changed format from video to document due to corruption")
        
        try:
            thumb = Path(video_path).parent.joinpath(f"{uuid.uuid4().hex}-thumbnail.png").as_posix()
            # Only generate thumbnail if we have valid dimensions and duration and file is not corrupted
            if width > 0 and height > 0 and duration > 0 and not is_corrupted:
                # A thumbnail's width and height should not exceed 320 pixels.
                ffmpeg.input(video_path, ss=duration / 2).filter(
                    "scale",
                    "if(gt(iw,ih),300,-1)",  # If width > height, scale width to 320 and height auto
                    "if(gt(iw,ih),-1,300)",
                ).output(thumb, vframes=1, update=True).run()
            else:
                thumb = None
        except ffmpeg._run.Error:
            thumb = None
        except Exception as e:
            logging.warning(f"Thumbnail generation failed: {e}")
            thumb = None

        # Adjust caption based on corruption status
        if is_corrupted:
            caption = f"{self._url}\n{filename}\n\n⚠️ File may be corrupted - uploaded as document"
        else:
            caption = f"{self._url}\n{filename}\n\nResolution: {width}x{height}\nDuration: {duration} seconds"
        
        # Return clean metadata without internal flags
        return dict(
            height=height, 
            width=width, 
            duration=duration, 
            thumb=thumb, 
            caption=caption, 
            is_corrupted=is_corrupted  # Keep this for internal logic only
        )

    async def _upload(self, files=None, meta=None):
        if files is None:
            files = list(Path(self._tempdir.name).glob("*"))
            if not files:
                logging.error("Upload failed - no files to upload")
                await self._bot_msg.edit_text(
                    "❌ **Download Failed**\n\n"
                    "No files were downloaded successfully.\n\n"
                    "**Possible reasons:**\n"
                    "• Content requires login/authentication\n"
                    "• Content is private or restricted\n"
                    "• Rate limiting from the platform\n"
                    "• Network connectivity issues\n\n"
                    "**For Instagram:** Try using a direct link or check if the content is public."
                )
                return
        
        # Validate and filter out corrupted/incomplete files
        valid_files = []
        for file_path in files:
            file_path_obj = Path(file_path)
            
            # Skip partial/temporary files
            if file_path_obj.name.endswith(('.part', '.tmp', '.download')):
                logging.warning(f"Skipping partial/temporary file: {file_path}")
                continue
            
            # Check if file is empty or too small
            if file_path_obj.stat().st_size < 100:  # Less than 100 bytes
                logging.warning(f"Skipping empty/tiny file: {file_path} (size: {file_path_obj.stat().st_size})")
                continue
            
            # Check if file is readable and not corrupted
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(4096)  # Read more bytes for better corruption detection
                    if len(header) < 100:
                        logging.warning(f"Skipping file with insufficient header: {file_path}")
                        continue
                    
                    # Try to seek and read from different parts of the file
                    file_size = file_path_obj.stat().st_size
                    if file_size > 8192:  # Only for files larger than 8KB
                        f.seek(file_size // 2)  # Middle of file
                        middle = f.read(1024)
                        if len(middle) < 100:
                            logging.warning(f"Skipping file with corrupted middle section: {file_path}")
                            continue
                        
                        f.seek(-1024, 2)  # Near end of file
                        end = f.read(1024)
                        if len(end) < 100:
                            logging.warning(f"Skipping file with corrupted end section: {file_path}")
                            continue
                
                valid_files.append(file_path)
                logging.info(f"File validation passed: {file_path} (size: {file_path_obj.stat().st_size})")
            except (IOError, OSError) as e:
                logging.warning(f"Skipping unreadable/corrupted file: {file_path} - {e}")
                continue
        
        if not valid_files:
            logging.error("Upload failed - no valid files found after validation")
            await self._bot_msg.edit_text(
                "❌ **Download Failed**\n\n"
                "Downloaded files are corrupted or incomplete.\n\n"
                "**Possible causes:**\n"
                "• Network interruption during download\n"
                "• Insufficient disk space\n"
                "• Source file corruption\n"
                "• Download timeout\n\n"
                "Please try again or use a different quality/format."
            )
            return
        
        files = valid_files
        logging.info(f"Validated {len(files)} files for upload: {[Path(f).name for f in files]}")
                
        if meta is None:
            try:
                meta = self.get_metadata()
            except FileNotFoundError as e:
                logging.error(f"Upload failed - metadata error: {e}")
                await self._bot_msg.edit_text(f"❌ **Processing Error**\n\n{str(e)}")
                return
            except Exception as e:
                logging.error(f"Error getting metadata: {e}")
                await self._bot_msg.edit_text(f"❌ **Processing Error**\n\nFailed to process downloaded file: {e}")
                return

        success = SimpleNamespace(document=None, video=None, audio=None, animation=None, photo=None)
        if self._format == "document":
            logging.info("Sending as document for %s", self._url)
            success = await self.send_something(
                chat_id=self._chat_id,
                files=files,
                _type="document",
                thumb=meta.get("thumb"),
                caption=meta.get("caption"),
            )
        elif self._format == "photo":
            logging.info("Sending as photo for %s", self._url)
            success = await self.send_something(
                chat_id=self._chat_id,
                files=files,
                _type="photo",
                caption=meta.get("caption"),
            )
        elif self._format == "audio":
            logging.info("Sending as audio for %s", self._url)
            success = await self.send_something(
                chat_id=self._chat_id,
                files=files,
                _type="audio",
                caption=meta.get("caption"),
            )
        elif self._format == "video":
            logging.info("Sending as video for %s", self._url)
            
            # If file is corrupted, force document upload
            if meta.get("is_corrupted", False):
                logging.warning("File is corrupted, forcing document upload")
                success = await self.send_something(
                    chat_id=self._chat_id,
                    files=files,
                    _type="document",
                    thumb=meta.get("thumb"),
                    caption=meta.get("caption"),
                )
            else:
                attempt_methods = ["video", "animation", "document"]  # Added document as fallback
                video_meta = meta.copy()

                upload_successful = False  # Flag to track if any method succeeded
                for method in attempt_methods:
                    # Create clean metadata for each upload method
                    current_meta = {
                        "height": video_meta.get("height"),
                        "width": video_meta.get("width"), 
                        "duration": video_meta.get("duration"),
                        "thumb": video_meta.get("thumb"),
                        "caption": video_meta.get("caption")
                    }

                    if method == "photo":
                        current_meta.pop("thumb", None)
                        current_meta.pop("duration", None)
                        current_meta.pop("height", None)
                        current_meta.pop("width", None)
                    elif method == "audio":
                        current_meta.pop("height", None)
                        current_meta.pop("width", None)
                    elif method == "document":
                        # For document upload, only keep caption and thumb
                        current_meta = {
                            "caption": video_meta.get("caption"),
                            "thumb": video_meta.get("thumb")
                        }

                    try:
                        success_obj = await self.send_something(
                            chat_id=self._chat_id,
                            files=files,
                            _type=method,
                            **current_meta
                        )

                        if method == "video":
                            success = success_obj
                        elif method == "animation":
                            success = success_obj
                        elif method == "document":
                            success = success_obj

                        upload_successful = True # Set flag to True on success
                        logging.info(f"Successfully uploaded as {method}")
                        break
                    except Exception as e:
                        logging.error("Failed to send as %s, error: %s", method, e)
                        if method == "document":
                            # If even document upload fails, this is a serious error
                            logging.error("Even document upload failed - file may be severely corrupted")

                # Check the flag after the loop
                if not upload_successful:
                    # Log download failure for stats
                    if self._download_id:
                        try:
                            download_time = time.time() - self._download_start_time
                            log_download_completion(self._download_id, False, error_message="Upload failed after all retries - file may be corrupted", download_time=download_time)
                            logging.info(f"Logged failed download completion for download_id: {self._download_id} (took {download_time:.2f}s)")
                        except Exception as e:
                            logging.error(f"Failed to log download failure: {e}")
                    
                    await self._bot_msg.edit_text(
                        "❌ **Upload Failed**\n\n"
                        "The downloaded file appears to be corrupted or incompatible.\n\n"
                        "**Possible solutions:**\n"
                        "• Try using `/direct` command for direct downloads\n"
                        "• Try a different quality/format\n"
                        "• Check if the source URL is still valid\n"
                        "• Report this issue if it persists"
                    )
                    return

        else:
            logging.error("Unknown upload format settings for %s", self._format)
            return

        video_key = self._calc_video_key()
        obj = success.document or success.video or success.audio or success.animation or success.photo
        mapping = {
            "file_id": json.dumps([getattr(obj, "file_id", None)]),
            "meta": json.dumps({k: v for k, v in meta.items() if k != "thumb"}, ensure_ascii=False),
        }

        self._redis.add_cache(video_key, mapping)
        
        # Log download completion for stats
        if self._download_id:
            try:
                download_time = time.time() - self._download_start_time
                log_download_completion(self._download_id, True, file_size=getattr(obj, "file_size", 0), download_time=download_time)
                logging.info(f"Logged successful download completion for download_id: {self._download_id} (took {download_time:.2f}s)")
            except Exception as e:
                logging.error(f"Failed to log download completion: {e}")
        
        # change progress bar to done
        await self._bot_msg.edit_text("✅ Success")
        return success

    def _get_video_cache(self):
        return self._redis.get_cache(self._calc_video_key())

    def _calc_video_key(self):
        h = hashlib.md5()
        # Include URL and current timestamp for uniqueness - disable caching essentially
        # This prevents URL corruption when fake redis is used
        unique_string = f"{self._url}:{self._quality}:{self._format}:{uuid.uuid4().hex}"
        h.update(unique_string.encode())
        key = h.hexdigest()
        logging.debug(f"Generated cache key: {key} for URL: {self._url}")
        return key

    @final
    async def start(self):
        # Access control will be handled at the handler level
        if cache := self._get_video_cache():
            logging.info("Cache hit for %s", self._url)
            meta, file_id = json.loads(cache["meta"]), json.loads(cache["file_id"])
            meta["cache"] = True
            await self._upload(file_id, meta)
        else:
            await self._start()
        self._record_usage()

    @abstractmethod
    def _start(self):
        pass
