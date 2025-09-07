# path: apps/communications/views/phone.py
from rest_framework import generics, status, pagination
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import PhoneSerializer
from ..models import Phone
from apps.core.models import Contact
from rest_framework.permissions import IsAuthenticated
from django.db import models
from apps.core.utils import get_accessible_fields
from common.models import default_refs  # ✅ ADD THIS IMPORT
from common.api_responses import api_response

class CommPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500

class PhoneView(generics.ListCreateAPIView):
    """Handles listing and creating phones with role-based field access."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommPagination

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('phones', 'view', self.request.user)
        if not accessible_fields:
            return Phone.objects.none()
        return Phone.objects.all()

    @extend_schema(
        summary="List Phones",
        description="Retrieve a list of phones, filtered by user role permissions from settings.",
        responses={
            200: PhoneSerializer(many=True),
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
        summary="Create Phone",
        description="Create a new phone and link to a contact, restricted by role-based editable fields.",
        request=PhoneSerializer,
        responses={
            201: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        }
    )
    def post(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
 
                 
        # ✅ STEP 1: Create phone FIRST
        phone = serializer.save()
        # Record submission snapshot
        try:
            phone.record_submission_snapshot(request.data, actor_id=getattr(request.user, 'id', 0))
            phone.save(update_fields=['prefs', 'dt_modified'])
        except Exception:
            pass
        
        # ✅ STEP 2: Setup refs structure properly
        if not phone.refs:
            phone.refs = default_refs()
        
        if 'links' not in phone.refs:
            phone.refs['links'] = {}
            
        if 'contacts' not in phone.refs['links']:
            phone.refs['links']['contacts'] = []
        
        # ✅ STEP 3: Add contact ID to proper location
        if request.user.id not in phone.refs['links']['contacts']:
            phone.refs['links']['contacts'].append(request.user.id)
        
        # ✅ STEP 4: Save the updated refs
        phone.save()
        
        if raw_flag:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED, raw=raw_flag)

class PhoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Handles retrieving, updating, and deleting a phone with role-based field access."""
    queryset = Phone.objects.all()
    serializer_class = PhoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user roles and viewable fields."""
        accessible_fields = get_accessible_fields('phones', 'view', self.request.user)
        if not accessible_fields:
            return Phone.objects.none()
        return Phone.objects.all()

    @extend_schema(
        summary="Get Phone",
        description="Retrieve a specific phone by ID, filtered by user role permissions from settings.",
        responses={
            200: PhoneSerializer,
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
        summary="Update Phone",
        description="Update a phone (partial update), restricted by role-based editable fields.",
        request=PhoneSerializer,
        responses={
            200: PhoneSerializer,
            400: OpenApiResponse(description="Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)
        response = super().patch(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(data=response.data, raw=raw_flag)

    @extend_schema(
        summary="Delete Phone",
        description="Delete a phone and remove from contact refs, restricted by role-based permissions.",
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        raw_flag = request.query_params.get('raw') == '1'
        accessible_fields = get_accessible_fields('phones', 'edit', request.user)
        if not accessible_fields:
            return api_response(success=False, status_code=status.HTTP_403_FORBIDDEN, message="No editable fields allowed for your role", raw=raw_flag)
        response = super().delete(request, *args, **kwargs)
        if raw_flag:
            return response
        return api_response(message="Deleted", data=None, status_code=response.status_code, raw=raw_flag)