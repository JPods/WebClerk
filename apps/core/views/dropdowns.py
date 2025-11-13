from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.core.services.frontend_dropdowns import frontend_dropdowns_service


class FrontendDropdownsView(APIView):
    """API view for serving frontend dropdown options."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Get all frontend dropdowns or a specific one."""
        dropdown_name = request.query_params.get('name')

        if dropdown_name:
            # Return specific dropdown
            dropdown = frontend_dropdowns_service.get_dropdown(dropdown_name)
            if dropdown is None:
                return Response(
                    {"error": f"Dropdown '{dropdown_name}' not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({dropdown_name: dropdown})

        # Return all dropdowns
        dropdowns = frontend_dropdowns_service.get_all_dropdowns()
        return Response(dropdowns)