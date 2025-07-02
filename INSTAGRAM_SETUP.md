# Instagram Authentication Setup Guide

The bot now uses yt-dlp with cookie authentication instead of an external service. Here's how to set it up:

## Option 1: Cookie File Method (Recommended)

### Step 1: Extract Instagram Cookies

#### Method A: Using Browser Extension
1. **Install Extension**:
   - Chrome/Edge: "Get cookies.txt LOCALLY" or "cookies.txt"
   - Firefox: "Export Cookies"

2. **Extract Cookies**:
   - Go to `https://instagram.com` and **login**
   - Make sure you can see posts and stories
   - Click the extension icon
   - Select "instagram.com" 
   - Download as `instagram-cookies.txt`

#### Method B: Manual Cookie Creation
1. **Login to Instagram** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Application/Storage → Cookies → https://instagram.com**
4. **Create a text file** `instagram-cookies.txt` with this format:
```
# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1735689600	sessionid	YOUR_SESSION_ID_HERE
.instagram.com	TRUE	/	FALSE	1735689600	csrftoken	YOUR_CSRF_TOKEN_HERE
.instagram.com	TRUE	/	TRUE	1735689600	ds_user_id	YOUR_USER_ID_HERE
```

**Important Cookie Fields:**
- `sessionid` - Most important for authentication
- `csrftoken` - Required for API calls
- `ds_user_id` - Your Instagram user ID

### Step 2: Place Cookie File
```bash
# Place the file in your bot directory
cp instagram-cookies.txt /path/to/ytdlbot/
```

## Option 2: Browser Cookie Method

### Step 1: Update .env File
```env
# Add this to your .env file
BROWSERS=chrome
# or
BROWSERS=firefox
# or 
BROWSERS=edge
```

### Step 2: Login to Instagram
- Open your specified browser
- Go to Instagram.com
- Login to your account
- Keep the browser open while using the bot

## Option 3: Multiple Cookie Sources
You can use both methods as fallbacks:

1. Place `instagram-cookies.txt` in bot directory (primary)
2. Set `BROWSERS=chrome,firefox` in .env (fallback)

## Testing Instagram Downloads

### Supported Instagram URLs:
```
https://instagram.com/p/ABC123/              # Posts
https://instagram.com/reel/ABC123/           # Reels  
https://instagram.com/tv/ABC123/             # IGTV
https://instagram.com/stories/highlights/123 # Story Highlights
```

### Test with Public Content First:
1. Find a **public Instagram post**
2. Send the URL to your bot
3. Check if it downloads successfully

## Troubleshooting

### ❌ "Authentication Required"
- **Cause**: No cookies found
- **Solution**: Add `instagram-cookies.txt` or set `BROWSERS` in .env

### ❌ "Content Not Accessible"  
- **Cause**: Private account or deleted content
- **Solution**: Try public content or check if you follow the account

### ❌ "Download Failed"
- **Cause**: Cookies expired or Instagram blocked request
- **Solution**: 
  1. Re-extract fresh cookies
  2. Try different Instagram account
  3. Wait a few minutes (rate limiting)

### ❌ "Missing Dependencies"
- **Cause**: yt-dlp not installed
- **Solution**: `pip install yt-dlp`

## Security Notes

⚠️ **Cookie Security:**
- Keep `instagram-cookies.txt` **private**
- Don't share or commit to version control
- Cookies expire - you may need to refresh them periodically
- Consider using a separate Instagram account for bot operations

## Advanced Configuration

### Custom Cookie Location:
If you want to use a different cookie file location, modify the `cookie_files` list in `src/engine/instagram.py`:

```python
cookie_files = [
    'path/to/your/instagram-cookies.txt',
    'instagram-cookies.txt', 
    'cookies.txt'
]
```

### Browser Priority:
Set multiple browsers as fallbacks:
```env
BROWSERS=chrome,firefox,edge
```

## Verification

To verify your setup is working:

1. **Check cookie file exists and has content**:
   ```bash
   ls -la instagram-cookies.txt
   cat instagram-cookies.txt | head -5
   ```

2. **Test with a public Instagram post**

3. **Check bot logs** for authentication status

4. **Try different content types** (posts, reels, IGTV)

---

✅ **Setup Complete!** Your bot should now be able to download Instagram content with proper authentication.
