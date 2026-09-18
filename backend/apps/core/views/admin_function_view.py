"""
Admin Functions API — list and execute admin functions.

GET  /api/core/admin-functions/           — list available functions
POST /api/core/admin-functions/run/       — execute a function with JSON params
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
import logging

from apps.core.admin_functions import list_functions, run_function

logger = logging.getLogger(__name__)


class AdminFunctionListView(APIView):
    """List all available admin functions."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        category = request.query_params.get('category')
        functions = list_functions(category=category)
        return Response({'functions': functions}, status=status.HTTP_200_OK)


class AdminFunctionRunView(APIView):
    """Execute an admin function.

    POST body:
    {
        "function": "af_purge_records_faker",
        "params": {"model": "document", "max_id": 10, "confirm": true}
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        fn_name = request.data.get('function')
        params = request.data.get('params', {})

        if not fn_name:
            return Response({'error': 'function name required'}, status=status.HTTP_400_BAD_REQUEST)

        result = run_function(fn_name, params)

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
