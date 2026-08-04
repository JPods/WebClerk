"""Seed communication behavior Setting and detail_layout Settings for email, phone, address, domain."""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


class Command(BaseCommand):
    help = "Create communication behaviors + detail layouts"

    def handle(self, *args, **options):
        # 1. Centralized Communication Behaviors
        s, c = Setting.objects.update_or_create(ida='comm-behaviors', defaults={
            'purpose': 'feature', 'parent_model': 'wc', 'name': 'Communication Behaviors',
            'config': {
                'shared': {
                    'click_actions': {
                        'phone': {'click': 'dial', 'shift_click': 'sms', 'widget': 'phone_dialer'},
                        'email': {'click': 'compose', 'shift_click': 'copy', 'widget': 'email_composer'},
                        'address': {'click': 'map', 'shift_click': 'copy', 'widget': 'address_formatter'},
                        'domain': {'click': 'open_url', 'shift_click': 'copy', 'widget': 'domain_link'},
                    },
                    'validation': {
                        'phone': {'normalize': True, 'min_digits': 7},
                        'email': {'validate_format': True},
                        'address': {'require_city_state': False},
                        'domain': {'validate_url': False},
                    },
                    'display': {
                        'phone': {'format': '(###) ###-####', 'show_country_code': True},
                        'email': {'truncate_at': 40},
                        'address': {'multiline': True, 'single_line_format': 'street, city, state zip'},
                        'domain': {'linkify': True},
                    },
                },
                'permissions': {
                    'add': ['admin', 'manager', 'user'],
                    'edit': ['admin', 'manager', 'user'],
                    'delete': ['admin', 'manager'],
                },
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: comm-behaviors")

        # 2. Email layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-email', defaults={
            'purpose': 'detail_layout', 'parent_model': 'email', 'name': 'Email Detail',
            'config': {
                'model': 'email', 'family': 'comm',
                'sections': [{'type': 'header', 'layout': 'single-column', 'fields': [
                    {'field': 'email', 'label': 'Email', 'type': 'action', 'widget': 'email_composer', 'help': 'Click to compose, Shift+click to copy'},
                    {'field': 'name', 'label': 'Name'},
                    {'field': 'attention', 'label': 'Attn'},
                    {'field': 'type', 'label': 'Type', 'type': 'select', 'options': ['work', 'personal', 'billing', 'support', 'other']},
                    {'field': 'opt_out', 'label': 'Opt Out', 'type': 'select', 'options': ['', 'opted_out', 'bounced', 'unsubscribed']},
                    {'field': 'is_primary', 'label': 'Primary', 'type': 'readonly'},
                    {'field': 'is_verified', 'label': 'Verified', 'type': 'readonly'},
                ]}],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: email layout")

        # 3. Phone layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-phone', defaults={
            'purpose': 'detail_layout', 'parent_model': 'phone', 'name': 'Phone Detail',
            'config': {
                'model': 'phone', 'family': 'comm',
                'sections': [{'type': 'header', 'layout': 'single-column', 'fields': [
                    {'field': 'number', 'label': 'Number', 'type': 'action', 'widget': 'phone_dialer', 'help': 'Click to dial, Shift+click for SMS'},
                    {'field': 'country_code', 'label': 'Country', 'type': 'readonly'},
                    {'field': 'format', 'label': 'Formatted', 'type': 'readonly'},
                    {'field': 'name', 'label': 'Name'},
                    {'field': 'attention', 'label': 'Attn'},
                    {'field': 'opt_out', 'label': 'Opt Out'},
                ]}],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: phone layout")

        # 4. Address layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-address', defaults={
            'purpose': 'detail_layout', 'parent_model': 'address', 'name': 'Address Detail',
            'config': {
                'model': 'address', 'family': 'comm',
                'sections': [{'type': 'header', 'layout': 'single-column', 'fields': [
                    {'field': 'full', 'label': 'Full', 'type': 'action', 'widget': 'address_formatter', 'help': 'Click to map, Shift+click to copy'},
                    {'field': 'address1', 'label': 'Street 1'},
                    {'field': 'address2', 'label': 'Street 2'},
                    {'field': 'city', 'label': 'City'},
                    {'field': 'state', 'label': 'State'},
                    {'field': 'zip', 'label': 'Zip'},
                    {'field': 'country', 'label': 'Country'},
                    {'field': 'address_type', 'label': 'Type', 'type': 'select', 'options': ['billing', 'shipping', 'home', 'work', 'other']},
                    {'field': 'instructions', 'label': 'Instructions'},
                ]}],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: address layout")

        # 5. Domain layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-domain', defaults={
            'purpose': 'detail_layout', 'parent_model': 'domain', 'name': 'Domain Detail',
            'config': {
                'model': 'domain', 'family': 'comm',
                'sections': [{'type': 'header', 'layout': 'single-column', 'fields': [
                    {'field': 'path', 'label': 'URL', 'type': 'action', 'widget': 'domain_link', 'help': 'Click to open, Shift+click to copy'},
                    {'field': 'type', 'label': 'Type', 'type': 'select', 'options': ['website', 'linkedin', 'twitter', 'facebook', 'instagram', 'github', 'youtube', 'other']},
                    {'field': 'status', 'label': 'Status', 'type': 'select', 'options': ['active', 'inactive', 'archived']},
                    {'field': 'comment', 'label': 'Notes'},
                    {'field': 'sequence', 'label': 'Order', 'type': 'readonly'},
                    {'field': 'count_accessed', 'label': 'Accessed', 'type': 'readonly'},
                ]}],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: domain layout")

        self.stdout.write(self.style.SUCCESS("Done — 5 Settings created/updated"))
