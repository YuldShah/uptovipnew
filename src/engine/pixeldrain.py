#!/usr/bin/env python3
# coding: utf-8

import tempfile
import pathlib
import re
from urllib.parse import urlparse
from engine.direct import DirectDownload


async def pixeldrain_download(client, bot_message, url):
    FILE_URL_FORMAT = "https://pixeldrain.com/api/file/{}?download"
    USER_PAGE_PATTERN = re.compile(r"https://pixeldrain.com/u/(\w+)")

    def _extract_file_id(url):
        if match := USER_PAGE_PATTERN.match(url):
            return match.group(1)

        parsed = urlparse(url)
        if parsed.path.startswith('/file/'):
            return parsed.path.split('/')[-1]

        raise ValueError("Invalid Pixeldrain URL format")

    def _get_download_url(file_id):
        return FILE_URL_FORMAT.format(file_id)

    async def _download(url):
        try:
            file_id = _extract_file_id(url)
            download_url = _get_download_url(file_id)

            ddl = DirectDownload(client, bot_message, download_url)
            await ddl.start()

        except ValueError as e:
            await bot_message.edit_text(f"Download failed!❌\n\n`{e}`")
        except Exception as e:
            await bot_message.edit_text(
                f"Download failed!❌\nAn error occurred: {str(e)}\n"
                "Please check your URL and try again."
            )

    await _download(url)