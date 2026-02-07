"""
Very basic database test to isolate the issue.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Basic database connection test"

    def handle(self, *args, **options):
        self.stdout.write("Testing basic database connection...")
        
        try:
            # Test 1: Try with Contact model instead of User (since User was swapped)
            from django.apps import apps
            Contact = apps.get_model('core', 'Contact')
            contact_count = Contact.objects.count()
            self.stdout.write(f"✅ Contact count: {contact_count}")
            
            # Test 2: Test Setting model but with a very simple query
            from apps.core.models.setting import Setting
            setting_count = Setting.objects.count()
            self.stdout.write(f"✅ Setting count: {setting_count}")
            
            # Test 3: Test without any filters
            self.stdout.write("Testing unfiltered Setting query...")
            all_settings = Setting.objects.all()[:3]  # Just get first 3
            self.stdout.write(f"✅ Got {len(all_settings)} settings without filters")
            
            # Test 4: Try with a simple filter
            self.stdout.write("Testing simple filter...")
            active_count = Setting.objects.filter(is_active=True).count()
            self.stdout.write(f"✅ Active settings count: {active_count}")
            
            # Test 5: Try the specific query that was failing
            self.stdout.write("Testing the failing query with .only()...")
            settings = Setting.objects.filter(is_active=True).only('parent_model', 'purpose', 'data')
            settings_list = list(settings)  # Force evaluation
            self.stdout.write(f"✅ Query with .only() succeeded: {len(settings_list)} records")
            
            # Test 6: Process the data (this is where it might freeze)
            self.stdout.write("Testing data processing...")
            for i, setting in enumerate(settings_list[:3]):  # Process first 3
                purpose = setting.purpose or 'general'
                model_name = setting.parent_model or 'general'
                data = setting.data or {}
                self.stdout.write(f"   Setting {i+1}: {model_name}:{purpose} = {len(str(data))} chars")
                if i >= 2:  # Only process first 3
                    break
            
            self.stdout.write(self.style.SUCCESS("All database tests passed!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Database test failed: {e}"))
            import traceback
            traceback.print_exc()