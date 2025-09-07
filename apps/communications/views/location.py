# path: apps/communications/views/location.py
from rest_framework import generics, status, pagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import LocationSerializer
from ..models import Location
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # Add this import
from common.api_responses import api_response


class CommPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500


class LocationView(generics.ListCreateAPIView):
    """Handles listing and creating locations with role-based field access."""

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommPagination

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('locations', 'view', self.request.user)
        if not accessible_fields:
            # Fallback to legacy table key if 'locations' not configured yet
            accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Location.objects.none()
        return Location.objects.all()

    @extend_schema(
        summary="List Locationes",
    description="Retrieve a list of locations, filtered by user role permissions from settings.",
        responses={
            200: LocationSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def get(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        response = super().get(request, *args, **kwargs)
        if raw_flag:
            return response
        data = response.data
        if isinstance(data, dict) and {'results', 'count'}.issubset(data.keys()):
            meta = {
                'total': data.get('count'),
                'page_size': data.get('page_size') or request.query_params.get('page_size') or CommPagination.page_size,
                'next': data.get('next'),
                'previous': data.get('previous'),
            }
            results = data.get('results')
            payload = {'results': results}
            payload.update({k: v for k, v in meta.items() if v is not None})
            return api_response(data=payload, raw=raw_flag)
        return api_response(data=data, raw=raw_flag)

    @extend_schema(
        summary="Create Location",
    description="Create a new location and link to a contact, restricted by role-based editable fields.",
        request=LocationSerializer,
        responses={
            201: LocationSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('locations', 'edit', request.user)
        if not accessible_fields:
            accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create address first, then set refs
        address = serializer.save()
        # Record submission snapshot
        try:
            address.record_submission_snapshot(request.data, actor_id=getattr(request.user, 'id', 0))
            address.save(update_fields=['prefs', 'dt_modified'])
        except Exception:
            pass

        # Properly handle refs.links.contacts structure
        if not address.refs:
            address.refs = default_refs()

        if 'links' not in address.refs:
            address.refs['links'] = {}

        if 'contacts' not in address.refs['links']:
            address.refs['links']['contacts'] = []

        # Add contact ID to the proper location
        if request.user.id not in address.refs['links']['contacts']:
            address.refs['links']['contacts'].append(request.user.id)

        # Save the updated refs
        address.save()

        # Response
        if raw_flag:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED, raw=raw_flag)


class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a location with role-based field access."""

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('locations', 'view', self.request.user)
        if not accessible_fields:
            accessible_fields = get_accessible_fields('addresses', 'view', self.request.user)
        if not accessible_fields:
            return Location.objects.none()
        return Location.objects.all()

    @extend_schema(
        summary="Get Location",
    description="Retrieve a specific location by ID, filtered by user role permissions from settings.",
        responses={
            200: LocationSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        response = super().get(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(data=response.data, raw=raw_flag)

    @extend_schema(
        summary="Update Location",
    description="Update a location (partial update), restricted by role-based editable fields.",
        request=LocationSerializer,
        responses={
            200: LocationSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('locations', 'edit', request.user)
        if not accessible_fields:
            accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)
        response = super().patch(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(data=response.data, raw=raw_flag)

    @extend_schema(
        summary="Delete Location",
    description="Delete a location and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('locations', 'edit', request.user)
        if not accessible_fields:
            accessible_fields = get_accessible_fields('addresses', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)
        response = super().delete(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(message="Deleted", data=None, status_code=response.status_code, raw=raw_flag)
