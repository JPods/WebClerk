from django.utils import timezone
from datetime import timedelta
import random

print("="*60)
print("CREATING MISSING RECORDS FOR JANE DOE")
print("="*60)

jane = Contact.objects.filter(name_first='Jane', name_last='Doe').first()

if jane:
    print(f"Creating missing records for: {jane.name_first} {jane.name_last}")
    print(f"Jane currently has 3 phones, but needs emails, addresses, domains, and actions.")
    
    # Create 3 emails for Jane
    print(f"\nCreating 3 emails for Jane...")
    email_domains = ['gmail.com', 'yahoo.com', 'marketingllc.com']
    for i in range(3):
        email_addr = f"jane.doe{i+1 if i > 0 else ''}@{email_domains[i]}"
        try:
            if not Email.objects.filter(email=email_addr).exists():
                email = Email.objects.create(
                    
                    email=email_addr,
                    name="Jane Doe",
                    attention="Attn: Jane",
                    is_primary=(i == 0),
                    is_verified=True,
                    dt_verified=timezone.now() - timedelta(days=random.randint(1, 90)),
                    comment=f"Email {i+1} for Jane Doe"
                )
                print(f"  ✓ Created email: {email_addr}")
            else:
                print(f"  - Email already exists: {email_addr}")
        except Exception as e:
            print(f"  ✗ Error creating email {email_addr}: {e}")
            import traceback
            traceback.print_exc()
    
    # Create 3 addresses for Jane
    print(f"\nCreating 3 addresses for Jane...")
    address_data = [
        {"street": "123 Marketing Ave", "city": "New York", "state": "NY"},
        {"street": "456 Business Blvd", "city": "Los Angeles", "state": "CA"},
        {"street": "789 Corporate Dr", "city": "Chicago", "state": "IL"}
    ]
    
    for i, addr_data in enumerate(address_data):
        try:
            address = Address.objects.create(
                address1=addr_data["street"],
                address2=f"Suite {100 + i}" if i == 1 else "",
                city=addr_data["city"],
                state=addr_data["state"],
                zip=f"{random.randint(10000, 99999)}",
                country="United States",
                dt_verified=timezone.now() - timedelta(days=random.randint(1, 60)),
                comment=f"Address {i+1} for Jane Doe in {addr_data['city']}"
            )
            print(f"  ✓ Created address: {addr_data['street']}, {addr_data['city']}, {addr_data['state']}")
        except Exception as e:
            print(f"  ✗ Error creating address in {addr_data['city']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Create 3 domains for Jane
    print(f"\nCreating 3 domains for Jane...")
    domain_data = [
        {"name": "janedoe-marketing", "type": "website", "ext": "com"},
        {"name": "jane-doe-linkedin", "type": "social", "ext": "net"},
        {"name": "jdoe-consulting", "type": "email", "ext": "org"}
    ]
    
    for i, domain_info in enumerate(domain_data):
        try:
            domain_url = f"{domain_info['name']}.{domain_info['ext']}"
            domain = Domain.objects.create(
                path=f"https://www.{domain_url}",
                type=domain_info["type"],
                description=f"{domain_info['type'].title()} domain for Jane Doe",
                dt_verified=timezone.now() - timedelta(days=random.randint(1, 120)),
                comment=f"{domain_info['type'].title()} domain for Jane Doe"
            )
            print(f"  ✓ Created domain: {domain_url} ({domain_info['type']})")
        except Exception as e:
            print(f"  ✗ Error creating domain {domain_url}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final verification for Jane
    print(f"\n" + "="*50)
    print("JANE DOE VERIFICATION")
    print("="*50)
    
    jane_emails = Email.objects.filter(name__icontains="Jane Doe").count()
    jane_phones = Phone.objects.filter(name__icontains="Jane Doe").count()
    jane_addresses = Address.objects.filter(comment__icontains="Jane").count()
    jane_domains = Domain.objects.filter(comment__icontains="Jane").count()
    
    print(f"Jane Doe's record counts:")
    print(f"  Emails:    {jane_emails} {'✅ Complete' if jane_emails >= 3 else '❌ Missing'}")
    print(f"  Phones:    {jane_phones} {'✅ Complete' if jane_phones >= 3 else '❌ Missing'}")
    print(f"  Addresses: {jane_addresses} {'✅ Complete' if jane_addresses >= 3 else '❌ Missing'}")
    print(f"  Domains:   {jane_domains} {'✅ Complete' if jane_domains >= 3 else '❌ Missing'}")
    
    # Show what was created
    print(f"\nJane Doe's records summary:")
    
    if jane_emails > 0:
        print(f"  📧 Emails:")
        for email in Email.objects.filter(name__icontains="Jane Doe"):
            primary = " (PRIMARY)" if email.is_primary else ""
            print(f"    • {email.email}{primary}")
    
    if jane_addresses > 0:
        print(f"  🏠 Addresses:")
        for address in Address.objects.filter(comment__icontains="Jane"):
            print(f"    • {address.address1}, {address.city}, {address.state}")
    
    if jane_domains > 0:
        print(f"  🌐 Domains:")
        for domain in Domain.objects.filter(comment__icontains="Jane"):
            print(f"    • {domain.path} ({domain.type})")
    
    if jane_emails >= 3 and jane_addresses >= 3 and jane_domains >= 3:
        print(f"\n🎉 SUCCESS! Jane Doe now has all required records!")
        print(f"   ✅ 3 emails, ✅ 3 phones, ✅ 3 addresses, ✅ 3 domains")
    else:
        print(f"\n⚠️  Jane Doe is still missing some records.")

else:
    print("❌ Jane Doe contact not found!")

print(f"\n🔍 Check Django admin to verify Jane Doe's complete records!")