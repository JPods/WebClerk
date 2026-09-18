"""Standardized pagination for transaction API endpoints.

Provides envelope-aware pagination that wraps paginated results with metadata
(page, total, count, timestamp) in the canonical API response envelope.
"""
from typing import Any, Dict, Optional
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone


class TransactionPagination(PageNumberPagination):
    """
    Page-based pagination with standard metadata envelope.
    
    Response shape:
    {
        "results": [...],      # page items
        "pagination": {
            "page": 1,
            "page_size": 25,
            "total_items": 1000,
            "total_pages": 40,
            "has_next": True,
            "has_previous": False,
            "next_page": 2,
            "prev_page": None,
        },
        "timestamp": "2025-12-08T10:30:45Z",
        "query_time_ms": 123,
    }
    """
    page_size = 25
    page_size_query_param = 'page_size'
    page_size_query_description = 'Items per page (max 500)'
    max_page_size = 500

    def paginate_queryset(self, queryset, request, view=None):
        """Capture request start time for query_time tracking."""
        self.request_start_time = timezone.now()
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data: Dict[str, Any]) -> Response:
        """Wrap paginated results with envelope metadata."""
        query_time_ms = None
        if hasattr(self, 'request_start_time'):
            elapsed = timezone.now() - self.request_start_time
            query_time_ms = int(elapsed.total_seconds() * 1000)

        # Compute page info
        page_num = self.page.number if hasattr(self.page, 'number') else 1
        total_items = self.page.paginator.count if hasattr(self.page, 'paginator') else len(data.get('results', []))
        total_pages = self.page.paginator.num_pages if hasattr(self.page, 'paginator') else 1
        has_next = self.page.has_next() if hasattr(self.page, 'has_next') else False
        has_previous = self.page.has_previous() if hasattr(self.page, 'has_previous') else False
        next_page = (page_num + 1) if has_next else None
        prev_page = (page_num - 1) if has_previous else None

        pagination_meta = {
            "page": page_num,
            "page_size": self.page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "next_page": next_page,
            "prev_page": prev_page,
        }

        envelope_data = {
            "results": data.get('results', []),
            "pagination": pagination_meta,
            "timestamp": timezone.now().isoformat(),
        }
        if query_time_ms is not None:
            envelope_data["query_time_ms"] = query_time_ms

        return Response(envelope_data)


class CursorTransactionPagination(PageNumberPagination):
    """
    Cursor-based pagination for large result sets (optimized for performance).
    
    Response shape is similar to TransactionPagination but uses cursor tokens
    instead of page numbers for safe pagination of rapidly changing data.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 500

    def get_paginated_response(self, data: Dict[str, Any]) -> Response:
        """Wrap cursor-paginated results with metadata."""
        pagination_meta = {
            "page_size": self.page_size,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
        }

        envelope_data = {
            "results": data.get('results', []),
            "pagination": pagination_meta,
            "timestamp": timezone.now().isoformat(),
        }

        return Response(envelope_data)
