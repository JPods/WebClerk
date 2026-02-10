from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.serializers.transaction_serializers import ProposalSerializer, ProposalLineSerializer
from apps.core.services import wcapi


class ProposalViewSet(viewsets.ModelViewSet):
    """
    REST API viewset for Proposal management.
    Uses WCAPI for all save operations to maintain consistency and security.
    """
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        return self.queryset

    def perform_create(self, serializer):
        """Create proposal using WCAPI save."""
        data = serializer.validated_data.copy()
        data['model_name'] = 'proposal'

        # Use WCAPI save for consistency
        result = wcapi.save_item('proposal', request=self.request, data=data)
        if result[1] == 'created':
            # Set the created instance on serializer for response
            instance = Proposal.objects.get(pk=result[0])
            serializer.instance = instance
        else:
            raise Exception("Failed to create proposal")

    def perform_update(self, serializer):
        """Update proposal using WCAPI save."""
        instance = self.get_object()
        data = serializer.validated_data.copy()
        data['model_name'] = 'proposal'
        data['id'] = instance.id

        # Use WCAPI save for consistency
        result = wcapi.save_item('proposal', request=self.request, data=data, id=instance.id)
        if result[1] == 'updated':
            # Refresh instance
            instance.refresh_from_db()
            serializer.instance = instance
        else:
            raise Exception("Failed to update proposal")

    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convert proposal to sales order."""
        proposal = self.get_object()
        try:
            from apps.transactions.services.proposal_to_order import transfer_proposal_to_order
            result = transfer_proposal_to_order(
                proposal=proposal,
                line_ids=request.data.get('line_ids'),
                transfer_all=request.data.get('transfer_all', True),
                order_status=request.data.get('order_status', 'confirmed'),
                preserve_proposal=request.data.get('preserve_proposal', True),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def totals(self, request, pk=None):
        """Get detailed totals for proposal."""
        proposal = self.get_object()
        totals = proposal.update_sell_cost_totals(persist=False)
        return Response(totals)

    # Backwards-compatible alias expected by external docs/tests
    @action(detail=True, methods=['post'], url_path='convert-to-sales-order')
    def convert_to_sales_order(self, request, pk=None):
        """Alias for convert_to_order to support legacy route naming."""
        return self.convert_to_order(request, pk)


class ProposalLineViewSet(viewsets.ModelViewSet):
    """
    REST API viewset for Proposal Line management.
    Uses WCAPI for all save operations.
    """
    queryset = ProposalLine.objects.all()
    serializer_class = ProposalLineSerializer

    def get_queryset(self):
        """Filter by proposal if specified."""
        queryset = self.queryset
        proposal_id = self.request.query_params.get('proposal_id')
        if proposal_id:
            queryset = queryset.filter(proposal_id=proposal_id)
        return queryset

    def perform_create(self, serializer):
        """Create proposal line using WCAPI save."""
        data = serializer.validated_data.copy()
        data['model_name'] = 'proposal_line'

        result = wcapi.save_item('proposal_line', request=self.request, data=data)
        if result[1] == 'created':
            instance = ProposalLine.objects.get(pk=result[0])
            serializer.instance = instance
        else:
            raise Exception("Failed to create proposal line")

    def perform_update(self, serializer):
        """Update proposal line using WCAPI save."""
        instance = self.get_object()
        data = serializer.validated_data.copy()
        data['model_name'] = 'proposal_line'
        data['id'] = instance.id

        result = wcapi.save_item('proposal_line', request=self.request, data=data, id=instance.id)
        if result[1] == 'updated':
            instance.refresh_from_db()
            serializer.instance = instance
        else:
            raise Exception("Failed to update proposal line")

    def perform_destroy(self, instance):
        """Delete proposal line using WCAPI."""
        wcapi.delete_item('proposal_line', request=self.request, id=instance.id)