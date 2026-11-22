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
        """The key is the only path (no absolute 'full' to go stale when data/ moves)."""
        _, _, _build_storage_path = _get_upload_helpers()
        result = _build_storage_path("test.txt")
        assert "key" in result
        assert "full" not in result
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


# The upload endpoint itself is tested in tests/test_document_quarantine.py.


# Run with: pytest tests/test_document_upload.py -v
# Run specific test: pytest tests/test_document_upload.py::TestComputeChecksum -v
# Run with coverage: pytest tests/test_document_upload.py --cov=apps.docs.views_upload
