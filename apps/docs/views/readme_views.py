from hashlib import sha1
from email.utils import parsedate_to_datetime, format_datetime
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.docs.models import Document


class ReadmeDetailView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ["get", "options", "head"]

    def get(self, request, slug: str, *args, **kwargs):
        doc = Document.objects.get(model_name="readme", slug=slug)

        # Compute ETag and Last-Modified
        content_basis = (getattr(doc, "html", "") or "") + (getattr(doc, "body", "") or "") + str(getattr(doc, "version", "")) + str(doc.pk)
        etag = f'W/"{sha1(content_basis.encode("utf-8")).hexdigest()}"'
        last_modified = getattr(doc, "dt_modified", None) or getattr(doc, "updated_at", None) or timezone.now()
        if timezone.is_naive(last_modified):
            last_modified = timezone.make_aware(last_modified, timezone=timezone.utc)
        last_modified = last_modified.astimezone(timezone.utc).replace(microsecond=0)
        last_modified_http = format_datetime(last_modified, usegmt=True)

        # ETag conditional
        inm = request.META.get("HTTP_IF_NONE_MATCH")
        if inm and inm.strip() == etag:
            resp = Response(status=304)
            resp["ETag"] = etag
            resp["Last-Modified"] = last_modified_http
            return resp

        # If-Modified-Since conditional
        ims_raw = request.META.get("HTTP_IF_MODIFIED_SINCE")
        if ims_raw:
            try:
                ims = parsedate_to_datetime(ims_raw)
                if ims.tzinfo is None:
                    ims = timezone.make_aware(ims, timezone=timezone.utc)
                ims = ims.astimezone(timezone.utc).replace(microsecond=0)
                if last_modified <= ims:
                    resp = Response(status=304)
                    resp["ETag"] = etag
                    resp["Last-Modified"] = last_modified_http
                    return resp
            except Exception:
                pass

        # Build payload
        payload = {"slug": doc.slug}
        html = getattr(doc, "html", None)
        if html is not None:
            payload["html"] = html
            payload["body"] = getattr(doc, "body", "")
        else:
            payload["body"] = getattr(doc, "body", "")

        resp = Response(data=payload, status=200)
        resp["ETag"] = etag
        resp["Last-Modified"] = last_modified_http
        return resp