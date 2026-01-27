from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import ScheduledTask, TaskRun, TaskConfig


class TaskConfigInline(admin.StackedInline):
    model = TaskConfig
    extra = 0
    fieldsets = (
        ('Processing Limits', {
            'fields': ('limit', 'batch_size'),
        }),
        ('Scope Filters', {
            'fields': ('app_filter', 'model_filter'),
            'classes': ('collapse',),
        }),
        ('Flags', {
            'fields': ('dry_run', 'verbose'),
        }),
        ('Custom Parameters', {
            'fields': ('extra_params',),
            'classes': ('collapse',),
        }),
    )


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status_badge', 'frequency', 'last_run_badge',
        'run_count', 'error_count', 'next_run_at'
    ]
    list_filter = ['status', 'frequency', 'last_run_status']
    search_fields = ['name', 'task_path', 'description']
    readonly_fields = [
        'last_run_at', 'last_run_status', 'last_run_duration',
        'next_run_at', 'run_count', 'error_count'
    ]
    inlines = [TaskConfigInline]
    
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'task_path', 'description'),
        }),
        ('Schedule', {
            'fields': ('frequency', 'run_at_hour', 'run_at_minute', 'run_on_day', 'crontab'),
        }),
        ('Status', {
            'fields': ('status',),
        }),
        ('Execution History', {
            'fields': (
                'last_run_at', 'last_run_status', 'last_run_duration',
                'next_run_at', 'run_count', 'error_count'
            ),
            'classes': ('collapse',),
        }),
        ('Configuration', {
            'fields': ('default_kwargs', 'max_retries', 'timeout_seconds'),
            'classes': ('collapse',),
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'paused': 'orange',
            'disabled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def last_run_badge(self, obj):
        if not obj.last_run_at:
            return '-'
        colors = {
            'success': 'green',
            'error': 'red',
        }
        color = colors.get(obj.last_run_status, 'gray')
        duration = f" ({obj.last_run_duration:.1f}s)" if obj.last_run_duration else ""
        return format_html(
            '<span style="color: {};">{}{}</span>',
            color, obj.last_run_at.strftime('%Y-%m-%d %H:%M'), duration
        )
    last_run_badge.short_description = 'Last Run'


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = [
        'task', 'status_badge', 'started_at', 'duration_display',
        'records_processed', 'records_updated', 'attempt'
    ]
    list_filter = ['status', 'task', 'started_at']
    search_fields = ['task__name', 'celery_task_id', 'error_message']
    readonly_fields = [
        'task', 'celery_task_id', 'status', 'started_at', 'finished_at',
        'duration', 'kwargs', 'result', 'error_message', 'error_traceback',
        'records_processed', 'records_updated', 'attempt'
    ]
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Task', {
            'fields': ('task', 'celery_task_id', 'status', 'attempt'),
        }),
        ('Timing', {
            'fields': ('started_at', 'finished_at', 'duration'),
        }),
        ('Input/Output', {
            'fields': ('kwargs', 'result', 'records_processed', 'records_updated'),
        }),
        ('Errors', {
            'fields': ('error_message', 'error_traceback'),
            'classes': ('collapse',),
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'success': 'green',
            'error': 'red',
            'timeout': 'orange',
            'retry': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration:.2f}s"
        return '-'
    duration_display.short_description = 'Duration'
    
    def has_add_permission(self, request):
        return False  # Runs are created by tasks, not manually
    
    def has_change_permission(self, request, obj=None):
        return False  # Runs are read-only


@admin.register(TaskConfig)
class TaskConfigAdmin(admin.ModelAdmin):
    list_display = ['task', 'limit', 'batch_size', 'app_filter', 'model_filter', 'dry_run']
    list_filter = ['dry_run', 'verbose']
    search_fields = ['task__name', 'app_filter', 'model_filter']
    
    fieldsets = (
        ('Task', {
            'fields': ('task',),
        }),
        ('Processing Limits', {
            'fields': ('limit', 'batch_size'),
        }),
        ('Scope Filters', {
            'fields': ('app_filter', 'model_filter'),
        }),
        ('Flags', {
            'fields': ('dry_run', 'verbose'),
        }),
        ('Custom Parameters', {
            'fields': ('extra_params',),
        }),
    )
