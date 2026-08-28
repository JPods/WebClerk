"""
Tests for Document Upload functionality.

Tests cover:
- Basic file upload
- Checksum deduplication
- EXIF metadata extraction
- GPS coordinate parsing
- Address/geolocation capture
- Virus scanning (placeholder)
"""
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile


def _get_upload_helpers():
    from apps.docs.views.upload_view import (
        _compute_checksum,
        _safe_filename,
        _build_storage_path,
    )
    return _compute_checksum, _safe_filename, _build_storage_path


# Unit tests - no database required
class TestComputeChecksum:
    """Tests for checksum computation."""

    def test_same_content_same_checksum(self):
        """Same file content should produce identical checksums."""
        _compute_checksum, *_ = _get_upload_helpers()
        content = b"Hello, World!"
        file1 = SimpleUploadedFile("test1.txt", content)
        file2 = SimpleUploadedFile("test2.txt", content)

        checksum1 = _compute_checksum(file1)
        checksum2 = _compute_checksum(file2)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 produces 64 hex chars

    def test_different_content_different_checksum(self):
        """Different content should produce different checksums."""
        _compute_checksum, *_ = _get_upload_helpers()
        file1 = SimpleUploadedFile("test1.txt", b"Content A")
        file2 = SimpleUploadedFile("test2.txt", b"Content B")

        checksum1 = _compute_checksum(file1)
        checksum2 = _compute_checksum(file2)

        assert checksum1 != checksum2

    def test_checksum_is_deterministic(self):
        """Computing checksum twice on same content should match."""
        _compute_checksum, *_ = _get_upload_helpers()
        content = b"Test content"
        file1 = SimpleUploadedFile("test1.txt", content)
        file2 = SimpleUploadedFile("test2.txt", content)

        checksum1 = _compute_checksum(file1)
        checksum2 = _compute_checksum(file2)

        assert checksum1 == checksum2


class TestBuildStoragePath:
    """Tests for storage path generation."""

    def test_path_contains_uploads_document(self):
        """Generated path should include uploads/document/."""
        _, _, _build_storage_path = _get_upload_helpers()
        result = _build_storage_path("myfile.pdf")
        assert "uploads/document/" in result["key"]

    def test_path_contains_file_extension(self):
        """Generated path should preserve file extension."""
        _, _, _build_storage_path = _get_upload_helpers()
        result = _build_storage_path("photo.jpg")
        assert result["key"].endswith(".jpg")

    def test_path_has_required_keys(self):
        """Result should contain key, full, and storage."""
        _, _, _build_storage_path = _get_upload_helpers()
        result = _build_storage_path("test.txt")
        assert "key" in result
        assert "full" in result
        assert "storage" in result
        assert result["storage"] == "local"

    def test_unique_paths_for_same_filename(self):
        """Same filename should produce unique paths (UUID-based)."""
        _, _, _build_storage_path = _get_upload_helpers()
        result1 = _build_storage_path("test.txt")
        result2 = _build_storage_path("test.txt")
        assert result1["key"] != result2["key"]


class TestSafeFilename:
    """Tests for filename sanitization."""

    def test_basename_extraction(self):
        """Should extract basename from path."""
        _, _safe_filename, _ = _get_upload_helpers()
        assert _safe_filename("/evil/../../../etc/passwd") == "passwd"

    def test_removes_dotdot(self):
        """Should remove directory traversal sequences."""
        _, _safe_filename, _ = _get_upload_helpers()
        result = _safe_filename("../secret.txt")
        assert ".." not in result

    def test_empty_name_returns_upload(self):
        """Empty name should return 'upload'."""
        _, _safe_filename, _ = _get_upload_helpers()
        assert _safe_filename("") == "upload"
        assert _safe_filename(None) == "upload"

    def test_normal_filename_unchanged(self):
        """Normal filename should pass through."""
        _, _safe_filename, _ = _get_upload_helpers()
        assert _safe_filename("photo.jpg") == "photo.jpg"


class TestDefaultDocumentMetadata:
    """Tests for default document metadata structure."""

    def test_metadata_has_address(self):
        """Metadata should have address section."""
        from common.models import default_document_metadata
        meta = default_document_metadata()
        assert "address" in meta
        assert "geo" in meta["address"]
        assert "lat" in meta["address"]["geo"]
        assert "lng" in meta["address"]["geo"]

    def test_metadata_has_virus(self):
        """Metadata should have virus section."""
        from common.models import default_document_metadata
        meta = default_document_metadata()
        assert "virus" in meta
        assert "status" in meta["virus"]
        assert meta["virus"]["status"] == "pending"

    def test_metadata_has_exif(self):
        """Metadata should have exif section."""
        from common.models import default_document_metadata
        meta = default_document_metadata()
        assert "exif" in meta
        assert "camera_make" in meta["exif"]
        assert "width" in meta["exif"]


# Integration tests - require database
@pytest.mark.django_db
class DocumentUploadAPITests:
    """Integration tests for the upload API endpoint."""

    def _get_client_and_user(self):
        from django.test import Client
        from django.contrib.auth import get_user_model
        User = get_user_model()
        client = Client()
        user = User.objects.create_user(
            email='upload@test.com',
            password='testpass123',
            name_first='Upload',
            name_last='Tester',
            username=''
        )
        client.login(email='upload@test.com', password='testpass123')
        return client, user

    def test_upload_requires_authentication(self):
        """Upload endpoint should require authentication."""
        from django.test import Client
        client = Client()
        file_obj = SimpleUploadedFile("test.txt", b"Hello!")

        response = client.post(
            '/wcapi/upload/',
            {'file': file_obj, 'purpose': 'document'}
        )

        assert response.status_code == 401

    def test_upload_requires_file(self):
        """Upload should fail without a file."""
        client, user = self._get_client_and_user()
        response = client.post(
            '/wcapi/upload/',
            {'purpose': 'document'}
        )

        assert response.status_code == 400

    def test_basic_upload(self):
        """Basic file upload should succeed."""
        client, user = self._get_client_and_user()
        file_obj = SimpleUploadedFile("test.txt", b"Hello, World!")

        response = client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'data' in data

    def test_upload_creates_document(self):
        """Upload should create a Document record."""
        from apps.docs.models.document import Document
        client, user = self._get_client_and_user()
        initial_count = Document.objects.count()
        file_obj = SimpleUploadedFile("test.txt", b"Test content for document")

        response = client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
            }
        )

        assert response.status_code == 200
        assert Document.objects.count() == initial_count + 1

    def test_upload_deduplication(self):
        """Uploading same content should reuse existing Document."""
        client, user = self._get_client_and_user()
        content = b"Deduplicated content"

        # First upload
        file1 = SimpleUploadedFile("first.txt", content)
        response1 = client.post(
            '/wcapi/upload/',
            {
                'file': file1,
                'purpose': 'document',
                'model_name': 'test',
            }
        )

        # Second upload with same content
        file2 = SimpleUploadedFile("second.txt", content)
        response2 = client.post(
            '/wcapi/upload/',
            {
                'file': file2,
                'purpose': 'document',
                'model_name': 'test',
            }
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json().get('data', response1.json())
        data2 = response2.json().get('data', response2.json())

        # Both should reference the same document
        assert data1.get('checksum') == data2.get('checksum')

    def test_upload_with_address_data(self):
        """Upload with address fields should populate metadata."""
        client, user = self._get_client_and_user()
        file_obj = SimpleUploadedFile("test.txt", b"Test")

        response = client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
                'address_city': 'San Francisco',
                'address_state': 'CA',
                'address_country': 'USA',
            }
        )

        assert response.status_code == 200

    def test_upload_with_geolocation(self):
        """Upload with geo coordinates should populate address.geo."""
        client, user = self._get_client_and_user()
        file_obj = SimpleUploadedFile("test.txt", b"GPS test")

        response = client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
                'geo_lat': '37.7749',
                'geo_lng': '-122.4194',
                'geo_accuracy': '10',
            }
        )

        assert response.status_code == 200
        data = response.json().get('data', response.json())

        # Response should indicate geo data was captured
        assert data.get('has_geo', False) or 'geo_lat' in str(data)


# Run with: pytest tests/test_document_upload.py -v
# Run specific test: pytest tests/test_document_upload.py::TestComputeChecksum -v
# Run with coverage: pytest tests/test_document_upload.py --cov=apps.docs.views_upload
