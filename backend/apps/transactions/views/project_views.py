from typing import Any, Dict
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.apps import apps

Project = apps.get_model("transactions", "Project")

class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "options", "head"]

    def get(self, request, *args, **kwargs):
        qs = Project.objects.active().order_by("-id")
        data = []
        for p in qs:
            data.append({
                "id": p.id,
                "situation": getattr(p, "situation", None),
                "objective": getattr(p, "objective", None),
                "priority": getattr(p, "priority", None),
                "status": getattr(p, "status", None),
                "attention": getattr(p, "attention", None),
                "intent": getattr(p, "intent", None),
                "category": getattr(p, "category", None),
            })
        return Response(data=data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        body: Dict[str, Any] = request.data or {}
        accepted = {
            "situation": body.get("situation"),
            "objective": body.get("objective"),
            "priority": body.get("priority"),
            "status": body.get("status"),
            "attention": body.get("attention"),
            "intent": body.get("intent"),
            "category": body.get("category"),
        }
        create_kwargs = {k: v for k, v in accepted.items() if v is not None}
        obj = Project.objects.create(**create_kwargs)
        return Response(data={"id": obj.pk}, status=status.HTTP_201_CREATED)