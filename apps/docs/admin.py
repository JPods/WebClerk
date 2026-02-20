from django.contrib import admin
from .models import Document, QuestionAnswer, Tag, LinkageEntry


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model."""
    # Scalar fields alphabetically for list display
    scalar_fields = (
        'checksum',
        'comment',
        'confidential',
        'count_accessed',
        'dt_created',
        'dt_modified',
        'id',
        'ida',
        'is_active',
        'is_archived',
        'is_deleted',
        'mime_type',
        'model_name',
        'name',
        'retention_period',
        'security_level',
        'sequence',
        'size_bytes',
        'slug',
        'status',
        'uuid',
        'version',
    )
    # Object/JSON fields alphabetically
    object_fields = (
        'actions',
        'body',
        'comments',
        'copyright',
        'data',
        'description',
        'metadata',
        'path',
        'prefs',
        'refs',
    )
    list_display = ('id', 'name', 'status', 'model_name', 'mime_type', 'size_bytes', 'dt_created')
    list_filter = ('status', 'model_name', 'confidential', 'is_active')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'search_vector')
    ordering = ('-dt_created',)
    
    fieldsets = (
        ('Identification', {'fields': ('id', 'ida', 'uuid', 'name', 'slug')}),
        ('Status & Classification', {'fields': ('status', 'model_name', 'confidential', 'security_level')}),
        ('File Info', {'fields': ('mime_type', 'size_bytes', 'checksum', 'path')}),
        ('Content', {'fields': ('description', 'body', 'comment', 'data', 'copyright')}),
        ('Counters & Sequence', {'fields': ('count_accessed', 'sequence', 'retention_period')}),
        ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
        ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
        ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
    )


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    """Admin interface for QuestionAnswer model."""
    # Scalar fields alphabetically for list display
    scalar_fields = (
        'answer_id',
        'count_accessed',
        'dt_created',
        'dt_modified',
        'id',
        'ida',
        'is_active',
        'is_archived',
        'is_deleted',
        'parent_id',
        'parent_model',
        'question_id',
        'security_level',
        'sequence',
        'status',
        'uuid',
        'version',
    )
    # Object/JSON/Text fields alphabetically
    object_fields = (
        'actions',
        'answer',
        'answered_by',
        'comments',
        'metadata',
        'prefs',
        'question',
        'refs',
        'setting',
    )
    list_display = ('id', 'question', 'answer', 'parent_model', 'parent_id', 'status', 'sequence', 'dt_created')
    list_filter = ('status', 'parent_model', 'is_active')
    search_fields = ('question', 'answer', 'parent_model')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified', 'search_vector')
    ordering = ('-dt_created',)
    raw_id_fields = ('setting',)
    
    fieldsets = (
        ('Identification', {'fields': ('id', 'ida', 'uuid')}),
        ('Question & Answer', {'fields': ('question', 'answer', 'status')}),
        ('Template Link', {'fields': ('setting', 'question_id', 'answer_id')}),
        ('Parent Link', {'fields': ('parent_model', 'parent_id')}),
        ('Attribution', {'fields': ('answered_by', 'security_level')}),
        ('Counters & Sequence', {'fields': ('count_accessed', 'sequence')}),
        ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
        ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
        ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for Tag model."""
    # Scalar fields alphabetically
    scalar_fields = (
        'count_accessed',
        'dt_created',
        'dt_modified',
        'id',
        'ida',
        'is_active',
        'is_archived',
        'is_deleted',
        'model_name',
        'name',
        'purpose',
        'record_id',
        'security_level',
        'sequence',
        'status',
        'uuid',
        'version',
    )
    # Object/JSON fields alphabetically
    object_fields = (
        'actions',
        'comments',
        'data',
        'metadata',
        'prefs',
        'refs',
    )
    list_display = ('id', 'name', 'purpose', 'status', 'model_name', 'record_id', 'sequence', 'dt_created')
    list_filter = ('purpose', 'status', 'model_name', 'is_active')
    search_fields = ('name', 'purpose', 'model_name')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    ordering = ('-dt_created',)
    
    fieldsets = (
        ('Identification', {'fields': ('id', 'ida', 'uuid', 'name')}),
        ('Classification', {'fields': ('purpose', 'status', 'security_level')}),
        ('Target Record', {'fields': ('model_name', 'record_id')}),
        ('Counters & Sequence', {'fields': ('count_accessed', 'sequence')}),
        ('Data', {'fields': ('data',)}),
        ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
        ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
        ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
    )


@admin.register(LinkageEntry)
class LinkageEntryAdmin(admin.ModelAdmin):
    """Admin interface for LinkageEntry model - unified linkage table."""
    # Scalar fields
    scalar_fields = (
        'dt_created',
        'dt_modified',
        'group_id',
        'id',
        'ida',
        'is_active',
        'is_archived',
        'is_deleted',
        'model_name',
        'name',
        'purpose',
        'record_id',
        'role',
        'security_level',
        'sequence',
        'uuid',
        'version',
    )
    # Object/JSON/Text fields
    object_fields = (
        'actions',
        'comments',
        'metadata',
        'note',
        'prefs',
        'refs',
    )
    list_display = ('id', 'group_id', 'model_name', 'record_id', 'purpose', 'role', 'name', 'dt_created')
    list_filter = ('model_name', 'purpose', 'role', 'is_active')
    search_fields = ('name', 'purpose', 'note', 'model_name')
    readonly_fields = ('uuid', 'dt_created', 'dt_modified')
    ordering = ('group_id', 'sequence', '-dt_created')
    
    fieldsets = (
        ('Group & Link', {'fields': ('group_id', 'model_name', 'record_id', 'role', 'sequence')}),
        ('Identification', {'fields': ('id', 'ida', 'uuid', 'name')}),
        ('Classification', {'fields': ('purpose', 'security_level')}),
        ('Content', {'fields': ('note',)}),
        ('Lifecycle', {'fields': ('is_active', 'is_deleted', 'is_archived', 'version')}),
        ('Timestamps', {'fields': ('dt_created', 'dt_modified')}),
        ('Extended Data', {'fields': ('refs', 'prefs', 'metadata', 'actions', 'comments'), 'classes': ('collapse',)}),
    )

