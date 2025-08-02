#!/usr/bin/env python3
"""
Universal API Test Runner
Tests the Universal API against all registered tables
"""

import os
import sys
import django
from django.test import TestCase
from django.test.utils import get_runner
from django.conf import settings

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
django.setup()

def run_universal_api_tests():
    """Run all Universal API tests"""
    print("🚀 Running Universal API Tests...")
    print("=" * 50)
    
    # Get Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run tests
    failures = test_runner.run_tests([
        'tests.test_universal_api.ContactAPITests',
        'tests.test_universal_api.AddressAPITests', 
        'tests.test_universal_api.PhoneAPITests',
        'tests.test_universal_api.EmailAPITests',
        'tests.test_universal_api.UniversalAPIRelationshipTests',
        'tests.test_universal_api.UniversalAPISecurityTests',
        'tests.test_universal_api.UniversalAPIPerformanceTests',
    ])
    
    if failures:
        print(f"❌ {failures} test(s) failed")
        return False
    else:
        print("✅ All Universal API tests passed!")
        return True

if __name__ == '__main__':
    success = run_universal_api_tests()
    sys.exit(0 if success else 1)