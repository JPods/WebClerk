"""QuestionAnswer serializers."""

from rest_framework import serializers
from apps.docs.models import QuestionAnswer


class QuestionAnswerSerializer(serializers.ModelSerializer):
    """Serializer for QuestionAnswer model."""
    
    # Include the setting name for display
    setting_name = serializers.CharField(source='setting.name', read_only=True, allow_null=True)
    
    class Meta:
        model = QuestionAnswer
        fields = [
            'id',
            'question',
            'answer',
            'setting_id',
            'setting_name',
            'question_id',
            'answer_id',
            'parent_model',
            'parent_id',
            'answered_by',
            'status',
            'sequence',
            'metadata',
            'dt_created',
            'dt_modified',
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'setting_name']


class QuestionAnswerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating QuestionAnswer records."""
    
    class Meta:
        model = QuestionAnswer
        fields = [
            'question',
            'answer',
            'setting_id',
            'question_id',
            'answer_id',
            'parent_model',
            'parent_id',
            'status',
            'sequence',
            'metadata',
        ]


class QuestionAnswerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating QuestionAnswer records (answering)."""
    
    class Meta:
        model = QuestionAnswer
        fields = [
            'answer',
            'answer_id',
            'status',
            'answered_by',
            'metadata',
        ]
