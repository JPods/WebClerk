# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/create_superuser.py
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
import django
django.setup()
from django.contrib.auth import get_user_model

email = 'admin@webclerk.com'
first_name = 'Super'
last_name = 'Admin'
password = '123456'

contact = get_user_model()

try:
    if not contact.objects.filter(email='$email').exists():
        contact.objects.create_superuser(
            email=f'{email}',
            name_first=f'{first_name}',
            name_last=f'{last_name}',
            password=f'{password}'
        )
        print("Superuser created successfully")
    else:
        print(f"Superuser with email {email} already exists")
except Exception as e:
    print(f"Error creating superuser: {e}")
    exit(1)