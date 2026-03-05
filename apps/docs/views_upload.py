from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from apps.docs.models import Document
from common.models import default_document_metadata


def _uploads_root() -> str:
    base_dir = getattr(settings, "BASE_DIR", None)
    base = str(base_dir) if base_dir else os.getcwd()
    root = os.path.join(base, ".local", "uploads", "document")
    os.makedirs(root, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    name = os.path.basename(name or "")
    if not name:
        return "upload"
    return name.replace("..", "").replace("/", "").replace("\\", "")


def _compute_checksum(file_obj) -> str:
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


def _build_storage_path(filename: str) -> Dict[str, str]:
    now = datetime.utcnow()
    y = now.strftime("%Y")
    m = now.strftime("%m")
    ext = os.path.splitext(filename)[1]
    key = f"uploads/document/{y}/{m}/{uuid.uuid4().hex}{ext}"
    return {
        "key": key,
        "full": os.path.join(str(getattr(settings, "BASE_DIR", os.getcwd())), key),
        "storage": "local",
    }


def _serialize_document(doc: Document) -> Dict[str, Any]:
    return {
        "id": doc.id,
        "uuid": str(doc.uuid) if getattr(doc, "uuid", None) else None,
        "name": doc.name,
        "slug": doc.slug,
        "status": doc.status,
        "description": doc.description,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "path": doc.path,
        "checksum": doc.checksum,
        "model_name": doc.model_name,
        "dt_created": doc.dt_created,
    }


class DocumentUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required"}, status=status.HTTP_400_BAD_REQUEST)

        model_name = request.data.get("model_name") or ""
        parent_id = request.data.get("parent_id")
        purpose = request.data.get("purpose") or "attachment"
        description = request.data.get("description") or ""

        filename = _safe_filename(upload.name)
        mime_type = upload.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        checksum = _compute_checksum(upload)
        existing = Document.objects.filter(checksum=checksum).first()
        if existing:
            if purpose == "attachment":
                metadata = default_document_metadata()
                now_ms = int(timezone.now().timestamp() * 1000)
                metadata.setdefault("history", {})
                metadata["history"]["created"] = {"dt": now_ms, "contact_id": 0}
                metadata["history"]["modified"] = {"dt": now_ms, "contact_id": 0}
                metadata["original_name"] = filename
                metadata["purpose"] = purpose

                cloned_path = dict(existing.path) if isinstance(existing.path, dict) else existing.path
                cloned = Document.objects.create(
                    name=filename,
                    description=description,
                    mime_type=existing.mime_type or mime_type,
                    size_bytes=existing.size_bytes or upload.size,
                    path=cloned_path,
                    checksum=checksum,
                    model_name=model_name or None,
                    data={"parent_id": parent_id, "purpose": purpose, "source_document_id": existing.id},
                    metadata=metadata,
                )

                if isinstance(cloned.path, dict):
                    cloned.path["url"] = cloned.path.get("url") or f"/wcapi/document/{cloned.id}/"
                    cloned.save(update_fields=["path"])

                payload = {
                    "document_id": cloned.id,
                    "path": (cloned.path or {}).get("key") if isinstance(cloned.path, dict) else None,
                    "checksum": cloned.checksum,
                    "is_duplicate": True,
                    "url": (cloned.path or {}).get("url") if isinstance(cloned.path, dict) else f"/wcapi/document/{cloned.id}/",
                    "name": cloned.name,
                    "size_bytes": cloned.size_bytes,
                    "mime_type": cloned.mime_type,
                    "document": _serialize_document(cloned),
                }
                return Response(payload, status=status.HTTP_201_CREATED)

            payload = {
                "document_id": existing.id,
                "path": (existing.path or {}).get("key") if isinstance(existing.path, dict) else None,
                "checksum": existing.checksum,
                "is_duplicate": True,
                "url": (existing.path or {}).get("url") if isinstance(existing.path, dict) else None,
                "name": existing.name,
                "size_bytes": existing.size_bytes,
                "mime_type": existing.mime_type,
                "document": _serialize_document(existing),
            }
            return Response(payload, status=status.HTTP_200_OK)

        upload.seek(0)
        storage = _build_storage_path(filename)
        full_path = storage["full"]
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        rel_key = storage["key"]
        # Don't set URL here - will set after document creation
        url = None
        metadata = default_document_metadata()
        now_ms = int(timezone.now().timestamp() * 1000)
        metadata.setdefault("history", {})
        metadata["history"]["created"] = {"dt": now_ms, "contact_id": 0}
        metadata["history"]["modified"] = {"dt": now_ms, "contact_id": 0}
        metadata["original_name"] = filename
        metadata["purpose"] = purpose

        if any(k.startswith("address_") for k in request.data.keys()):
            addr = metadata.get("address", {})
            addr["street"] = request.data.get("address_street", addr.get("street"))
            addr["street2"] = request.data.get("address_street2", addr.get("street2"))
            addr["city"] = request.data.get("address_city", addr.get("city"))
            addr["state"] = request.data.get("address_state", addr.get("state"))
            addr["postal_code"] = request.data.get("address_postal_code", addr.get("postal_code"))
            addr["country"] = request.data.get("address_country", addr.get("country"))
            addr["source"] = "manual"
            metadata["address"] = addr

        if request.data.get("geo_lat") and request.data.get("geo_lng"):
            try:
                addr = metadata.get("address", {})
                addr_geo = addr.get("geo", {})
                addr_geo["lat"] = float(request.data.get("geo_lat"))
                addr_geo["lng"] = float(request.data.get("geo_lng"))
                if request.data.get("geo_accuracy"):
                    addr_geo["accuracy"] = float(request.data.get("geo_accuracy"))
                addr["geo"] = addr_geo
                addr["source"] = "browser"
                addr["captured_at"] = now_ms
                metadata["address"] = addr
            except Exception:
                pass

        doc = Document.objects.create(
            name=filename,
            description=description,
            mime_type=mime_type,
            size_bytes=upload.size,
            path={"storage": "local", "key": rel_key, "url": f"/wcapi/document/{0}/", "full": full_path},  # Placeholder URL
            checksum=checksum,
            model_name=model_name or None,
            data={"parent_id": parent_id, "purpose": purpose},
            metadata=metadata,
        )

        # Update the path with the correct URL now that we have the document ID
        doc.path["url"] = f"/wcapi/document/{doc.id}/"
        doc.save(update_fields=['path'])

        payload = {
            "document_id": doc.id,
            "path": rel_key,
            "checksum": checksum,
            "is_duplicate": False,
            "url": doc.path.get("url") if isinstance(doc.path, dict) else f"/wcapi/document/{doc.id}/",
            "name": doc.name,
            "size_bytes": doc.size_bytes,
            "mime_type": doc.mime_type,
            "document": _serialize_document(doc),
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class DocumentDownloadView(APIView):
    def get(self, request, document_id: int):
        doc = Document.objects.filter(pk=document_id).first()
        if not doc:
            raise Http404("document not found")
        path = (doc.path or {}) if isinstance(doc.path, dict) else {}
        full_path = path.get("full")
        if not full_path or not os.path.exists(full_path):
            raise Http404("file not found")
        doc.increment_access()
        return FileResponse(open(full_path, "rb"), as_attachment=True, filename=doc.name or None)


class DocumentDeleteView(APIView):
    def delete(self, request, document_id: int):
        doc = Document.objects.filter(pk=document_id).first()
        if not doc:
            raise Http404("document not found")

        path = (doc.path or {}) if isinstance(doc.path, dict) else {}
        full_path = path.get("full")
        try:
            if full_path and os.path.exists(full_path):
                os.remove(full_path)
        except Exception:
            pass

        if hasattr(doc, "is_deleted"):
            setattr(doc, "is_deleted", True)
        if hasattr(doc, "is_active"):
            setattr(doc, "is_active", False)
        doc.save()

        return Response({"ok": True, "id": doc.id}, status=status.HTTP_200_OK)
