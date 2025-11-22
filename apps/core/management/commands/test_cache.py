"""
Simplified test command to debug cache population issues.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test cache population and debug issues"

    def handle(self, *args, **options):
        self.stdout.write("Starting cache test...")
        
        try:
            self.stdout.write("1. Testing Django setup...")
            from django.apps import apps
            self.stdout.write(f"   Django apps loaded: {len(apps.get_models())} models")
            
            self.stdout.write("2. Testing cache service...")
            from apps.core.services.cache_service import cache_service
            test_key = cache_service.make_key('test', 'connection')
            cache_service.set(test_key, 'test_value', ttl=60)
            retrieved = cache_service.get(test_key)
            self.stdout.write(f"   Cache test result: {retrieved}")
            
            self.stdout.write("3. Testing Setting model...")
            from apps.core.models.setting import Setting
            count = Setting.objects.count()
            self.stdout.write(f"   Setting records: {count}")
            
            if count > 0:
                self.stdout.write("4. Testing Setting query...")
                settings = Setting.objects.filter(is_active=True)[:5]
                for setting in settings:
                    self.stdout.write(f"   - {setting.name} ({setting.purpose})")
            else:
                self.stdout.write("4. No Setting records found")
                
            self.stdout.write("5. Testing SAFE cache tasks import...")
            from apps.core.tasks.safe_cache_tasks import update_all_settings_cache_safe
            self.stdout.write("   Safe cache tasks imported successfully")
            
            self.stdout.write("6. Testing SAFE cache population...")
            result = update_all_settings_cache_safe()
            self.stdout.write(f"   Result: {result}")
            
            self.stdout.write(self.style.SUCCESS("Test completed successfully!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during test: {e}"))
            import traceback
            traceback.print_exc()