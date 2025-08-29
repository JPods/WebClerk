from rest_framework import serializers
from apps.docs.models.linkage import Linkage

class LinkageSerializer(serializers.ModelSerializer):
    link_counts = serializers.SerializerMethodField()

    class Meta:
        model = Linkage
        fields = [
            'id','uuid','name','purpose','comment','metadata','refs','prefs','comments','health_rating',
            'created_dt','modified_dt','version','link_counts'
        ]
        read_only_fields = ['id','uuid','created_dt','modified_dt','version','link_counts']

    def get_link_counts(self, obj: Linkage):
        return obj.link_counts()
