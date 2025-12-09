"""
Test suite for enhanced WCAPI /get endpoint with filtering, search, and pagination.

Tests cover:
- Filter parsing and application (basic, lookup operators, negation)
- Search functionality (single/multi-field, fallback)
- Pagination (limit/offset and page-based)
- Ordering (ascending, descending, field mapping)
- Combined queries
- Edge cases and error handling
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal

# Import models being tested
from apps.transactions.models import Proposal, SalesOrder, Invoice
from apps.accounts.models import Contact, Organization
from apps.core.utils.registry import register_model

User = get_user_model()


class WCAPIGetFilteringTests(TestCase):
    """Test filter parsing and application."""
    
    fixtures = []  # Add fixtures if needed
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for filtering tests."""
        # Create test organization
        cls.org = Organization.objects.create(
            name="Test Org",
            short_name="TEST",
        )
        
        # Create test contacts
        cls.contact1 = Contact.objects.create(
            name="John Doe",
            email="john@example.com",
            org=cls.org,
        )
        cls.contact2 = Contact.objects.create(
            name="Jane Smith",
            email="jane@example.com",
            org=cls.org,
        )
        
        # Create test proposals with different statuses
        cls.proposal1 = Proposal.objects.create(
            name="Proposal 1",
            status="draft",
            contact=cls.contact1,
            amount=Decimal("1000.00"),
        )
        cls.proposal2 = Proposal.objects.create(
            name="Proposal 2",
            status="sent",
            contact=cls.contact2,
            amount=Decimal("5000.00"),
        )
        cls.proposal3 = Proposal.objects.create(
            name="Proposal 3",
            status="accepted",
            contact=cls.contact1,
            amount=Decimal("3000.00"),
        )
    
    def setUp(self):
        """Set up test client for each test."""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_login(self.user)
    
    def test_basic_filter_equality(self):
        """Test basic equality filter: ?status=draft"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status': 'draft'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'draft')
    
    def test_multiple_filters(self):
        """Test multiple filters combined: ?status=sent&contact_id=X"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status': 'sent',
            'contact_id': str(self.contact2.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'sent')
    
    def test_gte_filter(self):
        """Test greater-than-or-equal filter: ?amount__gte=2000"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'amount__gte': '2000'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match proposal2 (5000) and proposal3 (3000)
        self.assertEqual(data['count'], 2)
    
    def test_lte_filter(self):
        """Test less-than-or-equal filter: ?amount__lte=2000"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'amount__lte': '2000'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match proposal1 (1000)
        self.assertEqual(data['count'], 1)
    
    def test_range_filter(self):
        """Test range filter: ?amount__gte=2000&amount__lte=4000"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'amount__gte': '2000',
            'amount__lte': '4000'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match proposal3 (3000)
        self.assertEqual(data['count'], 1)
    
    def test_icontains_filter(self):
        """Test case-insensitive contains: ?name__icontains=proposal"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'name__icontains': 'proposal'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match all 3 proposals
        self.assertEqual(data['count'], 3)
    
    def test_ne_filter(self):
        """Test not-equal filter: ?status__ne=draft"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status__ne': 'draft'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match proposal2 and proposal3 (not draft)
        self.assertEqual(data['count'], 2)
        for result in data['results']:
            self.assertNotEqual(result['status'], 'draft')
    
    def test_invalid_filter_field(self):
        """Test that invalid filter fields are safely ignored."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'invalid_field': 'value',
            'status': 'draft'
        })
        
        # Should succeed, invalid field ignored
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['status'], 'draft')
    
    def test_filter_query_echo(self):
        """Test that filters appear in response query echo."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status': 'sent',
            'amount__gte': '3000'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('query', data)
        self.assertIn('filters', data['query'])
        self.assertEqual(data['query']['filters']['status'], 'sent')
        self.assertEqual(data['query']['filters']['amount__gte'], '3000')


class WCAPIGetSearchTests(TestCase):
    """Test full-text search functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for search tests."""
        cls.org = Organization.objects.create(
            name="Search Test Org",
            short_name="STO",
        )
        
        cls.contact1 = Contact.objects.create(
            name="John Customer",
            email="john.customer@example.com",
            org=cls.org,
        )
        cls.contact2 = Contact.objects.create(
            name="Invoice Bob",
            email="invoice.bob@example.com",
            org=cls.org,
        )
        
        cls.proposal1 = Proposal.objects.create(
            name="Customer Proposal for John",
            status="draft",
            contact=cls.contact1,
        )
        cls.proposal2 = Proposal.objects.create(
            name="Invoice Proposal for Bob",
            status="sent",
            contact=cls.contact2,
        )
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.user = User.objects.create_user(username='searchuser', password='testpass')
        self.client.force_login(self.user)
    
    def test_search_basic(self):
        """Test basic search with 'q' parameter."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'q': 'Customer'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data['count'], 0)
        self.assertIn('query', data)
        self.assertEqual(data['query']['search'], 'Customer')
    
    def test_search_alternative_param(self):
        """Test search with alternative 'search' parameter."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'search': 'Invoice'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data['count'], 0)
        self.assertEqual(data['query']['search'], 'Invoice')
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'q': 'customer'  # lowercase
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data['count'], 0)
    
    def test_search_combined_with_filter(self):
        """Test search combined with filters."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'q': 'Proposal',
            'status': 'draft'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(data['count'], 0)
        # All results should be draft status
        for result in data['results']:
            self.assertEqual(result['status'], 'draft')
    
    def test_search_empty_result(self):
        """Test search that returns no results."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'q': 'NonexistentXYZ123'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 0)


class WCAPIGetPaginationTests(TestCase):
    """Test pagination (limit/offset and page-based)."""
    
    @classmethod
    def setUpTestData(cls):
        """Create 15 test proposals for pagination testing."""
        cls.org = Organization.objects.create(
            name="Pagination Test Org",
            short_name="PTO",
        )
        
        cls.contact = Contact.objects.create(
            name="Test Contact",
            email="test@example.com",
            org=cls.org,
        )
        
        cls.proposals = []
        for i in range(15):
            p = Proposal.objects.create(
                name=f"Proposal {i+1:02d}",
                status="draft",
                contact=cls.contact,
                amount=Decimal(str(1000 + i * 100))
            )
            cls.proposals.append(p)
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.user = User.objects.create_user(username='paginguser', password='testpass')
        self.client.force_login(self.user)
    
    def test_default_pagination(self):
        """Test default pagination (limit=500, offset=0)."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 15)  # All 15 items
        self.assertEqual(data['limit'], 500)
        self.assertEqual(data['offset'], 0)
    
    def test_limit_offset_pagination(self):
        """Test limit/offset pagination: ?limit=5&offset=0"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'limit': '5',
            'offset': '0'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['total'], 15)
        self.assertEqual(data['limit'], 5)
        self.assertEqual(data['offset'], 0)
    
    def test_limit_offset_with_offset(self):
        """Test limit/offset with non-zero offset: ?limit=5&offset=10"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'limit': '5',
            'offset': '10'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['offset'], 10)
    
    def test_page_based_pagination(self):
        """Test page-based pagination: ?page=1&page_size=5"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'page': '1',
            'page_size': '5'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['total_pages'], 3)
        self.assertTrue(data['has_next'])
        self.assertFalse(data['has_previous'])
    
    def test_page_based_pagination_page_2(self):
        """Test page-based pagination page 2: ?page=2&page_size=5"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'page': '2',
            'page_size': '5'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['page'], 2)
        self.assertEqual(data['total_pages'], 3)
        self.assertTrue(data['has_next'])
        self.assertTrue(data['has_previous'])
    
    def test_page_based_pagination_last_page(self):
        """Test page-based pagination on last page: ?page=3&page_size=5"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'page': '3',
            'page_size': '5'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['page'], 3)
        self.assertEqual(data['total_pages'], 3)
        self.assertFalse(data['has_next'])
        self.assertTrue(data['has_previous'])
    
    def test_max_limit_enforcement(self):
        """Test that max limit of 1000 is enforced."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'limit': '2000'  # Request more than max
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['limit'], 1000)  # Capped at 1000


class WCAPIGetOrderingTests(TestCase):
    """Test ordering/sorting functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test proposals with different names for ordering."""
        cls.org = Organization.objects.create(
            name="Ordering Test Org",
            short_name="OTO",
        )
        
        cls.contact = Contact.objects.create(
            name="Test Contact",
            email="test@example.com",
            org=cls.org,
        )
        
        # Create proposals with names that will sort differently
        Proposal.objects.create(name="Zebra Proposal", status="draft", contact=cls.contact)
        Proposal.objects.create(name="Alpha Proposal", status="draft", contact=cls.contact)
        Proposal.objects.create(name="Beta Proposal", status="draft", contact=cls.contact)
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.user = User.objects.create_user(username='orderuser', password='testpass')
        self.client.force_login(self.user)
    
    def test_ordering_ascending(self):
        """Test ascending order: ?ordering=name"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'ordering': 'name'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [r['name'] for r in data['results']]
        self.assertEqual(names, sorted(names))  # Verify ascending order
    
    def test_ordering_descending(self):
        """Test descending order: ?ordering=-name"""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'ordering': '-name'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [r['name'] for r in data['results']]
        self.assertEqual(names, sorted(names, reverse=True))  # Verify descending order
    
    def test_ordering_alternative_param(self):
        """Test ordering with alternative 'order_by' parameter."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'order_by': 'name'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [r['name'] for r in data['results']]
        self.assertEqual(names, sorted(names))
    
    def test_invalid_ordering_field(self):
        """Test that invalid ordering field is safely ignored."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'ordering': 'invalid_field_xyz'
        })
        
        # Should succeed, invalid field ignored
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)


class WCAPIGetCombinedTests(TestCase):
    """Test complex combined queries."""
    
    @classmethod
    def setUpTestData(cls):
        """Create diverse test data."""
        cls.org = Organization.objects.create(
            name="Combined Test Org",
            short_name="CTO",
        )
        
        cls.contact1 = Contact.objects.create(
            name="John Premium",
            email="john@premium.com",
            org=cls.org,
        )
        cls.contact2 = Contact.objects.create(
            name="Basic User",
            email="basic@user.com",
            org=cls.org,
        )
        
        # Create proposals with different amounts and statuses
        Proposal.objects.create(
            name="Premium Proposal A",
            status="accepted",
            contact=cls.contact1,
            amount=Decimal("5000.00")
        )
        Proposal.objects.create(
            name="Basic Proposal B",
            status="draft",
            contact=cls.contact2,
            amount=Decimal("500.00")
        )
        Proposal.objects.create(
            name="Premium Proposal C",
            status="sent",
            contact=cls.contact1,
            amount=Decimal("3000.00")
        )
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.user = User.objects.create_user(username='combuser', password='testpass')
        self.client.force_login(self.user)
    
    def test_filter_and_search(self):
        """Test combined filter and search."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status': 'sent',
            'q': 'Premium'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should match Premium Proposal C (sent + contains Premium)
        self.assertGreater(data['count'], 0)
        self.assertEqual(data['query']['search'], 'Premium')
        self.assertEqual(data['query']['filters']['status'], 'sent')
    
    def test_filter_search_pagination_ordering(self):
        """Test all features combined."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'status__ne': 'draft',
            'q': 'Proposal',
            'page': '1',
            'page_size': '10',
            'ordering': '-amount'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertIn('page', data)
        self.assertEqual(data['query']['search'], 'Proposal')
        self.assertIn('status__ne', data['query']['filters'])


class WCAPIGetErrorHandlingTests(TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.user = User.objects.create_user(username='erroruser', password='testpass')
        self.client.force_login(self.user)
    
    def test_missing_model_name(self):
        """Test request without model_name parameter."""
        response = self.client.get('/api/wcapi/get/', {})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_invalid_model_name(self):
        """Test request with invalid model_name."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'nonexistent_model'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('detail', data)
    
    def test_single_record_by_id(self):
        """Test retrieving single record by ID."""
        # First create a proposal
        org = Organization.objects.create(name="Test", short_name="T")
        contact = Contact.objects.create(name="Test", email="test@test.com", org=org)
        proposal = Proposal.objects.create(
            name="Test",
            status="draft",
            contact=contact
        )
        
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'id': str(proposal.id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('record', data)
        self.assertEqual(data['record']['id'], proposal.id)
    
    def test_single_record_invalid_id(self):
        """Test retrieving single record with invalid ID."""
        response = self.client.get('/api/wcapi/get/', {
            'model_name': 'proposal',
            'id': '999999'
        })
        
        # Should return 404 or empty result depending on implementation
        self.assertIn(response.status_code, [200, 404])


if __name__ == '__main__':
    import unittest
    unittest.main()
