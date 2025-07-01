# ytdlbot

**YouTube Download Bot**

This Telegram bot allows you to download videos from YouTube and other supported websites.

# Usage

Just send a link directly to the bot.

# Supported websites

* YouTube
* Any websites [supported by yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

  ### Specific link downloader (Use /spdl for these links)
    * Instagram (Videos, Photos, Reels, IGTV & carousel)
    * Pixeldrain
    * KrakenFiles

# Features

1. Fast download and upload
2. Download & upload progress bar
3. Download quality selection
4. Upload format: file, video, audio
5. Cache mechanism - download once for the same video
6. Supports multiple download engines (yt-dlp, aria2, requests)

# Screenshots

## Normal download

![](assets/1.jpeg)

## Instagram download

![](assets/instagram.png)

![](assets/2.jpeg)

# How to deploy?

This bot can be deployed on any platform that supports Python.

## Run natively on your machine

> Project use PDM to manage dependencies.

1. <details>
    <summary>Install PDM</summary>

    You can install using pip: `pip install --user pdm`
    or for detailed instructions: [Official Docs](https://pdm-project.org/en/latest/#installation)
  
   </details>

2. Install modules using PDM: `pdm install`, or the old way use `pip install -r requirements.txt`

3. <details>
    <summary>Setting up config file</summary>

    ```
    cp .env.example .env
    ```
    
    Fill the fields in `.env`. For more information, see the comments in the `.env.example` file.

    **- Required Fields**
    - `WORKERS`: Number of workers (default is 100)
    - `APP_ID`: Telegram app ID
    - `APP_HASH`: Telegram app hash
    - `BOT_TOKEN`: Your telegram bot token
    - `OWNER`: Owner ID (separate by `,`)
    - `AUTHORIZED_USER`: List of authorized users ids, (separate by `,`)
    - `DB_DSN`: Your database URL (postgresql+psycopg2://user:pass@postgres/dbname) or SQLite (sqlite:///db.sqlite)
    - `REDIS_HOST`: Redis host

    **- Optional Fields**
    - `ENABLE_FFMPEG`: Enable FFMPEG for video processing (True/False)
    - `AUDIO_FORMAT`: Desired audio format (e.g.:- mp3, wav)
    - `ENABLE_ARIA2`: Enable Aria2 for downloads (True/False)
    - `RCLONE_PATH`: Path to Rclone executable
    - `RATE_LIMIT`: Rate limit for requests
    - `TMPFILE_PATH`: Path for temporary/download files (ensure the directory exists and is writable)
    - `TG_NORMAL_MAX_SIZE`: Maximum size for Telegram uploads in MB
    - `CAPTION_URL_LENGTH_LIMIT`: Maximum URL length in captions
    - `POTOKEN`: Your PO Token.  [PO-Token-Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
    - `BROWSERS`: Browser to handle 'cookies from browser', i.e. firefox
  </details>

4. Activate virtual environment that created by PDM: `source .venv/bin/activate`

5. Finally run the bot: `python src/main.py`

## Docker

One line command to run the bot

```shell
docker run --env-file .env ytdlbot
```

# Commands

```
start - Let's start
about - What's this bot?
help - Help
spdl - Use to download specific link downloader links
direct - Download using aria2/requests engines
ytdl - Download video in group
settings - Set your preference
unsub - Unsubscribe from YouTube Channel
ping - Ping the Bot
stats - Server and bot stats
```

# Test data

<details><summary>Tap to expand</summary>

## Test video

https://www.youtube.com/watch?v=V3RtA-1b_2E

## Test Playlist

https://www.youtube.com/playlist?list=PL1Hdq7xjQCJxQnGc05gS4wzHWccvEJy0w

## Test instagram

* single image: https://www.instagram.com/p/CXpxSyOrWCA/
* single video: https://www.instagram.com/p/Cah_7gnDVUW/
* reels: https://www.instagram.com/p/C0ozGsjtY0W/
* image carousel: https://www.instagram.com/p/C0ozPQ5o536/
* video and image carousel: https://www.instagram.com/p/C0ozhsVo-m8/

## Test Pixeldrain

https://pixeldrain.com/u/765ijw9i

## Test KrakenFiles

https://krakenfiles.com/view/oqmSTF0T5t/file.html

</details>

# License

Apache License 2.0
