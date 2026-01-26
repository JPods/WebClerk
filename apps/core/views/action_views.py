"""
ViewSet for Action model with CRUD operations.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import serializers

from apps.core.models import Action


class ActionSerializer(serializers.ModelSerializer):
    """Serializer for Action model."""
    
    class Meta:
        model = Action
        fields = '__all__'
        read_only_fields = ('id', 'uuid', 'dt_created', 'dt_modified')


class ActionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Action model providing CRUD operations.
    
    list: GET /actions/
    create: POST /actions/
    retrieve: GET /actions/{id}/
    update: PUT /actions/{id}/
    partial_update: PATCH /actions/{id}/
    destroy: DELETE /actions/{id}/
    """
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    
    def destroy(self, request, *args, **kwargs):
        """Delete an action record."""
        instance = self.get_object()
        action_id = instance.id
        self.perform_destroy(instance)
        return Response(
            {"deleted": True, "id": action_id},
            status=status.HTTP_200_OK
        )
