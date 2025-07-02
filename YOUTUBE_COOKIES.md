# YouTube Cookies Configuration - Working Setup

## ✅ Your Current Working Configuration

Since your `youtube-cookies.txt` file is working perfectly, here's your optimal configuration:

### **Your .env File Should Have:**

```bash
# Leave BROWSERS empty since you have working youtube-cookies.txt
BROWSERS=

# Optional: Add PO token if you have rate limiting issues
POTOKEN=

# Your other required settings
APP_ID=your_app_id
APP_HASH=your_app_hash
BOT_TOKEN=your_bot_token
ADMIN_IDS=your_admin_ids
DB_DSN=your_database_connection
```

## 🎯 How Your Bot Handles YouTube Downloads

Based on your `generic.py` engine, the bot will:

1. **Skip browser cookies** (since BROWSERS is empty)
2. **Use your youtube-cookies.txt file** (if file exists and > 100 bytes)
3. **Apply format filtering** for better compatibility

## 🔧 Cookie File Requirements

Your `youtube-cookies.txt` file should be:
- ✅ **In the bot's root directory** (same level as main.py)
- ✅ **Netscape/Mozilla cookie format**
- ✅ **More than 100 bytes** (bot checks file size)
- ✅ **Recent and valid** (not expired)

## 🧪 Test Your Setup

Test that your bot can extract video info:

```bash
# Test extraction with your working format
yt-dlp --cookies youtube-cookies.txt --format "best[height<=720]" --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Test different quality levels
yt-dlp --cookies youtube-cookies.txt --format "best[height<=480]" --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
yt-dlp --cookies youtube-cookies.txt --format "best[height<=1080]" --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Test audio extraction
yt-dlp --cookies youtube-cookies.txt --format "bestaudio" --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## 📋 Troubleshooting Tips

### If Downloads Fail:

1. **Update yt-dlp:**
   ```bash
   pip install --upgrade yt-dlp
   ```

2. **Check cookie file:**
   ```bash
   ls -la youtube-cookies.txt
   # Should show file size > 100 bytes
   ```

3. **Test specific formats:**
   ```bash
   # List available formats
   yt-dlp --cookies youtube-cookies.txt --list-formats "https://www.youtube.com/watch?v=VIDEO_ID"
   ```

4. **Update your cookies:**
   - Export fresh cookies from your browser
   - Replace youtube-cookies.txt
   - Restart the bot

### Common Issues & Solutions:

| Issue | Solution |
|-------|----------|
| "Signature extraction failed" | Update yt-dlp: `pip install --upgrade yt-dlp` |
| "Requested format not available" | Bot will auto-fallback to available formats |
| "Sign in to confirm you're not a bot" | Update your cookie file |
| "Video unavailable" | Check if video is region-blocked or private |

## 🚀 Bot Performance Optimization

Your bot is configured to:
- ✅ Use your working cookie file
- ✅ Skip problematic browser extraction
- ✅ Handle format fallbacks gracefully
- ✅ Support multiple quality levels

## 🔄 Keeping Cookies Fresh

To maintain optimal performance:

1. **Update cookies monthly** (or when issues arise)
2. **Export from the same browser** you use for YouTube
3. **Keep cookies file in bot directory**
4. **Restart bot after updating cookies**

## ✅ Your Working Test Command

This proves your setup works:
```bash
yt-dlp --cookies youtube-cookies.txt --format "best[height<=720]" --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
# Returns: Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)
```

Your bot should now handle YouTube downloads reliably! 🎉

## 🎯 Final Configuration Summary

- ✅ **BROWSERS=** (empty - using cookie file instead)
- ✅ **youtube-cookies.txt** in root directory
- ✅ **yt-dlp updated** to latest version
- ✅ **Format fallbacks** handled by bot
- ✅ **Quality selection** working (720p, 480p, etc.)

No browser installation needed - your cookie file method is actually more reliable! 🚀
