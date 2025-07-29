#!/usr/bin/env python3
"""
User Management Script for Eunice Authentication Service

This script provides utilities for managing user accounts in the auth database.
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

def connect_db():
    """Connect to the auth database."""
    db_path = Path(__file__).parent / "auth.db"
    return sqlite3.connect(db_path)

def list_users():
    """List all users in the database."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, full_name, is_disabled, created_at 
        FROM user 
        ORDER BY created_at DESC
    """)
    
    users = cursor.fetchall()
    
    if not users:
        print("No users found.")
        return
    
    print("\n📋 Current Users:")
    print("-" * 80)
    print(f"{'ID':<3} {'Username':<25} {'Email':<30} {'Name':<15} {'Status':<8} {'Created'}")
    print("-" * 80)
    
    for user in users:
        status = "Disabled" if user[4] else "Active"
        created = user[5][:19] if user[5] else "Unknown"
        print(f"{user[0]:<3} {user[1]:<25} {user[2]:<30} {user[3] or '':<15} {status:<8} {created}")
    
    conn.close()

def delete_user_by_id(user_id):
    """Delete a user by ID."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # First check if user exists
    cursor.execute("SELECT username, email FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ User with ID {user_id} not found.")
        conn.close()
        return False
    
    # Delete the user
    cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
    conn.commit()
    
    print(f"✅ Deleted user: {user[0]} ({user[1]})")
    conn.close()
    return True

def delete_test_users():
    """Delete all test users (with @example.com email)."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get test users first
    cursor.execute("SELECT id, username, email FROM user WHERE email LIKE '%@example.com'")
    test_users = cursor.fetchall()
    
    if not test_users:
        print("No test users found.")
        conn.close()
        return
    
    print(f"Found {len(test_users)} test user(s):")
    for user in test_users:
        print(f"  - {user[1]} ({user[2]})")
    
    confirm = input("\n⚠️  Delete all test users? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        conn.close()
        return
    
    # Delete test users
    cursor.execute("DELETE FROM user WHERE email LIKE '%@example.com'")
    deleted_count = cursor.rowcount
    conn.commit()
    
    print(f"✅ Deleted {deleted_count} test user(s).")
    conn.close()

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("""
🔧 Eunice User Management Script

Usage:
  python manage_users.py list              - List all users
  python manage_users.py delete <user_id>  - Delete user by ID  
  python manage_users.py delete-tests      - Delete all test users (@example.com)

Examples:
  python manage_users.py list
  python manage_users.py delete 5
  python manage_users.py delete-tests
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_users()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please provide a user ID to delete.")
            print("Usage: python manage_users.py delete <user_id>")
            return
        
        try:
            user_id = int(sys.argv[2])
            delete_user_by_id(user_id)
        except ValueError:
            print("❌ User ID must be a number.")
    
    elif command == "delete-tests":
        delete_test_users()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: list, delete, delete-tests")

if __name__ == "__main__":
    main()
