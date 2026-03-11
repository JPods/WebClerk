from django.contrib import admin
from common.admin_schema_labels import SchemaLabelsAdminMixin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "sources", "feedback", "dt_created")


@admin.register(Conversation)
class ConversationAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    list_display = ("id", "user", "context_page", "dt_created")
    list_filter = ("dt_created",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(SchemaLabelsAdminMixin, admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "content_preview", "feedback", "dt_created")
    list_filter = ("role", "feedback")

    @admin.display(description="content")
    def content_preview(self, obj):
        return obj.content[:80]
