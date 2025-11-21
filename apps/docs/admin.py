from django.contrib import admin
from .models import Document, QuestionAnswer, Tag, Linkage, LinkageIndex


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Linkage)
class LinkageAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(LinkageIndex)
class LinkageIndexAdmin(admin.ModelAdmin):
    list_display = ("id",)
