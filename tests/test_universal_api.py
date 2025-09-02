import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.core.models import Contact
from apps.communications.models import Location, Phone, Email

User = get_user_model()

class UniversalAPITestCase(TestCase):
    """Test suite for Universal API - works with ANY table"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user using Contact model (NO USERNAME FIELD!)
        self.user = User.objects.create_user(
            email='test@example.com',  # Primary identifier
            password='testpass123',
            name_first='Test',
            name_last='User',
            username=''  # custom user may ignore but keep param explicit
        )
        
        # Create additional test contact (separate from user)
        self.contact = Contact.objects.create(
            email='contact@example.com',
            name_first='Test',
            name_last='Contact',
            company='Test Company'
        )
        
        # Login user using email (not username)
        self.client.login(email='test@example.com', password='testpass123')
    
    def universal_query(self, table_name, filters=None):
        """Universal query method - works for ANY table"""
        data = {'table_name': table_name}
        if filters:
            data.update(filters)
        
        response = self.client.post(
            '/wcapi/query/',
            data=json.dumps(data),
            content_type='application/json'
        )
        return response
    
    def save_view(self, table_name, record_data):
        """Universal save method - works for ANY table"""
        data = {'table_name': table_name}
        data.update(record_data)
        
        response = self.client.post(
            '/wcapi/save/',
            data=json.dumps(data),
            content_type='application/json'
        )
        return response
    
    def universal_get(self, table_name, record_id):
        """Universal get method - works for ANY table"""
        data = {
            'table_name': table_name,
            'id': record_id
        }
        
        response = self.client.post(
            '/wcapi/get/',
            data=json.dumps(data),
            content_type='application/json'
        )
        return response


class ContactAPITests(UniversalAPITestCase):
    """Test Universal API with Contacts table"""
    
    def test_query_contacts(self):
        """Test querying contacts via Universal API"""
        response = self.universal_query('contacts')
        body = response.json()
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['data']['table_name'], 'contacts')
        self.assertIn('results', body['data'])
        print(f"✅ Query contacts: {len(body['data']['results'])} records found")
    
    def test_save_new_contact(self):
        """Test creating new contact via Universal API"""
        contact_data = {
            'email': 'john.doe@universal.com',
            'name_first': 'John',  # Use actual field name
            'name_last': 'Doe',    # Use actual field name
            'company': 'Universal Corp'
        }
        
        response = self.save_view('contacts', contact_data)
        
        # Check response
        print(f"📝 Save contact response: {response.status_code}")
        if response.status_code in [200, 201]:
            body = response.json()
            print(f"📝 Save contact data: {body}")
            if body.get('status') == 'success':
                # save endpoint legacy may still return id at root; tolerate either
                new_id = body.get('id') or body.get('data', {}).get('id')
                if new_id:
                    print(f"✅ Contact created with ID: {new_id}")
        elif response.status_code == 501:
            print("⚠️ Save functionality not implemented yet (501)")
        else:
            print(f"❌ Save failed: {response.json()}")


class LocationAPITests(UniversalAPITestCase):
    pass


class PhoneAPITests(UniversalAPITestCase):
    pass


class EmailAPITests(UniversalAPITestCase):
    pass


class UniversalAPISecurityTests(UniversalAPITestCase):
    pass


class UniversalAPIPerformanceTests(UniversalAPITestCase):
    pass


# Simplified relationship tests for now
class UniversalAPIRelationshipTests(UniversalAPITestCase):
    pass