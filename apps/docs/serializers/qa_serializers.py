from rest_framework import serializers
from apps.docs.models.question_answer import QuestionAnswer

class QASerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionAnswer
        fields = [
            'id','uuid','question','answer','question_setting','answered_by_contact','answered_by_name',
            'status','security_level','sequence','count_accessed','is_active','dt_created','dt_modified','version'
        ]
        read_only_fields = ['id','uuid','dt_created','dt_modified','version','count_accessed']

class QASearchSerializer(serializers.ModelSerializer):
    highlight_snippet = serializers.CharField(read_only=True)
    class Meta:
        model = QuestionAnswer
        fields = ['id','uuid','question','status','security_level','highlight_snippet']
