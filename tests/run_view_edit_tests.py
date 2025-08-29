#!/usr/bin/env python3
"""Runner for view/edit permission tests.

Usage:
  python tests/run_view_edit_tests.py
"""
import os
import sys
import django
import pytest
from django.conf import settings

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')

def run_view_edit_tests(verbosity=1):
    django.setup()
    print("🚦 Running view/edit permission tests via pytest...")
    args = ['tests/test_view_edit_permissions.py']
    if verbosity == 1:
        args.insert(0, '-q')
    exit_code = pytest.main(args)
    if exit_code == 0:
        print("✅ View/Edit permission tests passed")
        return True
    print("❌ View/Edit permission tests failed")
    return False

if __name__ == '__main__':
    success = run_view_edit_tests()
    sys.exit(0 if success else 1)
