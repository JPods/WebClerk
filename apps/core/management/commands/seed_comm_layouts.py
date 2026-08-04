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

        # 6. Action detail_layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-action', defaults={
            'purpose': 'detail_layout', 'parent_model': 'action', 'name': 'Action Detail',
            'config': {
                'model': 'action', 'family': 'core',
                'sections': [{'type': 'header', 'layout': 'two-column', 'columns': [
                    {'title': 'Action', 'fields': [
                        {'field': 'action.en', 'label': 'Action', 'type': 'search', 'help': 'Action title'},
                        {'field': 'description.en', 'label': 'Description'},
                        {'field': 'status', 'label': 'Status', 'type': 'select', 'options': ['open', 'in_progress', 'review', 'completed', 'cancelled']},
                        {'field': 'kanban_column', 'label': 'Column', 'type': 'select', 'options': ['Backlog', 'Planning', 'InProcess', 'Review', 'Complete']},
                        {'field': 'priority', 'label': 'Priority', 'type': 'select', 'options': ['1', '2', '3', '4']},
                        {'field': 'difficulty', 'label': 'Difficulty'},
                        {'field': 'percent_complete', 'label': '% Done', 'type': 'readonly'},
                    ]},
                    {'title': 'Assignment', 'fields': [
                        {'field': 'project_name', 'label': 'Project', 'type': 'search'},
                        {'field': 'assigned_to', 'label': 'Assigned', 'help': 'Contact(s) responsible'},
                        {'field': 'dt_created', 'label': 'Created', 'type': 'readonly'},
                        {'field': 'dt_needed', 'label': 'Due Date'},
                        {'field': 'source_name', 'label': 'Source'},
                    ]},
                ]}],
                'edit_rules': {'locked_statuses': ['completed', 'cancelled'], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: action layout")

        # 7. Document detail_layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-document', defaults={
            'purpose': 'detail_layout', 'parent_model': 'document', 'name': 'Document Detail',
            'config': {
                'model': 'document', 'family': 'core',
                'sections': [{'type': 'header', 'layout': 'two-column', 'columns': [
                    {'title': 'Document', 'fields': [
                        {'field': 'name', 'label': 'Name', 'type': 'search'},
                        {'field': 'description', 'label': 'Description'},
                        {'field': 'purpose', 'label': 'Purpose', 'type': 'select'},
                        {'field': 'status', 'label': 'Status', 'type': 'select', 'options': ['draft', 'active', 'archived']},
                        {'field': 'dt_created', 'label': 'Created', 'type': 'readonly'},
                        {'field': 'dt_modified', 'label': 'Modified', 'type': 'readonly'},
                    ]},
                    {'title': 'Attachment', 'fields': [
                        {'field': 'config.file_path', 'label': 'File', 'type': 'readonly'},
                        {'field': 'config.file_type', 'label': 'Type', 'type': 'readonly'},
                        {'field': 'config.file_size', 'label': 'Size', 'type': 'readonly'},
                        {'field': 'parent_model', 'label': 'Parent', 'type': 'readonly'},
                        {'field': 'parent_id', 'label': 'Parent ID', 'type': 'readonly'},
                    ]},
                ]}],
                'edit_rules': {'locked_statuses': ['archived'], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: document layout")

        # 8. Contact detail_layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-contact', defaults={
            'purpose': 'detail_layout', 'parent_model': 'contact', 'name': 'Contact Detail',
            'config': {
                'model': 'contact', 'family': 'core',
                'sections': [
                    {'type': 'header', 'layout': 'three-column', 'columns': [
                        {'title': 'Contact', 'title_ida': True, 'fields': [
                            {'field': 'name_first', 'label': 'First', 'type': 'search'},
                            {'field': 'name_last', 'label': 'Last', 'type': 'search'},
                            {'field': 'attention', 'label': 'Attn', 'type': 'readonly', 'help': 'Calculated from first + last'},
                            {'field': 'company', 'label': 'Company', 'type': 'search'},
                            {'field': 'title', 'label': 'Title'},
                            {'field': 'email', 'label': 'Email', 'type': 'action', 'widget': 'email_composer'},
                            {'field': 'phone', 'label': 'Phone', 'type': 'action', 'widget': 'phone_dialer'},
                        ]},
                        {'title': 'Address', 'fields': [
                            {'field': 'address_full', 'label': 'Address', 'type': 'action', 'widget': 'address_formatter'},
                            {'field': 'city', 'label': 'City'},
                            {'field': 'state', 'label': 'State'},
                            {'field': 'zip', 'label': 'Zip'},
                            {'field': 'country', 'label': 'Country'},
                        ]},
                        {'title': 'Profile', 'fields': [
                            {'field': 'role', 'label': 'Role', 'type': 'select', 'options': ['user', 'admin', 'manager', 'owner']},
                            {'field': 'status', 'label': 'Status', 'type': 'select', 'options': ['active', 'inactive']},
                            {'field': 'salutation', 'label': 'Salutation'},
                            {'field': 'dt_created', 'label': 'Created', 'type': 'readonly'},
                        ], 'action_summary': True},
                    ]},
                    {'type': 'tabs', 'tabs': [
                        {'label': 'Communications', 'content': 'communications'},
                        {'label': 'Organizations', 'content': 'organizations'},
                        {'label': 'Actions', 'content': 'actions'},
                        {'label': 'Documents', 'content': 'documents'},
                        {'label': 'QA', 'content': 'qa'},
                        {'label': 'Notes', 'content': 'notes'},
                        {'label': 'History', 'content': 'history'},
                    ]},
                ],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: contact layout")

        # 9. QuestionAnswer detail_layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-question-answer', defaults={
            'purpose': 'detail_layout', 'parent_model': 'question_answer', 'name': 'QA Detail',
            'config': {
                'model': 'question_answer', 'family': 'core',
                'sections': [{'type': 'header', 'layout': 'single-column', 'fields': [
                    {'field': 'question', 'label': 'Question'},
                    {'field': 'answer', 'label': 'Answer'},
                    {'field': 'category', 'label': 'Category', 'type': 'select'},
                    {'field': 'status', 'label': 'Status', 'type': 'select', 'options': ['draft', 'active', 'archived']},
                    {'field': 'parent_model', 'label': 'Parent', 'type': 'readonly'},
                    {'field': 'parent_id', 'label': 'Parent ID', 'type': 'readonly'},
                    {'field': 'dt_created', 'label': 'Created', 'type': 'readonly'},
                ]}],
                'edit_rules': {'locked_statuses': ['archived'], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: question_answer layout")

        # 10. Report detail_layout
        s, c = Setting.objects.update_or_create(ida='detail-layout-report', defaults={
            'purpose': 'detail_layout', 'parent_model': 'report', 'name': 'Report Detail',
            'config': {
                'model': 'report', 'family': 'core',
                'sections': [{'type': 'header', 'layout': 'two-column', 'columns': [
                    {'title': 'Report', 'fields': [
                        {'field': 'name', 'label': 'Name', 'type': 'search'},
                        {'field': 'description', 'label': 'Description'},
                        {'field': 'model_name', 'label': 'Model', 'type': 'select', 'help': 'Which model this report applies to'},
                        {'field': 'output_type', 'label': 'Output', 'type': 'select', 'options': ['print', 'email', 'label', 'export', 'json', 'api', 'merge', 'script', 'action']},
                        {'field': 'category', 'label': 'Category', 'type': 'select', 'options': ['report', 'statement', 'list', 'summary', 'letter', 'label', 'export', 'utility', 'customer_facing', 'vendor_facing', 'operations', 'warehouse', 'accounting', 'sales_analysis', 'tool']},
                    ]},
                    {'title': 'Settings', 'fields': [
                        {'field': 'role_required', 'label': 'Role', 'help': 'Blank = all users'},
                        {'field': 'sort_order', 'label': 'Sort'},
                        {'field': 'record_id', 'label': 'Record', 'type': 'readonly', 'help': 'Tied to specific record if set'},
                        {'field': 'purpose', 'label': 'Purpose'},
                        {'field': 'dt_created', 'label': 'Created', 'type': 'readonly'},
                    ]},
                ]}],
                'edit_rules': {'locked_statuses': [], 'status_field': 'status'},
            },
            'is_active': True,
        })
        self.stdout.write(f"{'C' if c else 'U'} #{s.id}: report layout")

        self.stdout.write(self.style.SUCCESS("Done — 10 Settings created/updated"))
