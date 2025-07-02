#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from pathlib import Path
import tempfile
from engine.direct import DirectDownload

# Simple test to verify file type detection
def test_file_type_detection():
    """Test the auto file type detection logic"""
    
    # Create a temporary test downloader instance
    class MockClient:
        pass
    
    class MockMessage:
        def __init__(self):
            self.chat = MockChat()
            self.id = 1
        async def edit_text(self, text):
            print(f"Bot message: {text}")
    
    class MockChat:
        def __init__(self):
            self.id = 123
            self.type = "private"
    
    # Test different file types
    test_cases = [
        ("test.zip", "document"),
        ("test.mp4", "video"), 
        ("test.jpg", "photo"),
        ("test.mp3", "audio"),
        ("test.pdf", "document"),
        ("test.rar", "document"),
        ("test.tar.gz", "document"),
        ("unknown_file", "document")  # fallback case
    ]
    
    print("Testing file type detection...")
    
    for filename, expected_format in test_cases:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=filename, delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_path = temp_file.name
        
        try:
            # Create downloader instance
            downloader = DirectDownload(MockClient(), MockMessage(), "http://example.com")
            
            # Test the auto detection
            downloader._auto_detect_format(temp_path)
            
            print(f"✓ {filename} -> detected format: {downloader._format} (expected: {expected_format})")
            
            if downloader._format != expected_format:
                print(f"  ⚠️  Expected {expected_format}, got {downloader._format}")
            
        finally:
            # Clean up
            os.unlink(temp_path)
    
    print("\nFile type detection test completed!")

if __name__ == "__main__":
    test_file_type_detection()
