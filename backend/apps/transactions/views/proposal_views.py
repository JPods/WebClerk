from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.transactions.models import Proposal, ProposalLine
from apps.transactions.serializers.transaction_serializers import ProposalSerializer, ProposalLineSerializer


class ProposalViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Proposal. Writes go through /wcapi/save/."""

    queryset = Proposal.objects.active()
    serializer_class = ProposalSerializer

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


class ProposalLineViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for ProposalLine. Writes go through /wcapi/save/."""

    queryset = ProposalLine.objects.active()
    serializer_class = ProposalLineSerializer

    def get_queryset(self):
        """Filter by proposal if specified."""
        queryset = self.queryset
        proposal_id = self.request.query_params.get('proposal_id')
        if proposal_id:
            queryset = queryset.filter(proposal_id=proposal_id)
        return queryset