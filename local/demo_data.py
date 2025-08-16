from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import Contact, Action, Phone, Location, Domain, Email
import json
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate database with test data for WebClerk 3.0 Universal API'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Populating WebClerk 3.0 test data...'))
        
        # Clear existing data (optional)
        Contact.objects.all().delete()
        Action.objects.all().delete()
        Phone.objects.all().delete()
        Location.objects.all().delete()
        Domain.objects.all().delete()
        Email.objects.all().delete()
        
        # Create 4 contacts
        contacts = []
        contact_data = [
            {
                'email': 'john.smith@techcorp.com',
                'name_first': 'John',
                'name_last': 'Smith',
                'company': 'TechCorp Industries',
                'title': 'Senior Software Engineer',
                'role': 'admin',
                'department': 'Engineering'
            },
            {
                'email': 'sarah.johnson@innovate.biz',
                'name_first': 'Sarah',
                'name_last': 'Johnson',
                'company': 'Innovate Solutions',
                'title': 'Product Manager',
                'role': 'manager',
                'department': 'Product'
            },
            {
                'email': 'mike.wilson@startup.io',
                'name_first': 'Mike',
                'name_last': 'Wilson',
                'company': 'StartupHub',
                'title': 'Marketing Director',
                'role': 'user',
                'department': 'Marketing'
            },
            {
                'email': 'lisa.brown@consulting.pro',
                'name_first': 'Lisa',
                'name_last': 'Brown',
                'company': 'Professional Consulting',
                'title': 'Senior Consultant',
                'role': 'user',
                'department': 'Consulting'
            }
        ]
        
        for data in contact_data:
            contact = Contact.objects.create(
                email=data['email'],
                name_first=data['name_first'],
                name_last=data['name_last'],
                company=data['company'],
                title=data['title'],
                role=data['role'],
                department=data['department'],
                password=make_password('testpass123'),
                is_active=True
            )
            contacts.append(contact)
            self.stdout.write(f'✅ Created contact: {contact.email}')
        
        # Create Actions for each contact
        action_types = ['call', 'email', 'meeting', 'follow_up']
        for i, contact in enumerate(contacts):
            for j, action_type in enumerate(action_types):
                action = Action.objects.create(
                    contact=contact,
                    action_type=action_type,
                    description=f'{action_type.title()} with {contact.name_first} regarding project discussion',
                    notes=f'Important {action_type} scheduled for follow-up on current initiatives.',
                    status='completed' if j % 2 == 0 else 'pending',
                    priority='high' if j == 0 else 'medium',
                    due_date=datetime.now() + timedelta(days=j+1),
                    refs={'links': {'contacts': [contact.contact_id]}}
                )
                self.stdout.write(f'✅ Created action: {action.action_type} for {contact.email}')
        
        # Create Phones for each contact
        phone_types = ['work', 'mobile', 'home', 'fax']
        phone_numbers = [
            ['555-0101', '555-0102', '555-0103', '555-0104'],
            ['555-0201', '555-0202', '555-0203', '555-0204'],
            ['555-0301', '555-0302', '555-0303', '555-0304'],
            ['555-0401', '555-0402', '555-0403', '555-0404']
        ]
        
        for i, contact in enumerate(contacts):
            for j, phone_type in enumerate(phone_types):
                phone = Phone.objects.create(
                    contact=contact,
                    phone_number=phone_numbers[i][j],
                    phone_type=phone_type,
                    extension='1001' if phone_type == 'work' else '',
                    is_primary=j == 0,
                    refs={'links': {'contacts': [contact.contact_id]}}
                )
                self.stdout.write(f'✅ Created phone: {phone.phone_number} for {contact.email}')
        
        # Create Locationes for each contact
        address_types = ['work', 'home', 'billing', 'shipping']
        cities = ['San Francisco', 'New York', 'Austin', 'Seattle']
        
        for i, contact in enumerate(contacts):
            for j, addr_type in enumerate(address_types):
                address = Location.objects.create(
                    contact=contact,
                    address_type=addr_type,
                    street=f'{(i+1)*100 + j*10} Main Street',
                    city=cities[i],
                    state='CA' if cities[i] == 'San Francisco' else 'NY' if cities[i] == 'New York' else 'TX' if cities[i] == 'Austin' else 'WA',
                    postal_code=f'{90000 + i*1000 + j*100}',
                    country='United States',
                    is_primary=j == 0,
                    refs={'links': {'contacts': [contact.contact_id]}}
                )
                self.stdout.write(f'✅ Created address: {address.city} for {contact.email}')
        
        # Create Domains for each contact
        domain_names = [
            ['techcorp.com', 'techcorp.net', 'techcorp.org', 'techcorp.io'],
            ['innovate.biz', 'innovate.com', 'innovate.net', 'innovate.co'],
            ['startup.io', 'startup.com', 'startup.co', 'startup.net'],
            ['consulting.pro', 'consulting.com', 'consulting.biz', 'consulting.org']
        ]
        
        for i, contact in enumerate(contacts):
            for j, domain_name in enumerate(domain_names[i]):
                domain = Domain.objects.create(
                    contact=contact,
                    domain_name=domain_name,
                    registrar='GoDaddy' if j % 2 == 0 else 'Namecheap',
                    expiry_date=datetime.now() + timedelta(days=365 + j*30),
                    is_active=True,
                    refs={'links': {'contacts': [contact.contact_id]}}
                )
                self.stdout.write(f'✅ Created domain: {domain.domain_name} for {contact.email}')
        
        # Create additional Emails for each contact
        email_types = ['work', 'personal', 'billing', 'support']
        email_prefixes = ['primary', 'alt', 'billing', 'support']
        
        for i, contact in enumerate(contacts):
            base_email = contact.email.split('@')[0]
            domain = contact.email.split('@')[1]
            
            for j, (email_type, prefix) in enumerate(zip(email_types, email_prefixes)):
                if j == 0:  # Skip first one as it's the contact's main email
                    email_address = contact.email
                else:
                    email_address = f'{base_email}.{prefix}@{domain}'
                
                email = Email.objects.create(
                    contact=contact,
                    email_address=email_address,
                    email_type=email_type,
                    is_primary=j == 0,
                    is_verified=True,
                    refs={'links': {'contacts': [contact.contact_id]}}
                )
                self.stdout.write(f'✅ Created email: {email.email_address} for {contact.email}')
        
        # Create a superuser for admin access
        if not Contact.objects.filter(email='admin@webclerk.com').exists():
            admin = Contact.objects.create(
                email='admin@webclerk.com',
                name_first='WebClerk',
                name_last='Administrator',
                company='WebClerk Inc',
                title='System Administrator',
                role='admin',
                password=make_password('admin123'),
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f'✅ Created admin user: {admin.email}')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Test data population completed!'))
        self.stdout.write(self.style.SUCCESS('\n📊 Summary:'))
        self.stdout.write(f'Contacts: {Contact.objects.count()}')
        self.stdout.write(f'Actions: {Action.objects.count()}')
        self.stdout.write(f'Phones: {Phone.objects.count()}')
        self.stdout.write(f'Locationes: {Location.objects.count()}')
        self.stdout.write(f'Domains: {Domain.objects.count()}')
        self.stdout.write(f'Emails: {Email.objects.count()}')
        
        self.stdout.write(self.style.SUCCESS('\n🔑 Admin Login:'))
        self.stdout.write('Email: admin@webclerk.com')
        self.stdout.write('Password: admin123')
        self.stdout.write('URL: http://localhost:8000/admin/')
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Test your Universal API:'))
        self.stdout.write('Contacts: http://localhost:8000/wcapi/contacts/manage/')
        self.stdout.write('Actions: http://localhost:8000/wcapi/actions/manage/')
        self.stdout.write('Phones: http://localhost:8000/wcapi/phones/manage/')
        self.stdout.write('Locationes: http://localhost:8000/wcapi/addresses/manage/')
        self.stdout.write('Domains: http://localhost:8000/wcapi/domains/manage/')
        self.stdout.write('Emails: http://localhost:8000/wcapi/emails/manage/')