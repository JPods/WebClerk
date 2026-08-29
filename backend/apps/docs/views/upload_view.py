from __future__ import annotations

import base64
import hashlib
import mimetypes
import os
import zlib
import uuid
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

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


def _encode_inline_content(file_obj) -> Dict[str, Any]:
    file_obj.seek(0)
    raw_bytes = file_obj.read()
    compressed = zlib.compress(raw_bytes, level=9)
    encoded = base64.b64encode(compressed).decode("ascii")
    return {
        "inline_encoding": "zlib+base64",
        "inline_content_b64": encoded,
        "inline_size_bytes": len(raw_bytes),
    }


def _decode_inline_content(doc: Document) -> bytes | None:
    data = doc.config if isinstance(doc.config, dict) else {}
    encoded = data.get("inline_content_b64")
    encoding = data.get("inline_encoding")
    if not isinstance(encoded, str) or not encoded:
        return None
    try:
        compressed = base64.b64decode(encoded.encode("ascii"))
        if encoding == "zlib+base64":
            return zlib.decompress(compressed)
        return compressed
    except Exception:
        return None


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
        "model_name": (doc.config or {}).get("parent_model", ""),
        "dt_created": doc.dt_created,
    }


class DocumentUploadView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
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
            existing_path = existing.path if isinstance(existing.path, dict) else {}
            existing_url = existing_path.get("url") if isinstance(existing_path, dict) else None
            if not isinstance(existing_url, str) or not existing_url:
                existing_url = f"/wcapi/document/{existing.id}/"
            payload = {
                "document_id": existing.id,
                "path": existing_path.get("key") if isinstance(existing_path, dict) else None,
                "checksum": existing.checksum,
                "is_duplicate": True,
                "url": existing_url,
                "name": existing.name,
                "size_bytes": existing.size_bytes,
                "mime_type": existing.mime_type,
                "document": _serialize_document(existing),
            }
            return Response(payload, status=status.HTTP_200_OK)

        # Write file to disk — Alice moves to cloud library later
        storage = _build_storage_path(filename)
        os.makedirs(os.path.dirname(storage["full"]), exist_ok=True)
        upload.seek(0)
        with open(storage["full"], "wb") as f:
            for chunk in upload.chunks():
                f.write(chunk)

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

        url = f"/wcapi/document/placeholder/"  # updated after create
        config_data = {
            "parent_model": model_name or "",
            "parent_id": parent_id,
            "role": purpose,
            "purpose": purpose,
        }

        doc = Document.objects.create(
            name=filename,
            description=description,
            mime_type=mime_type,
            size_bytes=upload.size,
            path={"storage": "local", "key": storage["key"], "url": "", "full": storage["full"]},
            checksum=checksum,
            purpose=purpose,
            config=config_data,
            metadata=metadata,
        )

        url = f"/wcapi/document/{doc.id}/"
        doc.path["url"] = url
        doc.save(update_fields=["path"])

        geo_data = (metadata.get("address", {}).get("geo", {})) if metadata else {}
        payload = {
            "document_id": doc.id,
            "path": storage["key"],
            "checksum": checksum,
            "is_duplicate": False,
            "url": url,
            "name": doc.name,
            "size_bytes": doc.size_bytes,
            "mime_type": doc.mime_type,
            "purpose": purpose,
            "description": description,
            "has_geo": bool(geo_data.get("lat")),
            "geo_lat": geo_data.get("lat"),
            "geo_lng": geo_data.get("lng"),
            "document": _serialize_document(doc),
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class DocumentDownloadView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id: int):
        doc = Document.objects.filter(pk=document_id).first()
        if not doc:
            raise Http404("document not found")

        inline_bytes = _decode_inline_content(doc)
        if inline_bytes is not None:
            doc.increment_access()
            response = HttpResponse(inline_bytes, content_type=doc.mime_type or "application/octet-stream")
            if doc.name:
                response["Content-Disposition"] = f'inline; filename="{doc.name}"'
            return response

        path = (doc.path or {}) if isinstance(doc.path, dict) else {}
        full_path = path.get("full")
        if not full_path or not os.path.exists(full_path):
            raise Http404("file not found")
        doc.increment_access()
        return FileResponse(open(full_path, "rb"), as_attachment=False, filename=doc.name or None)


class DocumentDeleteView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

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
