"""
RBAC Permissions API Views.

Endpoints for retrieving user permissions and role information.
"""
from __future__ import annotations

from typing import Any, Dict

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.services.role_filter import (
    build_user_context,
    get_user_filter_config,
    can_create,
    can_delete,
    get_allowed_fields,
)


class UserPermissionsView(APIView):
    """
    Get current user's effective permissions.
    
    Returns role information and per-model access controls.
    
    GET /wcapi/permissions/
    Response:
    {
        "roles": ["user_sales", "user_production"],
        "org_ids": {
            "customer": [],
            "vendor": [],
            "manufacturer": [],
            "employee": [1]
        },
        "contact_id": 42,
        "is_superuser": false,
        "models": {
            "order": {
                "view": true,
                "view_fields": ["*"] or ["id", "ida", ...],
                "edit": true,
                "edit_fields": ["*"] or ["status", ...],
                "create": true,
                "delete": false
            },
            ...
        }
    }
    """
    
    permission_classes = [IsAuthenticated]
    
    # Models to include in permissions response
    INCLUDED_MODELS = [
        # Transactions
        "order", "invoice", "proposal", "purchase", "workorder",
        # Orgs
        "customer", "vendor", "manufacturer",
        # Core
        "contact", "action", "document",
        # Products
        "item", "category",
    ]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Build user context
        context = build_user_context(user)
        
        # Build per-model permissions
        models_perms: Dict[str, Dict[str, Any]] = {}
        
        for model_name in self.INCLUDED_MODELS:
            config = get_user_filter_config(user, model_name)
            
            if config:
                view_fields = config.get("view_fields", [])
                edit_fields = config.get("edit_fields", [])
                
                models_perms[model_name] = {
                    "view": bool(view_fields),
                    "view_fields": view_fields,
                    "edit": bool(edit_fields),
                    "edit_fields": edit_fields,
                    "create": config.get("allow_create", False),
                    "delete": config.get("allow_delete", False),
                }
            else:
                # No config = no access
                models_perms[model_name] = {
                    "view": False,
                    "view_fields": [],
                    "edit": False,
                    "edit_fields": [],
                    "create": False,
                    "delete": False,
                }
        
        response_data = {
            "user_id": context.get("user_id"),
            "roles": context.get("roles", []),
            "org_ids": context.get("org_ids", {}),
            "contact_id": context.get("contact_id"),
            "is_superuser": context.get("is_superuser", False),
            "models": models_perms,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class ModelPermissionsView(APIView):
    """
    Get permissions for a specific model.
    
    GET /wcapi/permissions/<model_name>/
    Response:
    {
        "model": "order",
        "view": true,
        "view_fields": ["*"],
        "edit": true,
        "edit_fields": ["status", "notes"],
        "create": true,
        "delete": false,
        "query_filters": {...}
    }
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, model_name=None, *args, **kwargs):
        if not model_name:
            return Response(
                {"detail": "model_name required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        config = get_user_filter_config(user, model_name)
        
        if not config:
            return Response({
                "model": model_name,
                "view": False,
                "view_fields": [],
                "edit": False,
                "edit_fields": [],
                "create": False,
                "delete": False,
                "query_filters": {},
            }, status=status.HTTP_200_OK)
        
        return Response({
            "model": model_name,
            "view": bool(config.get("view_fields")),
            "view_fields": config.get("view_fields", []),
            "edit": bool(config.get("edit_fields")),
            "edit_fields": config.get("edit_fields", []),
            "create": config.get("allow_create", False),
            "delete": config.get("allow_delete", False),
            "query_filters": config.get("query_filters", {}),
        }, status=status.HTTP_200_OK)
