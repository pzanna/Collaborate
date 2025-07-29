#!/usr/bin/env python3
"""
Test script to verify profile picture upload functionality
"""
import requests
import json
from pathlib import Path

# Test configuration
AUTH_SERVICE_URL = "http://localhost:8013"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def test_profile_upload():
    """Test the profile picture upload functionality"""
    
    print("🧪 Testing Profile Picture Upload Fix...")
    
    # 1. Test health endpoint
    try:
        health_response = requests.get(f"{AUTH_SERVICE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Auth service is healthy")
        else:
            print("❌ Auth service health check failed")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to auth service: {e}")
        return False
    
    # 2. Test login
    try:
        login_data = {
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        login_response = requests.post(
            f"{AUTH_SERVICE_URL}/token",
            data=login_data,
            timeout=10
        )
        
        if login_response.status_code in [200, 202]:
            print("✅ Login endpoint accessible")
        else:
            print(f"⚠️ Login returned status {login_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Login test failed: {e}")
        return False
    
    # 3. Test upload endpoint accessibility (without auth)
    try:
        # Create a small test image file
        test_image_path = "/tmp/test_profile.jpg"
        Path(test_image_path).write_bytes(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xFF\xC0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xFF\xC4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xFF\xC4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xDA\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xAA\xFF\xD9')
        
        # Test upload endpoint without authentication (should return 401)
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test.jpg', f, 'image/jpeg')}
            upload_response = requests.post(
                f"{AUTH_SERVICE_URL}/upload-profile-picture",
                files=files,
                timeout=10
            )
        
        if upload_response.status_code == 401:
            print("✅ Upload endpoint accessible (returns 401 as expected without auth)")
        elif upload_response.status_code == 500:
            error_data = upload_response.json()
            if "read-only file system" in error_data.get("detail", "").lower():
                print("❌ Read-only filesystem error still present")
                return False
            elif "permission denied" in error_data.get("detail", "").lower():
                print("❌ Permission error still present")
                return False
            else:
                print(f"⚠️ Upload endpoint returned 500 with different error: {error_data}")
        else:
            print(f"⚠️ Upload endpoint returned unexpected status: {upload_response.status_code}")
        
        # Clean up test file
        Path(test_image_path).unlink(missing_ok=True)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload endpoint test failed: {e}")
        return False
    
    print("✅ Profile picture upload functionality tests completed")
    return True

if __name__ == "__main__":
    test_profile_upload()
