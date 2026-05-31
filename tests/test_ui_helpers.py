"""Tests for Streamlit UI artifact helpers."""

import time
from pathlib import Path

from app.ui_helpers import (
    CHAT_QR_WIDTH,
    SIDEBAR_QR_WIDTH,
    get_changed_artifacts,
    get_mime_type,
    image_preview_width,
    list_artifacts,
    snapshot_artifacts,
)


def test_list_artifacts_returns_file_metadata(tmp_path):
    files_dir = tmp_path / "data" / "files"
    qr_dir = tmp_path / "data" / "qr_codes"
    files_dir.mkdir(parents=True)
    qr_dir.mkdir(parents=True)

    demo_file = files_dir / "demo.txt"
    demo_file.write_text("hello", encoding="utf-8")
    qr_file = qr_dir / "demo.png"
    qr_file.write_bytes(b"\x89PNG")

    artifacts = list_artifacts(files_dir, qr_dir, tmp_path)
    assert set(artifacts) == {"data/files/demo.txt", "data/qr_codes/demo.png"}
    assert artifacts["data/files/demo.txt"]["name"] == "demo.txt"
    assert artifacts["data/files/demo.txt"]["suffix"] == ".txt"
    assert artifacts["data/files/demo.txt"]["size"] == 5


def test_get_changed_artifacts_detects_new_and_modified(tmp_path):
    files_dir = tmp_path / "data" / "files"
    qr_dir = tmp_path / "data" / "qr_codes"
    files_dir.mkdir(parents=True)
    qr_dir.mkdir(parents=True)

    before = snapshot_artifacts(files_dir, qr_dir, tmp_path)

    new_file = files_dir / "new.txt"
    new_file.write_text("one", encoding="utf-8")
    after_new = snapshot_artifacts(files_dir, qr_dir, tmp_path)
    assert get_changed_artifacts(before, after_new) == ["data/files/new.txt"]

    new_file.write_text("two", encoding="utf-8")
    time.sleep(0.01)
    after_modified = snapshot_artifacts(files_dir, qr_dir, tmp_path)
    changed = get_changed_artifacts(after_new, after_modified)
    assert changed == ["data/files/new.txt"]


def test_get_mime_type():
    assert get_mime_type(".png") == "image/png"
    assert get_mime_type(".txt") == "text/plain"
    assert get_mime_type(".json") == "application/json"
    assert get_mime_type(".bin") == "application/octet-stream"


def test_image_preview_width_for_qr(tmp_path):
    qr_dir = tmp_path / "data" / "qr_codes"
    qr_dir.mkdir(parents=True)
    qr_path = qr_dir / "github_qr.png"
    qr_path.write_bytes(b"\x89PNG")

    assert image_preview_width(qr_path, "chat", qr_dir) == CHAT_QR_WIDTH
    assert image_preview_width(qr_path, "sidebar_qr", qr_dir) == SIDEBAR_QR_WIDTH
