#!/usr/bin/env python3
# coding: utf-8

# ytdlbot - direct.py

import logging
import os
import re
import pathlib
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import filetype
import requests

from config import ENABLE_ARIA2, TMPFILE_PATH
from engine.base import BaseDownloader


class DirectDownload(BaseDownloader):

    def _setup_formats(self) -> list | None:
        # direct download doesn't need to setup formats
        pass

    def _get_aria2_name(self):
        try:
            cmd = f"aria2c --truncate-console-readout=true -x10 --dry-run --file-allocation=none {self._url}"
            result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
            stdout_str = result.stdout.decode("utf-8")
            name = os.path.basename(stdout_str).split("\n")[0]
            if len(name) == 0:
                name = os.path.basename(self._url)
            return name
        except Exception:
            name = os.path.basename(self._url)
            return name

    def _requests_download(self):
        logging.info("Requests download with url %s", self._url)
        response = requests.get(self._url, stream=True)
        response.raise_for_status()
        
        # Try to get filename from URL or Content-Disposition header
        filename = None
        if 'content-disposition' in response.headers:
            import re
            cd = response.headers['content-disposition']
            filename_match = re.findall('filename=([^;]+)', cd)
            if filename_match:
                filename = filename_match[0].strip('"\'')
        
        if not filename:
            filename = os.path.basename(self._url) or uuid4().hex
            
        file = Path(self._tempdir.name).joinpath(filename)
        
        with open(file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # If file doesn't have extension, try to detect and add it
        if not file.suffix:
            ext = filetype.guess_extension(file)
            if ext is not None:
                new_name = file.with_suffix(f".{ext}")
                file.rename(new_name)
                file = new_name

        return [file.as_posix()]

    def _aria2_download(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.4472.124 Safari/537.36"
        filename = self._get_aria2_name()
        self._process = None
        try:
            self._bot_msg.edit_text("Aria2 download starting...")
            temp_dir = self._tempdir.name
            command = [
                "aria2c",
                "--max-tries=3",
                "--max-concurrent-downloads=8",
                "--max-connection-per-server=16",
                "--split=16",
                "--summary-interval=1",
                "--console-log-level=notice",
                "--show-console-readout=true",
                "--quiet=false",
                "--human-readable=true",
                f"--user-agent={ua}",
                "-d", temp_dir,
                "-o", filename,
                self._url,
            ]

            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            while True:
                line = self._process.stdout.readline()
                if not line:
                    if self._process.poll() is not None:
                        break
                    continue

                progress = self.__parse_progress(line)
                if progress:
                    self.download_hook(progress)
                elif "Download complete:" in line:
                    self.download_hook({"status": "complete"})

            self._process.wait(timeout=300)
            success = self._process.wait() == 0
            if not success:
                raise subprocess.CalledProcessError(
                    self._process.returncode, 
                    command, 
                    self._process.stderr.read()
                )
            if self._process.returncode != 0:
                stderr_output = self._process.stderr.read() if self._process.stderr else "Unknown error"
                raise subprocess.CalledProcessError(
                    self._process.returncode, 
                    command, 
                    stderr_output
                )

            files = [f for f in Path(temp_dir).glob("*") if f.is_file()]
            if not files:
                raise FileNotFoundError(f"No files found in {temp_dir}")

            file = files[0]
            # Handle file extension
            if not file.suffix:
                if ext := filetype.guess_extension(file):
                    new_file = file.with_suffix(f".{ext}")
                    file.rename(new_file)
                    file = new_file

            logging.info("Successfully downloaded file: %s", file)

            return [file.as_posix()]

        except subprocess.TimeoutExpired:
            error_msg = "Download timed out after 5 minutes."
            logging.error(error_msg)
            self._bot_msg.edit_text(f"Download failed!❌\n\n{error_msg}")
            return []
        except Exception as e:
            self._bot_msg.edit_text(f"Download failed!❌\n\n`{e}`")
            return []
        finally:
            if self._process:
                self._process.terminate()
                self._process = None

    def __parse_progress(self, line: str) -> dict | None:
        if "Download complete:" in line or "(OK):download completed" in line:
            return {"status": "complete"}

        progress_match = re.search(
            r'\[#\w+\s+(?P<progress>[\d.]+[KMGTP]?iB)/(?P<total>[\d.]+[KMGTP]?iB)\(.*?\)\s+CN:\d+\s+DL:(?P<speed>[\d.]+[KMGTP]?iB)\s+ETA:(?P<eta>[\dhms]+)',
            line
        )

        if progress_match:
            return {
                "status": "downloading",
                "downloaded_bytes": self.__parse_size(progress_match.group("progress")),
                "total_bytes": self.__parse_size(progress_match.group("total")),
                "_speed_str": f"{progress_match.group('speed')}/s",
                "_eta_str": progress_match.group("eta")
            }

        # Fallback check for summary lines
        if "Download Progress Summary" in line and "MiB" in line:
            return {"status": "progress", "details": line}

        return None

    def __parse_size(self, size_str: str) -> int:
        units = {
            "B": 1, 
            "K": 1024, "KB": 1024, "KIB": 1024,
            "M": 1024**2, "MB": 1024**2, "MIB": 1024**2,
            "G": 1024**3, "GB": 1024**3, "GIB": 1024**3,
            "T": 1024**4, "TB": 1024**4, "TIB": 1024**4
        }
        match = re.match(r"([\d.]+)([A-Za-z]*)", size_str.replace("i", "").upper())
        if match:
            number, unit = match.groups()
            unit = unit or "B"
            return int(float(number) * units.get(unit, 1))
        return 0

    def _download(self, formats=None) -> list:
        if ENABLE_ARIA2:
            return self._aria2_download()
        return self._requests_download()

    async def _start(self):
        downloaded_files = self._download()
        if downloaded_files:
            # Auto-detect file type and override format setting for proper handling
            self._auto_detect_format(downloaded_files[0])
            await self._upload(files=downloaded_files)

    def _auto_detect_format(self, file_path: str):
        """Auto-detect file type and set appropriate format for upload"""
        try:
            # Get file extension and MIME type
            file_ext = Path(file_path).suffix.lower()
            
            # Try to detect MIME type
            mime_type = filetype.guess_mime(file_path)
            
            # Archive/compressed files should be sent as documents
            archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2', '.tar.xz'}
            document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.xlsx', '.xls', '.ppt', '.pptx'}
            
            if file_ext in archive_extensions or file_ext in document_extensions:
                logging.info(f"Auto-detected {file_ext} file, setting format to document")
                self._format = "document"
            elif mime_type:
                if mime_type.startswith('video/'):
                    logging.info(f"Auto-detected video file ({mime_type}), keeping video format")
                    self._format = "video"
                elif mime_type.startswith('audio/'):
                    logging.info(f"Auto-detected audio file ({mime_type}), setting format to audio")
                    self._format = "audio"
                elif mime_type.startswith('image/'):
                    logging.info(f"Auto-detected image file ({mime_type}), setting format to photo")
                    self._format = "photo"
                else:
                    logging.info(f"Auto-detected other file type ({mime_type}), setting format to document")
                    self._format = "document"
            else:
                # If can't detect, default to document for safety
                logging.info(f"Could not detect file type for {file_ext}, defaulting to document")
                self._format = "document"
                
        except Exception as e:
            logging.error(f"Error in auto file type detection: {e}, defaulting to document")
            self._format = "document"
