from django.contrib import admin
from .models import ConversionProject, SourceFile, ColumnMap, Oddity, StagingRow, PassLog


@admin.register(ConversionProject)
class ConversionProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'supplier_name', 'status', 'pass_count', 'dt_created')
    list_filter = ('status',)
    search_fields = ('name', 'supplier_name')


@admin.register(SourceFile)
class SourceFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'file_type', 'row_count', 'dt_created')
    list_filter = ('file_type',)


@admin.register(ColumnMap)
class ColumnMapAdmin(admin.ModelAdmin):
    list_display = ('source_column', 'target_model', 'target_field', 'confidence', 'status', 'pass_number')
    list_filter = ('status', 'target_model')
    search_fields = ('source_column', 'target_field')


@admin.register(Oddity)
class OddityAdmin(admin.ModelAdmin):
    list_display = ('category', 'severity', 'description', 'source_column', 'source_row', 'resolution')
    list_filter = ('severity', 'category', 'resolution')
    search_fields = ('description', 'category', 'source_value')


@admin.register(StagingRow)
class StagingRowAdmin(admin.ModelAdmin):
    list_display = ('source_row_number', 'target_model', 'status', 'pass_number')
    list_filter = ('status', 'target_model')


@admin.register(PassLog)
class PassLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'pass_number', 'status', 'rows_processed', 'rows_staged', 'oddities_found', 'llm_calls')
    list_filter = ('status',)
