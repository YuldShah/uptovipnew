# Browser Setup for Native Python YTDLBot

## 🌐 Browser Requirements for yt-dlp

When running YTDLBot natively (not in Docker), yt-dlp can use browser cookies to:
- Bypass age restrictions on YouTube
- Access private/unlisted videos
- Reduce rate limiting
- Handle geo-blocked content

## 🚀 Browser Installation Options

### Method 1: Firefox (Recommended)

#### Ubuntu/Debian:
```bash
# Install Firefox
sudo apt update
sudo apt install firefox -y

# Verify installation
firefox --version
```

#### CentOS/RHEL:
```bash
# Install Firefox
sudo dnf install firefox -y

# Or using snap
sudo snap install firefox
```

#### Manual Installation:
```bash
# Download Firefox
wget -O firefox.tar.bz2 "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US"

# Extract
tar -xjf firefox.tar.bz2

# Move to /opt
sudo mv firefox /opt/

# Create symlink
sudo ln -sf /opt/firefox/firefox /usr/local/bin/firefox

# Verify
firefox --version
```

### Method 2: Chrome/Chromium

#### Install Chrome:
```bash
# Download Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Install
sudo apt update
sudo apt install google-chrome-stable -y

# Verify
google-chrome --version
```

#### Install Chromium:
```bash
# Ubuntu/Debian
sudo apt install chromium-browser -y

# CentOS/RHEL
sudo dnf install chromium -y

# Verify
chromium --version
```

### Method 3: Headless Setup (Server without GUI)

For VPS without desktop environment:

```bash
# Install Firefox with dependencies
sudo apt update
sudo apt install firefox xvfb -y

# Install Chrome headless
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# Test headless Firefox
xvfb-run firefox --headless --version

# Test headless Chrome
google-chrome --headless --version
```

## ⚙️ YTDLBot Configuration

### Update Your .env File

```bash
# Set browser preference
BROWSERS=firefox

# Alternative options:
# BROWSERS=chrome
# BROWSERS=chromium
# BROWSERS=safari  # macOS only
# BROWSERS=edge    # Windows/limited Linux
```

### Multiple Browser Support

```bash
# Comma-separated list (fallback order)
BROWSERS=firefox,chrome,chromium
```

## 🔧 Browser-Specific Setup

### Firefox Profile Setup (Optional)

Create a dedicated Firefox profile for the bot:

```bash
# Create bot profile
firefox -CreateProfile "ytdlbot /home/$(whoami)/.mozilla/firefox/ytdlbot"

# Start Firefox with profile to set it up
firefox -P ytdlbot

# Then close Firefox and update your bot config
```

### Chrome Profile Setup (Optional)

```bash
# Create Chrome profile directory
mkdir -p ~/.config/google-chrome/ytdlbot

# Use in bot configuration (advanced)
```

## 🧪 Test Browser Integration

### Test yt-dlp with Browser

```bash
# Test with Firefox
yt-dlp --cookies-from-browser firefox "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Test with Chrome
yt-dlp --cookies-from-browser chrome "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Test extraction only (no download)
yt-dlp --cookies-from-browser firefox --get-title "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Test in Your Bot Environment

Create a test script:

```python
# test_browser.py
import os
import yt_dlp

def test_browser_integration():
    browsers = os.getenv("BROWSERS", "firefox").split(",")
    
    for browser in browsers:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            # Add browser cookies if available
            if browser.strip():
                ydl_opts['cookiesfrom'] = browser.strip()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)
                print(f"✅ {browser}: {info.get('title', 'Success')}")
                return True
                
        except Exception as e:
            print(f"❌ {browser}: {str(e)}")
            continue
    
    print("⚠️  No browsers working - using without cookies")
    return False

if __name__ == "__main__":
    test_browser_integration()
```

Run the test:
```bash
python test_browser.py
```

## 🚨 Troubleshooting

### Common Issues:

1. **Browser Not Found**
   ```bash
   # Check if browser is in PATH
   which firefox
   which google-chrome
   which chromium
   
   # If not found, create symlinks or install properly
   ```

2. **Permission Issues**
   ```bash
   # Fix browser permissions
   sudo chown -R $(whoami):$(whoami) ~/.mozilla
   sudo chown -R $(whoami):$(whoami) ~/.config/google-chrome
   ```

3. **Headless Environment Issues**
   ```bash
   # Install X11 dependencies
   sudo apt install xorg xvfb -y
   
   # Test with virtual display
   export DISPLAY=:99
   Xvfb :99 -screen 0 1024x768x24 &
   firefox --version
   ```

4. **Cookie Access Issues**
   ```bash
   # Make sure browser has been run at least once
   firefox --headless --safe-mode &
   sleep 5
   pkill firefox
   ```

## 📋 Recommended Setup for VPS

### Option A: Minimal Setup (Firefox only)
```bash
# 1. Install Firefox
sudo apt update && sudo apt install firefox xvfb -y

# 2. Test headless
xvfb-run firefox --headless --version

# 3. Update .env
echo "BROWSERS=firefox" >> .env

# 4. Initialize browser (run once)
xvfb-run firefox --headless --safe-mode &
sleep 10
pkill firefox
```

### Option B: Full Setup (Multiple browsers)
```bash
# 1. Install both browsers
sudo apt update
sudo apt install firefox chromium-browser xvfb -y

# 2. Test both
xvfb-run firefox --headless --version
chromium --headless --version

# 3. Update .env with fallbacks
echo "BROWSERS=firefox,chromium" >> .env
```

### Option C: No Browser (Fallback)
```bash
# Just comment out or leave empty
# BROWSERS=

# Bot will work without browser cookies
# (may have more limitations on some videos)
```

## 🎯 Production Recommendations

1. **Use Firefox**: Most reliable with yt-dlp
2. **Headless Mode**: Essential for VPS without GUI
3. **Virtual Display**: Use xvfb for GUI-less servers
4. **Multiple Browsers**: Set fallbacks in case one fails
5. **Test Regularly**: Browser updates can break cookie extraction

## 🔄 Environment Variables Summary

```bash
# Your final .env should include:
BROWSERS=firefox

# Or for multiple browsers:
BROWSERS=firefox,chromium,chrome

# Leave empty to disable browser cookies:
# BROWSERS=
```

Your bot will now use browser cookies for better YouTube access! 🎉

## Performance Impact

- ✅ **With Browsers**: Better success rate, fewer rate limits
- ⚠️ **Without Browsers**: Still works, but may hit more restrictions
- 🚀 **Recommended**: Use Firefox with xvfb for best results

The bot will automatically handle browser cookie extraction when configured properly.
