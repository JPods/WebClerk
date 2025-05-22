from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Contact

class ContactAdmin(UserAdmin):
    model = Contact
    list_display = ('email', 'name_first', 'name_last', 'get_roles', 'is_email_verified', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'is_email_verified', 'role')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'name_first', 'name_last', 'name_middle', 'role',
                'company', 'prefix', 'salutation', 'suffix', 'rank', 'attention'
            )
        }),
        ('Verification', {'fields': ('is_email_verified', 'verification_code', 'verification_code_expiry')}),
        ('Additional Info', {'fields': ('comment_alert', 'opt_out', 'publish', 'comment')}),
        ('Metadata', {'fields': ('refs', 'metadata')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'name_first', 'name_last', 'name_middle', 'role', 'password1', 'password2',
                'is_active', 'is_staff', 'is_email_verified', 'company', 'prefix', 'salutation',
                'suffix', 'rank', 'attention', 'comment_alert', 'opt_out', 'publish', 'comment',
                'refs', 'metadata'
            ),
        }),
    )
    search_fields = ('email', 'name_first', 'name_last')
    ordering = ('email',)

    def get_roles(self, obj):
        return ", ".join(obj.role) if obj.role else "None"
    get_roles.short_description = 'Roles'

admin.site.register(Contact, ContactAdmin)