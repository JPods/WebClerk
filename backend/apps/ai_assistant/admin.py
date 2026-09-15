from django.contrib import admin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from common.admin_mixins import ScalarFirstFieldsetMixin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "sources", "feedback", "dt_created")


@admin.register(Conversation)
class ConversationAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    # Scalar fields: context_page, dt_created, dt_modified, session_key
    list_display = ("context_page", "session_key", "dt_created")
    list_filter = ("dt_created",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(ScalarFirstFieldsetMixin, SchemaLabelsAdminMixin, admin.ModelAdmin):
    # Scalar fields: content, dt_created, feedback, role
    list_display = ("content", "feedback", "role", "dt_created")
    list_filter = ("role", "feedback")

    @admin.display(description="content")
    def content_preview(self, obj):
        return obj.content[:80]
