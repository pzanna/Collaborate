#!/usr/bin/env python3
"""
Test script for Phase 5 Frontend Integration
Tests the new research components and API integration
"""

import sys
import os
from pathlib import Path

def test_component_files():
    """Test that all research components are created"""
    frontend_components = Path("frontend/src/components/chat/research")
    
    expected_files = [
        "ResearchModeIndicator.tsx",
        "ResearchProgress.tsx",
        "ResearchResults.tsx",
        "ResearchTaskList.tsx",
        "ResearchInput.tsx",
    ]
    
    print("🧪 Testing Research Components...")
    
    if not frontend_components.exists():
        print("❌ Research components directory not found")
        return False
    
    missing_files = []
    for file in expected_files:
        if not (frontend_components / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing component files: {missing_files}")
        return False
    
    print("✅ All research components created")
    return True

def test_service_files():
    """Test that research services are created"""
    frontend_services = Path("frontend/src/services")
    
    expected_files = [
        "ResearchWebSocket.ts",
    ]
    
    print("🧪 Testing Research Services...")
    
    missing_files = []
    for file in expected_files:
        if not (frontend_services / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing service files: {missing_files}")
        return False
    
    print("✅ All research services created")
    return True

def test_api_updates():
    """Test that API service is updated with research endpoints"""
    api_file = Path("frontend/src/services/api.ts")
    
    print("🧪 Testing API Service Updates...")
    
    if not api_file.exists():
        print("❌ API service file not found")
        return False
    
    try:
        with open(api_file, 'r') as f:
            content = f.read()
        
        required_interfaces = [
            "ResearchRequest",
            "ResearchTaskResponse",
            "ResearchProgressUpdate",
        ]
        
        required_methods = [
            "startResearchTask",
            "getResearchTask",
            "cancelResearchTask",
            "getHealth",
        ]
        
        missing_items = []
        
        for interface in required_interfaces:
            if interface not in content:
                missing_items.append(f"interface {interface}")
        
        for method in required_methods:
            if method not in content:
                missing_items.append(f"method {method}")
        
        if missing_items:
            print(f"❌ Missing API items: {missing_items}")
            return False
        
        print("✅ API service updated with research endpoints")
        return True
        
    except Exception as e:
        print(f"❌ Error reading API service: {e}")
        return False

def test_chat_slice_updates():
    """Test that chat slice is updated with research state"""
    chat_slice_file = Path("frontend/src/store/slices/chatSlice.ts")
    
    print("🧪 Testing Chat Slice Updates...")
    
    if not chat_slice_file.exists():
        print("❌ Chat slice file not found")
        return False
    
    try:
        with open(chat_slice_file, 'r') as f:
            content = f.read()
        
        required_interfaces = [
            "ResearchTask",
        ]
        
        required_state_props = [
            "researchTasks",
            "activeResearchTask",
            "isResearchMode",
            "researchConnectionStatus",
        ]
        
        required_actions = [
            "setResearchConnectionStatus",
            "setResearchMode",
            "setActiveResearchTask",
            "addResearchTask",
            "updateResearchTask",
            "removeResearchTask",
            "handleResearchProgress",
        ]
        
        required_thunks = [
            "startResearchTask",
            "cancelResearchTask",
        ]
        
        missing_items = []
        
        for interface in required_interfaces:
            if interface not in content:
                missing_items.append(f"interface {interface}")
        
        for prop in required_state_props:
            if prop not in content:
                missing_items.append(f"state prop {prop}")
        
        for action in required_actions:
            if action not in content:
                missing_items.append(f"action {action}")
        
        for thunk in required_thunks:
            if thunk not in content:
                missing_items.append(f"thunk {thunk}")
        
        if missing_items:
            print(f"❌ Missing chat slice items: {missing_items}")
            return False
        
        print("✅ Chat slice updated with research state and actions")
        return True
        
    except Exception as e:
        print(f"❌ Error reading chat slice: {e}")
        return False

def test_conversation_view_updates():
    """Test that ConversationView is updated with research components"""
    conversation_view_file = Path("frontend/src/components/chat/ConversationView.tsx")
    
    print("🧪 Testing ConversationView Updates...")
    
    if not conversation_view_file.exists():
        print("❌ ConversationView file not found")
        return False
    
    try:
        with open(conversation_view_file, 'r') as f:
            content = f.read()
        
        required_imports = [
            "ResearchWebSocket",
            "ResearchModeIndicator",
            "ResearchProgress",
            "ResearchTaskList",
            "ResearchInput",
        ]
        
        required_elements = [
            "ResearchModeIndicator",
            "ResearchProgress",
            "ResearchTaskList",
            "ResearchInput",
        ]
        
        missing_items = []
        
        for import_item in required_imports:
            if import_item not in content:
                missing_items.append(f"import {import_item}")
        
        for element in required_elements:
            if f"<{element}" not in content:
                missing_items.append(f"component {element}")
        
        if missing_items:
            print(f"❌ Missing ConversationView items: {missing_items}")
            return False
        
        print("✅ ConversationView updated with research components")
        return True
        
    except Exception as e:
        print(f"❌ Error reading ConversationView: {e}")
        return False

def test_typescript_compilation():
    """Test that TypeScript compiles without errors"""
    print("🧪 Testing TypeScript Compilation...")
    
    # Check if we're in the right directory
    if not Path("frontend/package.json").exists():
        print("❌ Not in correct directory or frontend not found")
        return False
    
    try:
        # Run TypeScript compilation check
        result = os.system("cd frontend && npx tsc --noEmit --skipLibCheck")
        
        if result == 0:
            print("✅ TypeScript compilation successful")
            return True
        else:
            print("❌ TypeScript compilation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error running TypeScript check: {e}")
        return False

def main():
    """Run all Phase 5 tests"""
    print("🧪 Running Phase 5 Frontend Integration Tests")
    print("=" * 50)
    
    os.chdir('/Users/paulzanna/Github/Collaborate')
    
    tests = [
        ("Component Files", test_component_files),
        ("Service Files", test_service_files),
        ("API Updates", test_api_updates),
        ("Chat Slice Updates", test_chat_slice_updates),
        ("ConversationView Updates", test_conversation_view_updates),
        # ("TypeScript Compilation", test_typescript_compilation),  # Optional, may fail if deps not installed
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📝 Running {test_name}...")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 5 frontend integration tests passed!")
        return True
    else:
        print("💥 Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
