# 
# PURPOSE: Script to add file path documentation headers to all WebClerk3 files
# TEAM NOTE: Run this once to add learning documentation to all project files

#!/bin/bash

# Navigate to project root (relative)
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

echo "🔧 Adding file path documentation headers to WebClerk3 project..."

# 1. Update manage_addresses.html
cat > temp_header.txt << 'EOF'
<!--
PURPOSE: Location management interface using Universal API for full CRUD operations
UNIVERSAL API: Uses /wcapi/get/, /wcapi/save/, /wcapi/delete/ endpoints
REPLACES: Old hardcoded address management system with individual views
TEAM NOTE: This template shows the complete pattern for building Universal API interfaces
ARCHITECTURE: Client-side JavaScript communicates with Universal API endpoints
FEATURES:
  - Real-time Add/Edit/Delete via Universal API
  - Form auto-population from Universal API data
  - Contact-specific filtering (?contact_id=X)
  - Responsive table display
  - Error handling and user feedback
TABLES: Works with 'addresses' table via Universal API
JAVASCRIPT: Uses fetch() to communicate with Universal API endpoints
SECURITY: Inherits authentication requirements from Universal API
-->

EOF

# Remove old header and add new one
sed '1,1d' communications/templates/communications/manage_addresses.html > temp_file.txt
cat temp_header.txt temp_file.txt > communications/templates/communications/manage_addresses.html
rm temp_header.txt temp_file.txt

# 2. Update contact.html
cat > temp_header.txt << 'EOF'
<!--
PURPOSE: Main contact detail page with Universal API navigation links
UNIVERSAL API: Links to /wcapi/{table}/manage/ endpoints for related data
REPLACES: Old hardcoded URLs like /manage-addresses/, /manage-phones/
TEAM NOTE: Shows how to convert traditional Django links to Universal API URLs
ARCHITECTURE: Central hub that connects to all related data via Universal API
URL PATTERN: href="/wcapi/{model_name}/manage/?contact_id={{ user.id }}"
NAVIGATION:
  - Locationes: /wcapi/address/manage/?contact_id=X
  - Phones: /wcapi/phone/manage/?contact_id=X
  - Emails: /wcapi/email/manage/?contact_id=X
  - Domains: /wcapi/domain/manage/?contact_id=X
  - Actions: /wcapi/action/manage/?contact_id=X
TABLES: Links to all communication tables via Universal API
CONTEXT: Receives contact data from Django view, passes to Universal API via URLs
-->

EOF

# Update contact.html if it exists
if [ -f "core/templates/core/contact.html" ]; then
    # Find the first non-comment line and insert header before it
    grep -n "{% extends" core/templates/core/contact.html | head -1 | cut -d: -f1 | read line_num
    head -n $((line_num-1)) core/templates/core/contact.html > temp_start.txt 2>/dev/null || touch temp_start.txt
    tail -n +$line_num core/templates/core/contact.html > temp_end.txt
    cat temp_start.txt temp_header.txt temp_end.txt > core/templates/core/contact.html
    rm temp_start.txt temp_end.txt
fi
rm temp_header.txt

# 3. Update generic_views.py (already has header, but ensure it's complete)
cat > temp_header.txt << 'EOF'
# 
# PURPOSE: Universal CRUD views that handle ANY table across ALL apps
# UNIVERSAL API: Core implementation of query, save, get, delete, clone operations
# REPLACES: Individual hardcoded views for each table type (addresses, phones, emails, etc.)
# TEAM NOTE: This is the heart of the Universal API - one set of views handles all tables
# ARCHITECTURE: Recreates 30-year-old 4D database universal table access in modern Django
# TABLES: Works with any model registered in MODEL_REGISTRY (addresses, phones, emails, domains, contacts)
# PATTERN: Uses dynamic model loading and serialization for any Django model
# SECURITY: Requires login authentication for all operations
# FEATURES: 
#   - Dynamic model class loading from any app
#   - Automatic serializer generation
#   - Table registry for configuration
#   - Universal CRUD operations
#   - Background task support (django-q)

EOF

# Update generic_views.py - replace existing header
if [ -f "core/views/generic_views.py" ]; then
    # Find first import line
    grep -n "^import\|^from" core/views/generic_views.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line core/views/generic_views.py > temp_body.txt
    cat temp_header.txt temp_body.txt > core/views/generic_views.py
    rm temp_body.txt
fi
rm temp_header.txt

# 4. Update common/models.py
cat > temp_header.txt << 'EOF'
# 
# PURPOSE: Base model with Universal API metadata system for ALL models
# UNIVERSAL API: Provides foundation metadata structure that makes Universal API work
# REPLACES: Individual metadata handling scattered across different models
# TEAM NOTE: Every model inherits from BaseModel to get Universal API compatibility
# ARCHITECTURE: Implements the 4D-style metadata system (history, health, refs, prefs)
# METADATA STRUCTURE: 
#   - history.dt.created/modified (timestamps)
#   - health.rating (data quality scores)
#   - refs.keywords (searchable keywords)
#   - prefs (user preferences)
# FEATURES:
#   - Automatic timestamp management
#   - Keyword generation from all fields
#   - Undefined field capture
#   - JSON metadata storage
# TABLES: Base class inherited by all models (contacts, addresses, phones, emails, etc.)

EOF

# Update common/models.py
if [ -f "common/models.py" ]; then
    grep -n "^from\|^import" common/models.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line common/models.py > temp_body.txt
    cat temp_header.txt temp_body.txt > common/models.py
    rm temp_body.txt
fi
rm temp_header.txt

# 5. Update core/models/contact_model.py
cat > temp_header.txt << 'EOF'
# 
# PURPOSE: Main Contact model with Universal API support and Django authentication
# UNIVERSAL API: Accessible via 'contacts' table name in Universal API
# REPLACES: Old Contact model without Universal API metadata support
# TEAM NOTE: This is the central user/contact entity that other models reference
# ARCHITECTURE: Combines Django's AbstractBaseUser with Universal API BaseModel
# RELATIONSHIPS: Referenced by addresses, phones, emails, domains, actions
# FEATURES:
#   - Django authentication integration
#   - Universal API metadata
#   - Role-based permissions
#   - UUID generation
#   - Superuser auto-role assignment
# TABLES: Stored in 'contacts' table, accessible via /wcapi/contacts/

EOF

if [ -f "core/models/contact_model.py" ]; then
    grep -n "^from\|^import" core/models/contact_model.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line core/models/contact_model.py > temp_body.txt
    cat temp_header.txt temp_body.txt > core/models/contact_model.py
    rm temp_body.txt
fi
rm temp_header.txt

# 6. Update communications/models.py
cat > temp_header.txt << 'EOF'
# 
# PURPOSE: Location, Phone, Email, Domain models for Universal API communication data
# UNIVERSAL API: Accessible via 'addresses', 'phones', 'emails', 'domains' table names
# REPLACES: Old communication models without Universal API support
# TEAM NOTE: These models show how related data connects to contacts in Universal API
# ARCHITECTURE: All inherit BaseModel and reference Contact via foreign keys
# RELATIONSHIPS: 
#   - Location -> Contact (one contact, many addresses)
#   - Phone -> Contact (one contact, many phones)
#   - Email -> Contact (one contact, many emails)
#   - Domain -> Contact (one contact, many domains)
# FEATURES:
#   - Primary field designation
#   - Type categorization (home, work, mobile, etc.)
#   - Verification status tracking
#   - Universal API metadata inheritance
# TABLES: 'addresses', 'phones', 'emails', 'domains' via Universal API

EOF

if [ -f "communications/models.py" ]; then
    grep -n "^from\|^import" communications/models.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line communications/models.py > temp_body.txt
    cat temp_header.txt temp_body.txt > communications/models.py
    rm temp_body.txt
fi
rm temp_header.txt

# 7. Update core/urls.py
cat > temp_header.txt << 'EOF'
# 
# PURPOSE: URL routing for Universal API endpoints and standard Django views
# UNIVERSAL API: Routes /wcapi/ URLs to universal views that handle any table
# REPLACES: Individual URL patterns for each table management interface
# TEAM NOTE: These patterns enable Universal API to work with any table name dynamically
# ARCHITECTURE: Implements 4D-style universal table access via URLs
# URL PATTERNS:
#   - /wcapi/<model_name>/manage/ -> Universal management interface
#   - /wcapi/query/ -> Universal query endpoint
#   - /wcapi/save/ -> Universal save endpoint
#   - /wcapi/get/ -> Universal get endpoint
#   - /wcapi/delete/ -> Universal delete endpoint
#   - /wcapi/clone/ -> Universal clone endpoint
# SECURITY: All Universal API endpoints require authentication
# TABLES: Works with any model registered in MODEL_REGISTRY

EOF

if [ -f "core/urls.py" ]; then
    grep -n "^from\|^import" core/urls.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line core/urls.py > temp_body.txt
    cat temp_header.txt temp_body.txt > core/urls.py
    rm temp_body.txt
fi
rm temp_header.txt

# 8. Update tests/test_universal_api_simple.py
cat > temp_header.txt << 'EOF'
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

EOF

if [ -f "tests/test_universal_api_simple.py" ]; then
    grep -n "^import\|^from" tests/test_universal_api_simple.py | head -1 | cut -d: -f1 | read import_line
    tail -n +$import_line tests/test_universal_api_simple.py > temp_body.txt
    cat temp_header.txt temp_body.txt > tests/test_universal_api_simple.py
    rm temp_body.txt
fi
rm temp_header.txt

echo "✅ File path documentation headers added successfully!"
echo ""
echo "📋 Updated files:"
echo "  - communications/templates/communications/manage_addresses.html"
echo "  - core/templates/core/contact.html"
echo "  - core/views/generic_views.py"
echo "  - common/models.py"
echo "  - core/models/contact_model.py"
echo "  - communications/models.py"
echo "  - core/urls.py"
echo "  - tests/test_universal_api_simple.py"
echo ""
echo "🎯 Your team can now easily understand each file's purpose and role in the Universal API!"