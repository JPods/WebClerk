"""
ViewSet for Action model with CRUD operations.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers

from apps.core.models import Action

console_logger = logging.getLogger('console')


# system fields inherited from BaseModel (read-only)
_BASE_RO = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'metadata', 'refs', 'prefs',
    'actions', 'comments', 'health_rating',
]


class ActionSerializer(serializers.ModelSerializer):
    """Serializer for Action model."""
    
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Action
        fields = [
            'id', 'uuid', 'ida', 'dt_created', 'dt_modified', 'version',
            'is_active', 'security_level', 'is_deleted', 'is_archived',
            'metadata', 'refs', 'prefs', 'actions', 'comments', 'health_rating',
            'parent_action', 'action', 'description', 'assigned_to',
            'contact_id', 'languages', 'project_name', 'project_id',
            'project_ida', 'sequence', 'kanban_column', 'priority',
            'difficulty', 'status', 'percent_complete', 'burndown',
            'dt_start', 'dt_deadline', 'dt_expected', 'dt_completed',
            'dt_updated', 'duration', 'dt_start_original', 'dt_end_original',
            'created_by', 'start_by', 'deadline_by', 'expected_by',
            'completed_by', 'updated_by', 'end_by', 'linkage',
            'project_metadata', 'attachments',
        ]
        read_only_fields = _BASE_RO

    def get_attachments(self, obj):
        """Get attachments linked to this action."""
        try:
            from apps.docs.models import LinkageEntry, Document
            
            # Find linkage groups that include this action
            action_entries = LinkageEntry.objects.filter(
                model_name='action',
                record_id=obj.id
            )
            
            if not action_entries.exists():
                return []
            
            # Get group IDs
            group_ids = action_entries.values_list('group_id', flat=True).distinct()
            
            # Find all documents linked to these groups
            document_entries = LinkageEntry.objects.filter(
                group_id__in=group_ids,
                model_name='document'
            ).select_related('document')
            
            attachments = []
            for entry in document_entries:
                try:
                    # Get the document by record_id
                    doc = Document.objects.get(id=entry.record_id)
                    attachments.append({
                        'id': doc.id,
                        'name': doc.name,
                        'size_bytes': doc.size_bytes,
                        'mime_type': doc.mime_type,
                        'url': doc.path.get('url') if doc.path and isinstance(doc.path, dict) else None,
                    })
                except Document.DoesNotExist:
                    continue
            
            return attachments
        except Exception as e:
            console_logger.error(f"[ActionSerializer.get_attachments] Failed to get attachments for action {obj.id}: {e}")
            return []


class ActionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Action. Writes go through /wcapi/save/."""

    queryset = Action.objects.active()
    serializer_class = ActionSerializer
