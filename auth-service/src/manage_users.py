#!/usr/bin/env python3
"""
User Management Script for Eunice Authentication Service

This script provides utilities for managing user accounts in the PostgreSQL auth database.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import subprocess

def get_db_connection_info():
    """Get database connection info from environment or defaults."""
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@eunice-postgres:5432/eunice")
    return database_url

def execute_sql(sql_query):
    """Execute SQL query using docker exec and psql."""
    try:
        # Use docker exec to run psql command
        result = subprocess.run([
            "docker", "exec", "eunice-postgres", 
            "psql", "-U", "postgres", "-d", "eunice", 
            "-c", sql_query
        ], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing SQL: {e}")
        print(f"Error output: {e.stderr}")
        return None

def list_users():
    """List all users in the database."""
    sql_query = """SELECT id, email, first_name, last_name, is_disabled, created_at 
                  FROM "user" 
                  ORDER BY created_at DESC;"""
    
    result = execute_sql(sql_query)
    if not result:
        print("❌ Failed to retrieve users.")
        return
    
    lines = result.strip().split('\n')
    if len(lines) <= 2:  # Just headers
        print("No users found.")
        return
    
    print("\n📋 Current Users:")
    print("-" * 80)
    print(f"{'ID':<3} {'Email':<30} {'First Name':<15} {'Last Name':<15} {'Status':<8} {'Created'}")
    print("-" * 80)
    
    # Skip header lines (first 2 lines)
    for line in lines[2:]:
        if line.strip() and not line.startswith('-'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                user_id = parts[0]
                email = parts[1]
                first_name = parts[2] if parts[2] else ''
                last_name = parts[3] if parts[3] else ''
                is_disabled = parts[4]
                created_at = parts[5][:19] if parts[5] else 'Unknown'
                status = "Disabled" if is_disabled == 't' else "Active"
                print(f"{user_id:<3} {email:<30} {first_name:<15} {last_name:<15} {status:<8} {created_at}")

def delete_user_by_id(user_id):
    """Delete a user by ID."""
    # First check if user exists
    check_sql = f"SELECT email, first_name, last_name FROM \"user\" WHERE id = {user_id};"
    result = execute_sql(check_sql)
    
    if not result or len(result.strip().split('\n')) <= 2:
        print(f"❌ User with ID {user_id} not found.")
        return False
    
    # Get user info from result
    lines = result.strip().split('\n')
    if len(lines) > 2:
        user_line = lines[2].strip()
        if user_line and not user_line.startswith('-'):
            parts = [p.strip() for p in user_line.split('|')]
            if len(parts) >= 3:
                email = parts[0]
                first_name = parts[1]
                last_name = parts[2]
                
                # Delete the user
                delete_sql = f"DELETE FROM \"user\" WHERE id = {user_id};"
                delete_result = execute_sql(delete_sql)
                
                if delete_result is not None:
                    print(f"✅ Deleted user: {first_name} {last_name} ({email})")
                    return True
                else:
                    print(f"❌ Failed to delete user with ID {user_id}")
                    return False
    
    print(f"❌ Could not parse user data for ID {user_id}")
    return False

def delete_test_users():
    """Delete all test users (with @example.com email)."""
    # Get test users first
    check_sql = "SELECT id, email, first_name, last_name FROM \"user\" WHERE email LIKE '%@example.com';"
    result = execute_sql(check_sql)
    
    if not result:
        print("❌ Failed to check for test users.")
        return
    
    lines = result.strip().split('\n')
    if len(lines) <= 2:
        print("No test users found.")
        return
    
    test_users = []
    for line in lines[2:]:
        if line.strip() and not line.startswith('-'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                test_users.append((parts[0], parts[1], parts[2], parts[3]))
    
    if not test_users:
        print("No test users found.")
        return
    
    print(f"Found {len(test_users)} test user(s):")
    for user in test_users:
        print(f"  - {user[2]} {user[3]} ({user[1]})")
    
    confirm = input("\n⚠️  Delete all test users? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Delete test users
    delete_sql = "DELETE FROM \"user\" WHERE email LIKE '%@example.com';"
    delete_result = execute_sql(delete_sql)
    
    if delete_result is not None:
        print(f"✅ Deleted {len(test_users)} test user(s).")
    else:
        print("❌ Failed to delete test users.")

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
