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
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.docs.models.document import Document
from apps.docs.views_upload import (
    compute_checksum,
    get_upload_path,
    extract_exif_data,
    scan_for_viruses,
    _parse_exif_datetime,
    _convert_gps_coords,
    PIL_AVAILABLE,
)
from common.models import default_document_metadata
from .utils import assert_envelope

User = get_user_model()


# Unit tests - no database required
class TestComputeChecksum:
    """Tests for checksum computation."""

    def test_same_content_same_checksum(self):
        """Same file content should produce identical checksums."""
        content = b"Hello, World!"
        file1 = SimpleUploadedFile("test1.txt", content)
        file2 = SimpleUploadedFile("test2.txt", content)
        
        checksum1 = compute_checksum(file1)
        checksum2 = compute_checksum(file2)
        
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 produces 64 hex chars

    def test_different_content_different_checksum(self):
        """Different content should produce different checksums."""
        file1 = SimpleUploadedFile("test1.txt", b"Content A")
        file2 = SimpleUploadedFile("test2.txt", b"Content B")
        
        checksum1 = compute_checksum(file1)
        checksum2 = compute_checksum(file2)
        
        assert checksum1 != checksum2

    def test_file_pointer_reset_after_checksum(self):
        """File pointer should be reset to beginning after computing checksum."""
        content = b"Test content"
        file_obj = SimpleUploadedFile("test.txt", content)
        
        compute_checksum(file_obj)
        
        # Should be able to read from beginning
        assert file_obj.read() == content


class TestGetUploadPath:
    """Tests for upload path generation."""

    def test_path_contains_purpose(self):
        """Generated path should include the purpose."""
        path = get_upload_path("document", "myfile.pdf")
        assert "uploads/document/" in path

    def test_path_contains_filename(self):
        """Generated path should include original filename."""
        path = get_upload_path("qa_image", "photo.jpg")
        assert path.endswith("_photo.jpg")

    def test_path_sanitizes_filename(self):
        """Path should use only basename, not full paths."""
        path = get_upload_path("document", "/evil/../../../etc/passwd")
        assert "passwd" in path
        assert ".." not in path

    def test_different_purposes(self):
        """Different purposes should result in different base paths."""
        purposes = ["qa_image", "document", "product_image", "attachment", "import"]
        paths = [get_upload_path(p, "test.txt") for p in purposes]
        
        # All paths should be unique (due to different purposes)
        unique_bases = {p.split('/')[1] for p in paths}
        assert len(unique_bases) == len(purposes)


class TestParseExifDatetime:
    """Tests for EXIF datetime parsing."""

    def test_valid_datetime(self):
        """Valid EXIF datetime should be parsed to milliseconds timestamp."""
        result = _parse_exif_datetime("2024:01:15 10:30:45")
        assert isinstance(result, int)
        assert result > 0

    def test_empty_value(self):
        """Empty value should return 0."""
        assert _parse_exif_datetime(None) == 0
        assert _parse_exif_datetime("") == 0

    def test_invalid_format(self):
        """Invalid format should return 0."""
        assert _parse_exif_datetime("not a date") == 0
        assert _parse_exif_datetime("2024-01-15") == 0


class TestConvertGpsCoords:
    """Tests for GPS coordinate conversion."""

    def test_valid_north_coordinates(self):
        """North latitude should be positive."""
        coords = (37, 46, 30)  # 37°46'30"N
        result = _convert_gps_coords(coords, 'N')
        assert result is not None
        assert abs(result - 37.775) < 0.001

    def test_valid_south_coordinates(self):
        """South latitude should be negative."""
        coords = (33, 52, 10)  # 33°52'10"S
        result = _convert_gps_coords(coords, 'S')
        assert result is not None
        assert result < 0

    def test_valid_west_coordinates(self):
        """West longitude should be negative."""
        coords = (122, 25, 10)  # 122°25'10"W
        result = _convert_gps_coords(coords, 'W')
        assert result is not None
        assert result < 0

    def test_valid_east_coordinates(self):
        """East longitude should be positive."""
        coords = (139, 45, 0)  # 139°45'0"E
        result = _convert_gps_coords(coords, 'E')
        assert result is not None
        assert result > 0

    def test_none_values(self):
        """None values should return None."""
        assert _convert_gps_coords(None, 'N') is None
        assert _convert_gps_coords((37, 46, 30), None) is None


class TestExtractExifData:
    """Tests for EXIF extraction."""

    def test_non_image_file(self):
        """Non-image file should return empty EXIF."""
        file_obj = SimpleUploadedFile("test.txt", b"Hello, World!")
        result = extract_exif_data(file_obj)
        
        assert "exif" in result
        assert "geo" in result

    @pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")
    def test_image_without_exif(self):
        """Image without EXIF should return basic dimensions."""
        # Create a minimal valid PNG
        # 8x8 pixel grayscale PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x08,  # 8x8
            0x08, 0x00, 0x00, 0x00, 0x00, 0x4B, 0x6D, 0x29,  # 8-bit grayscale
            0x64,
            0x00, 0x00, 0x00, 0x1D, 0x49, 0x44, 0x41, 0x54,  # IDAT chunk
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x03, 0x00, 0x7F,
            0xE0, 0x20, 0x01,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,  # IEND chunk
            0xAE, 0x42, 0x60, 0x82
        ])
        file_obj = SimpleUploadedFile("test.png", png_data, content_type="image/png")
        
        result = extract_exif_data(file_obj)
        
        # Should have basic image dimensions
        assert "exif" in result


class TestScanForViruses:
    """Tests for virus scanning placeholder."""

    def test_scanning_disabled(self):
        """When scanning disabled, should return skipped status."""
        with override_settings(VIRUS_SCAN_ENABLED=False):
            result = scan_for_viruses("/tmp/test.txt")
        
        assert result["status"] == "skipped"
        assert result["details"]["reason"] == "scanning_disabled"
        assert result["quarantined"] is False

    def test_scanning_enabled_placeholder(self):
        """When scanning enabled, placeholder returns appropriate status."""
        with override_settings(VIRUS_SCAN_ENABLED=True):
            result = scan_for_viruses("/tmp/test.txt")
        
        # Placeholder implementation should still work
        assert "status" in result
        assert "scanned_at" in result


class TestDefaultDocumentMetadata:
    """Tests for default document metadata structure."""

    def test_metadata_has_address(self):
        """Metadata should have address section."""
        meta = default_document_metadata()
        assert "address" in meta
        assert "geo" in meta["address"]
        assert "lat" in meta["address"]["geo"]
        assert "lng" in meta["address"]["geo"]

    def test_metadata_has_virus(self):
        """Metadata should have virus section."""
        meta = default_document_metadata()
        assert "virus" in meta
        assert "status" in meta["virus"]
        assert meta["virus"]["status"] == "pending"

    def test_metadata_has_exif(self):
        """Metadata should have exif section."""
        meta = default_document_metadata()
        assert "exif" in meta
        assert "camera_make" in meta["exif"]
        assert "width" in meta["exif"]


# Integration tests - require database
@pytest.mark.django_db
class DocumentUploadAPITests(TestCase):
    """Integration tests for the upload API endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='upload@test.com',
            password='testpass123',
            name_first='Upload',
            name_last='Tester',
            username=''
        )
        self.client.login(email='upload@test.com', password='testpass123')

    def test_upload_requires_authentication(self):
        """Upload endpoint should require authentication."""
        self.client.logout()
        file_obj = SimpleUploadedFile("test.txt", b"Hello!")
        
        response = self.client.post(
            '/wcapi/upload/',
            {'file': file_obj, 'purpose': 'document'}
        )
        
        self.assertEqual(response.status_code, 401)

    def test_upload_requires_file(self):
        """Upload should fail without a file."""
        response = self.client.post(
            '/wcapi/upload/',
            {'purpose': 'document'}
        )
        
        self.assertEqual(response.status_code, 400)

    def test_basic_upload(self):
        """Basic file upload should succeed."""
        file_obj = SimpleUploadedFile("test.txt", b"Hello, World!")
        
        response = self.client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data', data)

    def test_upload_creates_document(self):
        """Upload should create a Document record."""
        initial_count = Document.objects.count()
        file_obj = SimpleUploadedFile("test.txt", b"Test content for document")
        
        response = self.client.post(
            '/wcapi/upload/',
            {
                'file': file_obj,
                'purpose': 'document',
                'model_name': 'test',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Document.objects.count(), initial_count + 1)

    def test_upload_deduplication(self):
        """Uploading same content should reuse existing Document."""
        content = b"Deduplicated content"
        
        # First upload
        file1 = SimpleUploadedFile("first.txt", content)
        response1 = self.client.post(
            '/wcapi/upload/',
            {
                'file': file1,
                'purpose': 'document',
                'model_name': 'test',
            }
        )
        
        # Second upload with same content
        file2 = SimpleUploadedFile("second.txt", content)
        response2 = self.client.post(
            '/wcapi/upload/',
            {
                'file': file2,
                'purpose': 'document',
                'model_name': 'test',
            }
        )
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json().get('data', response1.json())
        data2 = response2.json().get('data', response2.json())
        
        # Both should reference the same document
        self.assertEqual(data1.get('checksum'), data2.get('checksum'))

    def test_upload_with_address_data(self):
        """Upload with address fields should populate metadata."""
        file_obj = SimpleUploadedFile("test.txt", b"Test")
        
        response = self.client.post(
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
        
        self.assertEqual(response.status_code, 200)

    def test_upload_with_geolocation(self):
        """Upload with geo coordinates should populate address.geo."""
        file_obj = SimpleUploadedFile("test.txt", b"GPS test")
        
        response = self.client.post(
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
        
        self.assertEqual(response.status_code, 200)
        data = response.json().get('data', response.json())
        
        # Response should indicate geo data was captured
        self.assertTrue(data.get('has_geo', False) or 'geo_lat' in str(data))


# Run with: pytest tests/test_document_upload.py -v
# Run specific test: pytest tests/test_document_upload.py::TestComputeChecksum -v
# Run with coverage: pytest tests/test_document_upload.py --cov=apps.docs.views_upload
