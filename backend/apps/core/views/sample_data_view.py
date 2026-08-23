"""
Sample data endpoint for report parade onboarding.

GET /wcapi/sample-data/?model=invoice
GET /wcapi/sample-data/          (returns index)

Serves polished JSON files from apps/core/sample_data/.
These are curated, proven sample records that make reports
render with realistic data during onboarding — before the
user has their own data.

Future: WC_HQ serves these same files via API. For now,
local JSON is the source of truth.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api_responses import api_response

logger = logging.getLogger(__name__)

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"


class SampleDataView(APIView):
    """Serve sample data for report parade onboarding."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        model_name = request.query_params.get("model", "").strip().lower()

        if not model_name:
            # Return the index
            index_path = SAMPLE_DATA_DIR / "_index.json"
            if not index_path.exists():
                return api_response(
                    success=False, status_code=404,
                    message="Sample data index not found",
                )
            return api_response(
                success=True,
                data=json.loads(index_path.read_text()),
            )

        # Serve a specific model's sample data
        file_path = SAMPLE_DATA_DIR / f"{model_name}.json"
        if not file_path.exists():
            return api_response(
                success=False, status_code=404,
                message=f"No sample data for model: {model_name}",
            )

        data = json.loads(file_path.read_text())
        # Strip internal _meta from response
        data.pop("_meta", None)
        return api_response(success=True, data=data)
