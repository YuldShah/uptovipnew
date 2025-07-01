#!/usr/local/bin/python3
# coding: utf-8

import typing

from pyrogram import Client, types


class BotText:

    start = """Welcome to YouTube Download bot. Type /help for more information."""

    help = """
1. For YouTube and any websites supported by yt-dlp, just send the link and we will process and send it to you.

2. For specific links use `/spdl {URL}`.

3. If the bot doesn't work, try again later.
    """

    about = "YouTube Download Bot - Private Access"

    settings = """
Please choose the preferred format and video quality for your video. These settings only **apply to YouTube videos**.
High: 1080P
Medium: 720P
Low: 480P

If you choose to send the video as a document, Telegram client will not be able stream it.

Your current settings:
Video quality: {}
Sending type: {}
"""


class Types:
    Message = typing.Union[types.Message, typing.Coroutine]
    Client = Client
