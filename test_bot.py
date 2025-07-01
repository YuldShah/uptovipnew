#!/usr/bin/env python3
# coding: utf-8

"""
Comprehensive test suite for YouTube Download Bot - Private Edition
Tests all major functionality including access control, admin interface,
statistics, and error handling.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.model import (
    init_user, set_user_access_status, get_user_access_status,
    add_channel, remove_channel, get_required_channels,
    log_download_attempt, log_download_completion, 
    get_download_statistics, get_user_activity_statistics,
    log_user_activity
)
from utils.access_control import get_admin_list, check_user_access
from utils.error_handling import setup_comprehensive_logging, error_reporter

# Test configuration
TEST_USER_IDS = [111111, 222222, 333333]
TEST_CHANNEL_IDS = [-1001234567890, -1001234567891]
TEST_ADMIN_ID = 123456789


class BotTester:
    """Comprehensive bot testing suite"""
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        
        self.test_results[test_name] = {
            'success': success,
            'message': message,
            'timestamp': datetime.now()
        }
        
        if not success:
            self.failed_tests.append(test_name)
    
    def test_database_models(self):
        """Test database models and functions"""
        print("\n🗄️ Testing Database Models...")
        
        try:
            # Test user initialization
            for user_id in TEST_USER_IDS:
                init_user(user_id)
            self.log_test("User Initialization", True, f"Initialized {len(TEST_USER_IDS)} test users")
            
            # Test access status management
            set_user_access_status(TEST_USER_IDS[0], 1)  # Whitelist
            set_user_access_status(TEST_USER_IDS[1], -1)  # Ban
            set_user_access_status(TEST_USER_IDS[2], 0)  # Normal
            
            status_0 = get_user_access_status(TEST_USER_IDS[0])
            status_1 = get_user_access_status(TEST_USER_IDS[1])
            status_2 = get_user_access_status(TEST_USER_IDS[2])
            
            if status_0 == 1 and status_1 == -1 and status_2 == 0:
                self.log_test("Access Status Management", True, "All status changes applied correctly")
            else:
                self.log_test("Access Status Management", False, f"Status mismatch: {status_0}, {status_1}, {status_2}")
            
            # Test channel management
            success_1 = add_channel(TEST_CHANNEL_IDS[0], "Test Channel 1", "https://t.me/testchannel1", TEST_ADMIN_ID)
            success_2 = add_channel(TEST_CHANNEL_IDS[1], "Test Channel 2", "https://t.me/testchannel2", TEST_ADMIN_ID)
            
            if success_1 and success_2:
                self.log_test("Channel Addition", True, "Added 2 test channels")
            else:
                self.log_test("Channel Addition", False, f"Channel addition failed: {success_1}, {success_2}")
            
            channels = get_required_channels()
            if len(channels) >= 2:
                self.log_test("Channel Retrieval", True, f"Retrieved {len(channels)} channels")
            else:
                self.log_test("Channel Retrieval", False, f"Expected at least 2 channels, got {len(channels)}")
            
        except Exception as e:
            self.log_test("Database Models", False, f"Exception: {str(e)}")
    
    def test_access_control(self):
        """Test access control logic"""
        print("\n🔐 Testing Access Control...")
        
        try:
            # Test admin check
            admins = get_admin_list()
            if admins:
                self.log_test("Admin List Retrieval", True, f"Found {len(admins)} admins")
            else:
                self.log_test("Admin List Retrieval", False, "No admins configured")
            
            # Test user access checks
            whitelist_access = check_user_access(TEST_USER_IDS[0], admins)
            ban_access = check_user_access(TEST_USER_IDS[1], admins)
            normal_access = check_user_access(TEST_USER_IDS[2], admins)
            
            if (whitelist_access['has_access'] and 
                not ban_access['has_access'] and 
                not normal_access['has_access']):  # Normal user fails without channel membership
                self.log_test("Access Control Logic", True, "All access checks working correctly")
            else:
                self.log_test("Access Control Logic", False, 
                            f"Access logic error: W={whitelist_access['has_access']}, "
                            f"B={ban_access['has_access']}, N={normal_access['has_access']}")
            
        except Exception as e:
            self.log_test("Access Control", False, f"Exception: {str(e)}")
    
    def test_statistics_system(self):
        """Test statistics tracking and retrieval"""
        print("\n📊 Testing Statistics System...")
        
        try:
            # Test download logging
            download_id = log_download_attempt(TEST_USER_IDS[0], "https://youtube.com/watch?v=test", "youtube", "720p")
            if download_id:
                self.log_test("Download Attempt Logging", True, f"Created download log ID: {download_id}")
                
                # Test download completion
                log_download_completion(
                    download_id=download_id,
                    success=True,
                    file_size=1024*1024*50,  # 50MB
                    duration=30.5,
                    video_quality="720p",
                    audio_quality="128kbps"
                )
                self.log_test("Download Completion Logging", True, "Logged successful download")
            else:
                self.log_test("Download Attempt Logging", False, "Failed to create download log")
            
            # Test activity logging
            log_user_activity(TEST_USER_IDS[0], 'start', {'command': 'start'})
            log_user_activity(TEST_USER_IDS[0], 'download', {'platform': 'youtube'})
            log_user_activity(TEST_USER_IDS[1], 'settings', {'action': 'change_quality'})
            self.log_test("User Activity Logging", True, "Logged various user activities")
            
            # Test statistics retrieval
            download_stats = get_download_statistics(7)
            if download_stats and download_stats.get('total_downloads', 0) > 0:
                self.log_test("Download Statistics Retrieval", True, 
                            f"Retrieved stats: {download_stats['total_downloads']} downloads")
            else:
                self.log_test("Download Statistics Retrieval", False, "No download statistics available")
            
            activity_stats = get_user_activity_statistics(7)
            if activity_stats and activity_stats.get('active_users', 0) > 0:
                self.log_test("Activity Statistics Retrieval", True, 
                            f"Retrieved stats: {activity_stats['active_users']} active users")
            else:
                self.log_test("Activity Statistics Retrieval", False, "No activity statistics available")
            
        except Exception as e:
            self.log_test("Statistics System", False, f"Exception: {str(e)}")
    
    def test_error_handling(self):
        """Test error handling and logging system"""
        print("\n🛡️ Testing Error Handling...")
        
        try:
            # Test error reporter
            error_reporter.report_error("test_error", "This is a test error", TEST_USER_IDS[0])
            error_reporter.report_error("critical_test", "Critical test error", TEST_USER_IDS[1])
            
            error_summary = error_reporter.get_error_summary()
            if error_summary['total_errors'] >= 2:
                self.log_test("Error Reporter", True, f"Tracked {error_summary['total_errors']} errors")
            else:
                self.log_test("Error Reporter", False, f"Expected 2+ errors, got {error_summary['total_errors']}")
            
            # Test logging setup
            setup_comprehensive_logging()
            logging.info("Test log message for verification")
            self.log_test("Logging System Setup", True, "Comprehensive logging initialized")
            
        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {str(e)}")
    
    def test_configuration(self):
        """Test configuration and environment setup"""
        print("\n⚙️ Testing Configuration...")
        
        try:
            # Test environment variables
            required_vars = ['BOT_TOKEN', 'APP_ID', 'APP_HASH', 'ADMIN_IDS']
            missing_vars = []
            
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if not missing_vars:
                self.log_test("Environment Variables", True, "All required variables present")
            else:
                self.log_test("Environment Variables", False, f"Missing: {', '.join(missing_vars)}")
            
            # Test admin configuration
            admin_ids_str = os.getenv('ADMIN_IDS', '')
            if admin_ids_str and ',' in admin_ids_str:
                self.log_test("Admin Configuration", True, f"Multiple admins configured")
            elif admin_ids_str:
                self.log_test("Admin Configuration", True, "Single admin configured")
            else:
                self.log_test("Admin Configuration", False, "No admins configured")
            
        except Exception as e:
            self.log_test("Configuration", False, f"Exception: {str(e)}")
    
    def cleanup_test_data(self):
        """Clean up test data from database"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Remove test channels
            for channel_id in TEST_CHANNEL_IDS:
                remove_channel(channel_id)
            
            # Reset test users to normal status
            for user_id in TEST_USER_IDS:
                set_user_access_status(user_id, 0)
            
            self.log_test("Test Data Cleanup", True, "Cleaned up all test data")
            
        except Exception as e:
            self.log_test("Test Data Cleanup", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Comprehensive Bot Test Suite...")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Run all test categories
        self.test_configuration()
        self.test_database_models()
        self.test_access_control()
        self.test_statistics_system()
        self.test_error_handling()
        
        # Cleanup
        self.cleanup_test_data()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Generate test report
        self.generate_report(duration)
    
    def generate_report(self, duration: float):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 TEST SUITE RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results.values() if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print("\n🚨 FAILED TESTS:")
            for test_name in self.failed_tests:
                result = self.test_results[test_name]
                print(f"   ❌ {test_name}: {result['message']}")
        
        print("\n📝 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {test_name}: {result['message']}")
        
        # Overall status
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Bot is ready for production.")
        elif failed_tests <= 2:
            print("\n⚠️  Minor issues detected. Review failed tests before deployment.")
        else:
            print("\n🚨 Multiple test failures. Bot needs attention before deployment.")
        
        print("=" * 60)


def main():
    """Run the test suite"""
    print("YouTube Download Bot - Private Edition")
    print("Comprehensive Test Suite")
    print("-" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('src/main.py'):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected to find 'src/main.py' in current directory")
        return 1
    
    # Initialize tester
    tester = BotTester()
    
    try:
        # Run all tests
        tester.run_all_tests()
        
        # Return appropriate exit code
        return 0 if not tester.failed_tests else 1
        
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
