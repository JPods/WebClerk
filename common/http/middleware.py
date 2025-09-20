from __future__ import annotations

import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

class ForceJSONResponses(MiddlewareMixin):
    """
    Ensure 403/404/405 are JSON and in our standard envelope.
    Preserve responses already in envelope format; enrich with error.code if missing.
    """
    MESSAGE_MAP = {
        403: "Forbidden",
        404: "Not found",
        405: "Method not allowed",
    }
    CODE_MAP = {
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
    }

    def process_response(self, request, response):
        code = getattr(response, "status_code", 200)
        if code not in self.MESSAGE_MAP:
            return response

        # Already enveloped? Keep it, but add error.code if missing.
        try:
            raw = (response.content or b"").decode()
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict) and "status" in data:
                if "error" not in data:
                    data["error"] = {"code": self.CODE_MAP.get(code)}
                    return JsonResponse(data, status=code)
                return response
        except Exception:
            pass

        payload = {
            "status": "fail",
            "message": self.MESSAGE_MAP[code],
            "data": None,
            "error": {"code": self.CODE_MAP[code]},
        }
        return JsonResponse(payload, status=code)


class Envelope404Middleware(MiddlewareMixin):
    """
    Fallback wrapper for any raw 404s that slip through.
    """
    def process_response(self, request, response):
        if getattr(response, "status_code", 200) != 404:
            return response
        try:
            raw = (response.content or b"").decode()
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict) and "status" in data:
                if "error" not in data:
                    data["error"] = {"code": "not_found"}
                    return JsonResponse(data, status=404)
                return response
        except Exception:
            pass
        return JsonResponse(
            {"status": "fail", "message": "Not found", "data": None, "error": {"code": "not_found"}},
            status=404,
        )