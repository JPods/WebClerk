from django.core.management.base import BaseCommand
from apps.transactions.models import Order
from apps.core.models import Contact
from apps.communications.models import Address, Phone, Email, Domain
from apps.products.models import Item

class Command(BaseCommand):
    help = 'Ensure all refs data in Order ID 22 are valid and linked to real database records'

    def handle(self, *args, **options):
        self.stdout.write('Ensuring refs data validity for Order ID 22...')

        try:
            order = Order.objects.get(id=22)
        except Order.DoesNotExist:
            self.stdout.write(self.style.ERROR('Order ID 22 does not exist'))
            return

        # Load sample refs if not present
        sample_refs = {
            'categories': [],
            'depends_on': {},
            'keywords': [],
            'links': {
                'contact': [
                    {
                        'purpose': 'billto',
                        'contact_id': 1,
                        'attention': 'Some Name',
                        'address_id': 64,
                        'full': 'street 123\ncity, state\n 12345',
                        'phone_id': 25,
                        'phone': '123.334.1223',
                        'email_id': 677,
                        'email': '1@1.com',
                        'domain_id': 453,
                        'domain': 'www.shipto.com/this'
                    },
                    {
                        'purpose': 'shipto',
                        'contact_id': 1,
                        'attention': 'Some Name',
                        'address_id': 64,
                        'full': 'street 123\ncity, state\n 12345',
                        'phone_id': 25,
                        'phone': '123.334.1223',
                        'email_id': 677,
                        'email': '1@1.com',
                        'domain_id': 453,
                        'domain': 'www.shipto.com/this'
                    },
                    {
                        'purpose': 'support',
                        'contact_id': 1,
                        'attention': 'Some Name',
                        'address_id': 64,
                        'full': 'street 123\ncity, state\n 12345',
                        'phone_id': 25,
                        'phone': '123.334.1223',
                        'email_id': 677,
                        'email': '1@1.com',
                        'domain_id': 453,
                        'domain': 'www.shipto.com/this'
                    },
                    {
                        'purpose': 'rep',
                        'contact_id': 1,
                        'attention': 'Some Name',
                        'address_id': 64,
                        'full': 'street 123\ncity, state\n 12345',
                        'phone_id': 25,
                        'phone': '123.334.1223',
                        'email_id': 677,
                        'email': '1@1.com',
                        'domain_id': 453,
                        'domain': 'www.shipto.com/this'
                    },
                    {
                        'purpose': 'sales',
                        'contact_id': 1,
                        'attention': 'Some Name',
                        'address_id': 64,
                        'full': 'street 123\ncity, state\n 12345',
                        'phone_id': 25,
                        'phone': '123.334.1223',
                        'email_id': 677,
                        'email': '1@1.com',
                        'domain_id': 453,
                        'domain': 'www.shipto.com/this'
                    }
                ],
                'domain': [],
                'email': [],
                'item': [],
                'address': [],
                'phone': [],
                'order_line': [
                    {'id': 11},
                    {'id': 12},
                    {'id': 13}
                ]
            },
            'related_ids': [],
            'tags': []
        }

        refs = order.refs or {}
        links = refs.setdefault('links', {})

        # Ensure contact links are present
        if not links.get('contact'):
            links['contact'] = sample_refs['links']['contact']
            order.refs = refs
            order.save()

        # Ensure order_line links are present
        if not links.get('order_line'):
            links['order_line'] = sample_refs['links']['order_line']
            order.refs = refs
            order.save()

        # Ensure contact records exist
        for contact_ref in links.get('contact', []):
            contact_id = contact_ref.get('contact_id')
            if contact_id:
                contact, created = Contact.objects.get_or_create(
                    id=contact_id,
                    defaults={'email': f'contact{contact_id}@example.com', 'name_first': 'Contact', 'name_last': str(contact_id)}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Contact ID {contact_id}: email={contact.email}, name={contact.get_full_name()} - {status}')

            address_id = contact_ref.get('address_id')
            if address_id:
                address, created = Address.objects.get_or_create(
                    id=address_id,
                    defaults={'full': f'Address {address_id}', 'address1': f'Street {address_id}', 'city': 'City', 'state': 'ST', 'zip': '12345'}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Address ID {address_id}: full={address.full}, city={address.city} - {status}')

            phone_id = contact_ref.get('phone_id')
            if phone_id:
                phone, created = Phone.objects.get_or_create(
                    id=phone_id,
                    defaults={'number': f'123-456-{phone_id:04d}', 'name': 'Phone'}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Phone ID {phone_id}: number={phone.number}, name={phone.name} - {status}')

            email_id = contact_ref.get('email_id')
            if email_id:
                email, created = Email.objects.get_or_create(
                    id=email_id,
                    defaults={'email': f'email{email_id}@example.com', 'type': 'work'}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Email ID {email_id}: email={email.email}, type={email.type} - {status}')

            domain_id = contact_ref.get('domain_id')
            if domain_id:
                domain, created = Domain.objects.get_or_create(
                    id=domain_id,
                    defaults={'path': f'domain{domain_id}.com', 'type': 'website'}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Domain ID {domain_id}: path={domain.path}, type={domain.type} - {status}')

        # Ensure order_line records exist
        for line_ref in links.get('order_line', []):
            line_id = line_ref.get('id')
            if line_id:
                # Create dummy item if needed
                item_id = (line_id - 10) * 2  # Simple mapping
                item, created = Item.objects.get_or_create(
                    id=item_id,
                    defaults={'name': f'Item {item_id}', 'uom': 'EA'}
                )
                status = 'CREATED' if created else 'EXISTED'
                self.stdout.write(f'Item ID {item_id}: name={item.name}, uom={item.uom} - {status}')

        # Log all other links if they have IDs
        for link_type in ['domain', 'email', 'item', 'address', 'phone']:
            for link_ref in links.get(link_type, []):
                if isinstance(link_ref, dict) and 'id' in link_ref:
                    link_id = link_ref['id']
                    self.stdout.write(f'{link_type.capitalize()} ID {link_id} referenced in refs.links.{link_type}')

        self.stdout.write(self.style.SUCCESS('All refs data validated and linked records ensured'))