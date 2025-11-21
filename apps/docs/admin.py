from django.contrib import admin
from .models import Document, QuestionAnswer, Tag, Linkage, LinkageIndex


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "document_type", "status", "dt_created")
    list_filter = ("document_type", "status")
    search_fields = ("name", "content", "tags__name")
    readonly_fields = ("uuid", "dt_created", "dt_modified")


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "document", "dt_created")
    list_filter = ("document",)
    search_fields = ("question", "answer")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tag_type", "is_active")
    list_filter = ("tag_type", "is_active")
    search_fields = ("name", "description")


@admin.register(Linkage)
class LinkageAdmin(admin.ModelAdmin):
    list_display = ("id", "source_table", "source_id", "target_table", "target_id", "link_type")
    list_filter = ("source_table", "target_table", "link_type")
    search_fields = ("source_table", "target_table")


@admin.register(LinkageIndex)
class LinkageIndexAdmin(admin.ModelAdmin):
    list_display = ("id", "table_name", "record_id", "keyword", "weight")
    list_filter = ("table_name",)
    search_fields = ("table_name", "record_id", "keyword")
