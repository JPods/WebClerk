"""LinkageEntry serializers."""

from rest_framework import serializers
from apps.docs.models import LinkageEntry


class LinkageEntrySerializer(serializers.ModelSerializer):
    """Full serializer for LinkageEntry model."""
    
    # Computed fields
    group_entry_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LinkageEntry
        fields = [
            'id',
            'group_id',
            'model_name',
            'record_id',
            'purpose',
            'name',
            'note',
            'role',
            'sequence',
            # BaseModel fields
            'refs',
            'prefs',
            'metadata',
            'actions',
            'comments',
            'is_active',
            'is_deleted',
            'is_archived',
            'security_level',
            'dt_created',
            'dt_modified',
            # Computed
            'group_entry_count',
        ]
        read_only_fields = ['id', 'dt_created', 'dt_modified', 'group_entry_count']
    
    def get_group_entry_count(self, obj) -> int:
        """Return count of entries in the same group."""
        return LinkageEntry.objects.filter(group_id=obj.group_id).count()


class LinkageEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating LinkageEntry records."""
    
    class Meta:
        model = LinkageEntry
        fields = [
            'group_id',
            'model_name',
            'record_id',
            'purpose',
            'name',
            'note',
            'role',
            'sequence',
            'refs',
            'prefs',
            'metadata',
        ]
    
    def validate(self, attrs):
        """Ensure record isn't already linked elsewhere."""
        model_name = attrs.get('model_name')
        record_id = attrs.get('record_id')
        
        if model_name and record_id is not None:
            existing = LinkageEntry.objects.filter(
                model_name=model_name, 
                record_id=record_id
            ).first()
            if existing:
                raise serializers.ValidationError(
                    f"Record {model_name}:{record_id} already linked to group {existing.group_id}"
                )
        
        return attrs


class LinkageEntryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating LinkageEntry records."""
    
    class Meta:
        model = LinkageEntry
        fields = [
            'purpose',
            'name',
            'note',
            'role',
            'sequence',
            'refs',
            'prefs',
            'metadata',
            'is_active',
        ]


class LinkageGroupSerializer(serializers.Serializer):
    """Serializer for creating a new linkage group with multiple entries."""
    
    entries = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of link entries: [{model_name, record_id, role?, note?, sequence?}, ...]"
    )
    purpose = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_entries(self, entries):
        """Validate each entry has required fields."""
        for i, entry in enumerate(entries):
            if 'model_name' not in entry:
                raise serializers.ValidationError(f"Entry {i} missing 'model_name'")
            if 'record_id' not in entry:
                raise serializers.ValidationError(f"Entry {i} missing 'record_id'")
        return entries
    
    def create(self, validated_data):
        """Create a new group with all entries."""
        group_id = LinkageEntry.create_group(
            entries=validated_data['entries'],
            purpose=validated_data.get('purpose'),
            name=validated_data.get('name'),
        )
        return {'group_id': group_id}


class LinkageGroupSummarySerializer(serializers.Serializer):
    """Read-only serializer for group summary."""
    
    group_id = serializers.IntegerField()
    entry_count = serializers.IntegerField()
    models = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="{model_name: [record_ids], ...}"
    )
    purpose = serializers.CharField(allow_null=True)
    name = serializers.CharField(allow_null=True)
