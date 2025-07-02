#!/usr/bin/env python3
"""
Test script to verify download logging functionality
"""

import sys
import os
sys.path.append('src')

from database.model import log_download_attempt, log_download_completion, get_download_statistics

def test_download_logging():
    print("Testing download logging functionality...")
    
    # Test logging a download attempt
    print("\n1. Testing log_download_attempt...")
    download_id = log_download_attempt(12345, "https://test.com/video.mp4", "youtube")
    print(f"   Download ID returned: {download_id}")
    print(f"   Type of download_id: {type(download_id)}")
    
    # Test logging completion
    print("\n2. Testing log_download_completion...")
    if download_id and download_id != -1:
        success = log_download_completion(download_id, True, file_size=1024000)
        print(f"   Completion logged successfully: {success}")
    else:
        print("   Cannot test completion - invalid download_id")
    
    # Test getting statistics
    print("\n3. Testing get_download_statistics...")
    try:
        stats = get_download_statistics()
        print(f"   Statistics retrieved: {stats}")
    except Exception as e:
        print(f"   Error getting statistics: {e}")

if __name__ == "__main__":
    test_download_logging()
