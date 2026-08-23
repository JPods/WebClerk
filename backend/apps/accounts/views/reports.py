"""
Accounts views — report endpoints.
"""
from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services.aged_receivables import (
    aged_receivables_report,
    customer_statement,
)


class AgedReceivablesView(APIView):
    """Aged receivables report data.

    GET /wcapi/reports/aged_receivables/
    GET /wcapi/reports/aged_receivables/?customer_id=42
    GET /wcapi/reports/aged_receivables/?as_of=2026-07-31
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of_str = request.query_params.get('as_of')
        customer_id = request.query_params.get('customer_id')

        as_of = None
        if as_of_str:
            try:
                as_of = date.fromisoformat(as_of_str)
            except ValueError:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        customer_ids = None
        if customer_id:
            try:
                customer_ids = [int(customer_id)]
            except ValueError:
                return Response(
                    {'detail': 'Invalid customer_id.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        report = aged_receivables_report(
            as_of_date=as_of,
            customer_ids=customer_ids,
        )
        return Response(report)


class CustomerStatementView(APIView):
    """Single customer statement data.

    GET /wcapi/reports/statement/<customer_id>/
    GET /wcapi/reports/statement/<customer_id>/?as_of=2026-07-31
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        as_of_str = request.query_params.get('as_of')

        as_of = None
        if as_of_str:
            try:
                as_of = date.fromisoformat(as_of_str)
            except ValueError:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            cid = int(customer_id)
        except ValueError:
            return Response(
                {'detail': 'Invalid customer_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = customer_statement(cid, as_of_date=as_of)
        return Response(report)
