# path: tests/test_universal_api_simple.py
# 
# PURPOSE: Comprehensive test suite for Universal API functionality
# UNIVERSAL API: Tests all endpoints (query, save, get, delete, clone) with multiple tables
# REPLACES: Individual test files for each table type
# TEAM NOTE: Run these tests to verify Universal API works correctly
# ARCHITECTURE: Tests the Universal API system end-to-end
# TEST COVERAGE:
#   - Endpoint existence (all URLs return non-404)
#   - Authentication requirements
#   - Security (invalid table rejection)
#   - CRUD operations for each table type
#   - Error handling and response formats
# TABLES: Tests contacts, addresses, phones, emails via Universal API
# AUTOMATION: Can be run with `python manage.py test tests.test_universal_api_simple`
# CI/CD: Essential for automated testing of Universal API functionality

