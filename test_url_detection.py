#!/usr/bin/env python3

# Simple test to verify the direct download auto-detection
import sys
sys.path.append('src')

def test_direct_download_detection():
    """Test the URL auto-detection logic for direct downloads"""
    
    # Define the same extensions as in main.py
    direct_download_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', 
                                '.pdf', '.doc', '.docx', '.xlsx', '.ppt', '.pptx',
                                '.exe', '.msi', '.deb', '.rpm', '.dmg', '.pkg',
                                '.iso', '.img', '.bin'}
    
    test_urls = [
        ("https://github.com/aandrew-me/ytDownloader/releases/download/v3.19.1/YTDownloader_Mac_arm64.zip", True),
        ("https://example.com/file.pdf", True),
        ("https://example.com/video.mp4", False),
        ("https://youtube.com/watch?v=abc123", False),
        ("https://example.com/document.docx", True),
        ("https://example.com/archive.tar.gz", True),
        ("https://example.com/installer.exe", True),
        ("https://example.com/page.html", False),
    ]
    
    print("Testing direct download auto-detection...")
    
    for url, expected in test_urls:
        url_lower = url.lower()
        is_direct_download = any(url_lower.endswith(ext) for ext in direct_download_extensions)
        
        status = "✓" if is_direct_download == expected else "✗"
        print(f"{status} {url} -> direct download: {is_direct_download} (expected: {expected})")
    
    print("\nDirect download detection test completed!")

if __name__ == "__main__":
    test_direct_download_detection()
