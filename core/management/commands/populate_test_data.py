from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import Contact
from core.models.action import Action
from core.models.setting import Setting
from core.models.template import Template
from communications.models.phone import Phone
from communications.models.email import Email
from communications.models.domain import Domain
from communications.models.address import Address
import json
from datetime import datetime, timedelta
import uuid

class Command(BaseCommand):
    help = 'Populate database with test data for WebClerk 3.0 Universal API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion even with many users (use with caution)',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Create full dataset with lots of related data',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting WebClerk 3.0 test data population...'))
        
        # Safety checks
        total_contacts = Contact.objects.count()
        superusers = Contact.objects.filter(is_superuser=True).count()
        
        self.stdout.write(f'📊 Current database state:')
        self.stdout.write(f'   Total contacts: {total_contacts}')
        self.stdout.write(f'   Superusers: {superusers}')
        
        # Safety check for many users
        if total_contacts > 10 and not options.get('force'):
            self.stdout.write(self.style.WARNING(f'⚠️  Database has {total_contacts} contacts.'))
            self.stdout.write(self.style.WARNING('   This script will modify/delete data.'))
            confirm = input('Are you sure you want to continue? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.ERROR('❌ Operation cancelled by user.'))
                return
        
        # Preserve superusers if only one exists
        preserve_superuser = superusers == 1
        if preserve_superuser:
            superuser = Contact.objects.filter(is_superuser=True).first()
            self.stdout.write(f'🔒 Preserving single superuser: {superuser.email}')
        
        # Use existing contacts if we have 3 or more
        use_existing_contacts = total_contacts >= 3
        
        if use_existing_contacts:
            self.stdout.write(f'♻️  Using existing contacts instead of creating new ones')
            if preserve_superuser:
                contacts = list(Contact.objects.exclude(is_superuser=True)[:4])
            else:
                contacts = list(Contact.objects.all()[:4])
            
            if len(contacts) < 4:
                needed = 4 - len(contacts)
                self.stdout.write(f'📝 Need to create {needed} additional contacts')
                contacts.extend(self._create_contacts(needed))
        else:
            # Clear existing data but preserve superuser
            if preserve_superuser:
                Contact.objects.exclude(is_superuser=True).delete()
            else:
                Contact.objects.all().delete()
            
            # Clear other data
            self._clear_all_data()
            
            # Create new contacts
            self.stdout.write('📝 Creating 4 new contacts...')
            contacts = self._create_contacts(4)
        
        # Always clear and recreate communications data
        self._clear_communications_data()
        Action.objects.all().delete()
        Setting.objects.all().delete()
        Template.objects.all().delete()
        
        self.stdout.write(f'✅ Working with {len(contacts)} contacts')
        
        # Create all test data
        self._create_actions(contacts, full=options.get('full', False))
        self._create_phones(contacts, full=options.get('full', False))
        self._create_emails(contacts, full=options.get('full', False))
        self._create_domains(contacts, full=options.get('full', False))
        self._create_addresses(contacts, full=options.get('full', False))
        self._create_settings()
        self._create_templates()
        self._ensure_admin_user()
        self._print_summary()
    
    def _clear_all_data(self):
        """Clear all data"""
        Action.objects.all().delete()
        Setting.objects.all().delete()
        Template.objects.all().delete()
        self._clear_communications_data()
    
    def _clear_communications_data(self):
        """Clear communications data"""
        Phone.objects.all().delete()
        Email.objects.all().delete()
        Domain.objects.all().delete()
        Address.objects.all().delete()
    
    def _create_contacts(self, count):
        """Create specified number of contacts"""
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
        
        for i in range(min(count, len(contact_data))):
            data = contact_data[i]
            contact, created = Contact.objects.get_or_create(
                email=data['email'],
                defaults={
                    'name_first': data['name_first'],
                    'name_last': data['name_last'],
                    'company': data['company'],
                    'title': data['title'],
                    'role': data['role'],
                    'department': data['department'],
                    'password': make_password('testpass123'),
                    'is_active': True
                }
            )
            contacts.append(contact)
            if created:
                self.stdout.write(f'✅ Created contact: {contact.email}')
            else:
                self.stdout.write(f'♻️  Using existing contact: {contact.email}')
        
        return contacts
    
    
    
    def _create_actions(self, contacts, full=False):
        """Create actions for contacts - CORRECTED REFS STRUCTURE"""
        action_types = ['Call client', 'Send email', 'Schedule meeting', 'Follow up', 'Complete task', 'Review document']
        statuses = ['pending', 'in_progress', 'completed', 'cancelled', 'on_hold']
        priorities = ['low', 'medium', 'high', 'urgent']
        difficulties = ['easy', 'medium', 'hard', 'expert']
        qualities = ['draft', 'good', 'excellent', 'perfect']

        count_per_contact = 6 if full else 3

        for i, contact in enumerate(contacts):
            for j in range(count_per_contact):
                action_type = action_types[j % len(action_types)]
                status = statuses[j % len(statuses)]
                priority = priorities[j % len(priorities)]
                difficulty = difficulties[j % len(difficulties)]
                quality = qualities[j % len(qualities)]

                try:
                    action = Action.objects.create(
                        action=f'{action_type} - {contact.name_first}',
                        action_by=f'{contact.name_first} {contact.name_last}',
                        priority=priority,
                        difficulty=difficulty,
                        hours=round(1.0 + (j * 0.5), 1),
                        percent=min(25 + (j * 15), 100),
                        status=status,
                        quality=quality,
                        description=f'Action to {action_type.lower()} regarding project discussion',
                        dt_action=datetime.now() - timedelta(days=j),
                        dt_due=datetime.now() + timedelta(days=j+1),
                        dt_updated=datetime.now(),
                        refs={
                            "keywords": [action_type.lower(), "action", "task", priority, status, contact.name_first.lower(), contact.company.lower()],
                            "tags": [action_type.replace(' ', '_').lower(), priority, status, "task"],
                            "links": {"contacts": [contact.id]},  # ✅ CORRECT STRUCTURE
                            "categories": ["action", "task_management"],
                            "related_ids": []
                        },
                        comment=f'Action {j+1} for {contact.email} - {action_type}'
                    )
                    self.stdout.write(f'✅ Created action: {action.action} ({priority}) for {contact.email}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Could not create action: {e}')

    # Add these methods to your Command class:

    def _create_phones(self, contacts, full=False):
        """Create phone numbers for contacts - CORRECTED REFS STRUCTURE"""
        phone_types = ['Work', 'Mobile', 'Home', 'Fax', 'Office', 'Direct']
        
        base_phones = ['+1-555-01', '+1-555-02', '+1-555-03', '+1-555-04']
        count_per_contact = 6 if full else 3
        
        for contact in contacts:
            base = base_phones[contacts.index(contact) % len(base_phones)]
            
            for j in range(count_per_contact):
                phone_number = f'{base}{j:02d}'
                formatted_number = f'({phone_number[2:5]}) {phone_number[5:8]}-{phone_number[8:]}'
                phone_type = phone_types[j % len(phone_types)]
                
                try:
                    Phone.objects.create(
                        number=phone_number,
                        country_code='+1',
                        format=formatted_number,
                        name=f'{contact.name_first}\'s {phone_type}',
                        attention=f'{contact.name_first} {contact.name_last}',
                        opt_out=False,
                        refs={
                            "keywords": [phone_type.lower(), "phone", "communication", contact.name_first.lower(), contact.company.lower()],
                            "tags": [phone_type, "communication", "phone"],
                            "links": {"contacts": [contact.id]},
                            "categories": ["phone", "contact_info"],
                            "related_ids": []
                        },
                        comment=f'{phone_type} phone for {contact.email}'
                    )
                    self.stdout.write(f'✅ Created phone: {phone_number} ({phone_type}) for {contact.email}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Could not create phone: {e}')

    def _create_emails(self, contacts, full=False):
        """Create email addresses for contacts - CORRECTED REFS STRUCTURE"""
        email_types = ['work', 'personal', 'billing', 'support', 'marketing', 'admin']
        
        count_per_contact = 4 if full else 2
        
        for i, contact in enumerate(contacts):
            base_email = contact.email.split('@')[0]
            domain = contact.email.split('@')[1]
            
            for j in range(count_per_contact):
                if j == 0:
                    email_address = contact.email
                    email_type = 'work'
                    is_primary = True
                    is_verified = True
                else:
                    email_type = email_types[j % len(email_types)]
                    email_address = f'{base_email}.{email_type}@{domain}'
                    is_primary = False
                    is_verified = False
                
                try:
                    email = Email.objects.create(
                        email=email_address,
                        name=f'{contact.name_first}\'s {email_type.title()} Email',
                        attention=f'{contact.name_first} {contact.name_last}',
                        type=email_type,
                        opt_out='',
                        is_primary=is_primary,
                        is_verified=is_verified,
                        refs={
                            "keywords": [email_type, "email", "communication", contact.name_first.lower(), contact.company.lower(), domain],
                            "tags": [email_type, "communication", "email", "primary" if is_primary else "secondary"],
                            "links": {"contacts": [contact.id]},
                            "categories": ["email", "contact_info"],
                            "related_ids": []
                        },
                        comment=f'{email_type.title()} email for {contact.email}'
                    )
                    self.stdout.write(f'✅ Created email: {email.email} ({email_type}) for {contact.email}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Could not create email: {e}')

    def _create_domains(self, contacts, full=False):
        """Create domains for contacts - CORRECTED REFS STRUCTURE"""
        domain_extensions = ['.com', '.net', '.org', '.io', '.biz', '.co']
        domain_types = ['website', 'email', 'api', 'cdn', 'subdomain']
        
        count_per_contact = 3 if full else 2
        
        for contact in contacts:
            base_domain = contact.email.split('@')[1].split('.')[0]
            
            for j in range(count_per_contact):
                extension = domain_extensions[j % len(domain_extensions)]
                domain_name = f'{base_domain}{extension}'
                domain_type = domain_types[j % len(domain_types)]
                
                try:
                    Domain.objects.create(
                        path=domain_name,
                        type=domain_type,
                        refs={
                            "keywords": [domain_type, "domain", "web", base_domain, contact.company.lower(), extension[1:]],
                            "tags": [domain_type, "web", "infrastructure", "domain"],
                            "links": {"contacts": [contact.id]},
                            "categories": ["domain", "web_infrastructure"],
                            "related_ids": []
                        },
                        comment=f'{domain_type.title()} domain for {contact.company}'
                    )
                    self.stdout.write(f'✅ Created domain: {domain_name} ({domain_type}) for {contact.email}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Could not create domain: {e}')

    def _create_addresses(self, contacts, full=False):
        """Create addresses for contacts - CORRECTED REFS STRUCTURE"""
        address_types = ['Work', 'Home', 'Billing', 'Shipping', 'Corporate', 'Branch']
        cities = ['San Francisco', 'New York', 'Austin', 'Seattle', 'Denver', 'Portland']
        states = ['CA', 'NY', 'TX', 'WA', 'CO', 'OR']
        
        count_per_contact = 4 if full else 2
        
        for idx, contact in enumerate(contacts):
            for j in range(count_per_contact):
                city = cities[idx % len(cities)]
                state = states[idx % len(states)]
                address_type = address_types[j % len(address_types)]
                street_address = f'{(idx+1)*1000 + j*100} {address_type} Street'
                zip_code = f'{90000 + idx*1000 + j*100}'
                
                try:
                    Address.objects.create(
                        address1=street_address,
                        address2=f'Suite {j+1}' if j > 0 else '',
                        address_type=address_type,
                        city=city,
                        state=state,
                        zip=zip_code,
                        country='United States',
                        full=f'{street_address}, {city}, {state} {zip_code}',
                        instructions=f'Deliver to {address_type} address during business hours',
                        latitude=37.7749 + (idx * 0.1),
                        longitude=-122.4194 + (j * 0.1),
                        refs={
                            "keywords": [address_type.lower(), "address", "location", city.lower(), state.lower(), contact.name_first.lower(), contact.company.lower()],
                            "tags": [address_type, "location", "physical", "address"],
                            "links": {"contacts": [contact.id]},
                            "categories": ["address", "location"],
                            "related_ids": []
                        },
                        comment=f'{address_type} address for {contact.email}'
                    )
                    self.stdout.write(f'✅ Created address: {city} ({address_type}) for {contact.email}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Could not create address: {e}')




    
    def _create_settings(self):
        """Create system settings"""
        settings_data = [
            {
                'name': 'API Rate Limit',
                'purpose': 'api_rate_limit',
                'role': 'system',
                'table_name': 'system_config',
                'data': {'limit': 1000, 'window': 'hour'},
                'is_active': True
            },
            {
                'name': 'Default Timezone',
                'purpose': 'default_timezone',
                'role': 'system',
                'table_name': 'system_config',
                'data': {'timezone': 'America/Los_Angeles'},
                'is_active': True
            },
            {
                'name': 'Email Verification',
                'purpose': 'email_verification',
                'role': 'security',
                'table_name': 'security_config',
                'data': {'required': True, 'expiry_hours': 24},
                'is_active': True
            },
            {
                'name': 'Upload Size Limit',
                'purpose': 'upload_limit',
                'role': 'system',
                'table_name': 'system_config',
                'data': {'max_size_mb': 10, 'allowed_types': ['jpg', 'png', 'pdf']},
                'is_active': True
            }
        ]
        
        for setting_data in settings_data:
            try:
                setting = Setting.objects.create(
                    name=setting_data['name'],
                    purpose=setting_data['purpose'],
                    role=setting_data['role'],
                    table_name=setting_data['table_name'],
                    data=setting_data['data'],
                    is_active=setting_data['is_active'],
                    comment=f'System setting for {setting_data["purpose"]}'
                )
                self.stdout.write(f'✅ Created setting: {setting.name}')
            except Exception as e:
                self.stdout.write(f'⚠️ Could not create setting: {e}')
    
    def _create_templates(self):
        """Create templates"""
        template_data = [
            {
                'name': 'Welcome Email Template',
                'purpose': 'welcome_email',
                'table_name': 'email_templates',
                'comment': 'Welcome email sent to new users'
            },
            {
                'name': 'Password Reset Template',
                'purpose': 'password_reset',
                'table_name': 'email_templates',
                'comment': 'Password reset email template'
            },
            {
                'name': 'Meeting Reminder Template',
                'purpose': 'meeting_reminder',
                'table_name': 'notification_templates',
                'comment': 'Meeting reminder notification template'
            },
            {
                'name': 'Follow-up Task Template',
                'purpose': 'followup_task',
                'table_name': 'task_templates',
                'comment': 'Template for follow-up tasks'
            },
            {
                'name': 'Invoice Template',
                'purpose': 'invoice_document',
                'table_name': 'document_templates',
                'comment': 'Standard invoice document template'
            }
        ]
        
        for tmpl_data in template_data:
            try:
                template = Template.objects.create(
                    name=tmpl_data['name'],
                    purpose=tmpl_data['purpose'],
                    table_name=tmpl_data['table_name'],
                    comment=tmpl_data['comment']
                )
                self.stdout.write(f'✅ Created template: {template.name}')
            except Exception as e:
                self.stdout.write(f'⚠️ Could not create template: {e}')
    
    def _ensure_admin_user(self):
        """Ensure we have an admin user"""
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
        else:
            self.stdout.write(f'♻️  Admin user already exists: admin@webclerk.com')
    
    def _print_summary(self):
        """Print final summary"""
        self.stdout.write(self.style.SUCCESS('\n🎉 Test data population completed!'))
        self.stdout.write(self.style.SUCCESS('\n📊 Final Summary:'))
        self.stdout.write(f'📞 Contacts: {Contact.objects.count()}')
        self.stdout.write(f'⚡ Actions: {Action.objects.count()}')
        self.stdout.write(f'⚙️  Settings: {Setting.objects.count()}')
        self.stdout.write(f'📄 Templates: {Template.objects.count()}')
        self.stdout.write(f'📱 Phones: {Phone.objects.count()}')
        self.stdout.write(f'📧 Emails: {Email.objects.count()}')
        self.stdout.write(f'🌐 Domains: {Domain.objects.count()}')
        self.stdout.write(f'🏠 Addresses: {Address.objects.count()}')
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Your Beautiful Contact Page:'))
        self.stdout.write('📞 Contact View: http://localhost:8000/contact/')
        self.stdout.write('⚡ Universal API: http://localhost:8000/WCapi/')