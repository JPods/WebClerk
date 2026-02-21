"""
ViewSet for Action model with CRUD operations.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers

from apps.core.models import Action


# system fields inherited from BaseModel (read-only)
_BASE_RO = [
    'id', 'uuid', 'dt_created', 'dt_modified', 'version',
    'is_deleted', 'is_archived', 'metadata', 'refs', 'prefs',
    'actions', 'comments', 'health_rating',
]


class ActionSerializer(serializers.ModelSerializer):
    """Serializer for Action model."""

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
            'project_metadata',
        ]
        read_only_fields = _BASE_RO


class ActionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Action. Writes go through /wcapi/save/."""

    queryset = Action.objects.active()
    serializer_class = ActionSerializer
