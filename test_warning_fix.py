#!/usr/bin/env python3
"""
Test script to verify Django database warning fix.

This script runs a basic Django check to see if the database warning is resolved.
"""
import os
import sys
import subprocess
import warnings

# Add the Django project to Python path
sys.path.insert(0, '/Users/an7or/MyWork/BillJames/webClerk3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3.settings')

def test_django_check():
    """Run Django check and capture output."""
    try:
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Run Django check
            result = subprocess.run([
                sys.executable, 'manage.py', 'check'
            ], capture_output=True, text=True, cwd='/Users/an7or/MyWork/BillJames/webClerk3')
            
            print("=== DJANGO CHECK OUTPUT ===")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            print("Return code:", result.returncode)
            
            print("\n=== WARNINGS CAPTURED ===")
            for warning in w:
                print(f"Warning: {warning.message}")
                print(f"Category: {warning.category}")
                print(f"Filename: {warning.filename}")
                print(f"Line: {warning.lineno}")
                print("---")
            
            # Check for the specific database warning
            db_warnings = [warning for warning in w if 'database' in str(warning.message).lower()]
            
            if db_warnings:
                print(f"\n❌ DATABASE WARNING STILL PRESENT: {len(db_warnings)} warning(s)")
                for warning in db_warnings:
                    print(f"   - {warning.message}")
                return False
            else:
                print("\n✅ NO DATABASE WARNINGS FOUND!")
                return True
                
    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    print("Testing Django database warning fix...")
    success = test_django_check()
    sys.exit(0 if success else 1)