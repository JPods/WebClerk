from rest_framework import serializers
from apps.transactions.models.project import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'uuid', 'name', 'situation', 'objective', 'priority', 'status', 'attention',
            'contact_id', 'tasks', 'burndown', 'category', 'intent', 'logistics',
            'profit', 'profit_velocity', 'security_level', 'config', 'prefs',
            'dt_created', 'dt_modified', 'version'
        ]
        read_only_fields = ['id', 'uuid', 'burndown', 'dt_created', 'dt_modified', 'version']

    def validate_priority(self, value):  # guard even though model clean enforces
        if not (1 <= value <= 5):
            raise serializers.ValidationError('Priority must be 1-5')
        return value

    def validate_burndown(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError('Burndown must be 0-100')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Hide internal metrics if low role (reuse role rules infra later if desired)
        request = self.context.get('request')
        role = getattr(getattr(request, 'user', None), 'role', '') if request else ''
        if role not in ('admin', 'manager'):
            # remove profit velocity (example of conditional field hiding)
            data.pop('profit_velocity', None)
        return data
