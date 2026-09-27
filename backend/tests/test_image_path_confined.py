"""Fable, 2026-09-27: the image URL is unauthenticated; its model and ida must not leave the image root."""
from apps.core.services import resolve_image


def test_dot_dot_never_leaves_the_image_root(tmp_path, monkeypatch):
    root = tmp_path / 'images'
    (root / 'item' / 'A1').mkdir(parents=True)
    (root / 'item' / 'A1' / 'tn.jpg').write_bytes(b'inside')
    (tmp_path / 'tn.jpg').write_bytes(b'outside')
    monkeypatch.setattr(resolve_image, 'get_image_root', lambda: root)
    assert resolve_image._check_local('item', 'A1', 'tn.jpg')['bytes'] == b'inside'
    assert resolve_image._check_local('..', '.', 'tn.jpg') is None
