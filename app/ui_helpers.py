"""UI helpers for artifact display in Streamlit."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import streamlit as st

MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".json": "application/json",
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_PREVIEW_SUFFIXES = {".txt", ".md", ".json"}

PreviewContext = Literal["chat", "sidebar_qr", "sidebar_qr_list", "sidebar_file"]

CHAT_QR_WIDTH = 280
CHAT_IMAGE_WIDTH = 420
SIDEBAR_QR_WIDTH = 180
SIDEBAR_QR_LIST_WIDTH = 200


def get_mime_type(suffix: str) -> str:
    return MIME_TYPES.get(suffix.lower(), "application/octet-stream")


def is_qr_artifact(path: Path, qr_codes_dir: Path | None = None) -> bool:
    if qr_codes_dir is None:
        return "qr" in path.name.lower() and path.suffix.lower() == ".png"
    try:
        return path.resolve().parent == qr_codes_dir.resolve()
    except OSError:
        return False


def image_preview_width(
    path: Path,
    preview_context: PreviewContext = "chat",
    qr_codes_dir: Path | None = None,
) -> int:
    if is_qr_artifact(path, qr_codes_dir):
        if preview_context == "sidebar_qr":
            return SIDEBAR_QR_WIDTH
        if preview_context in {"sidebar_qr_list", "sidebar_file"}:
            return SIDEBAR_QR_LIST_WIDTH
        return CHAT_QR_WIDTH
    return CHAT_IMAGE_WIDTH


def _iter_artifact_paths(files_dir: Path, qr_codes_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (files_dir, qr_codes_dir):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                paths.append(path)
    return paths


def _file_info(path: Path, project_root: Path) -> dict[str, Any]:
    stat = path.stat()
    rel_path = path.relative_to(project_root).as_posix()
    return {
        "path": path,
        "rel_path": rel_path,
        "name": path.name,
        "suffix": path.suffix.lower(),
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def list_artifacts(
    files_dir: Path,
    qr_codes_dir: Path,
    project_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return current artifact files from data/files and data/qr_codes."""
    root = project_root or files_dir.parent.parent
    artifacts: dict[str, dict[str, Any]] = {}
    for path in _iter_artifact_paths(files_dir, qr_codes_dir):
        info = _file_info(path, root)
        artifacts[info["rel_path"]] = info
    return artifacts


def snapshot_artifacts(
    files_dir: Path,
    qr_codes_dir: Path,
    project_root: Path | None = None,
) -> dict[str, tuple[float, int]]:
    """Snapshot artifact mtimes and sizes for change detection."""
    snapshot: dict[str, tuple[float, int]] = {}
    for rel_path, info in list_artifacts(files_dir, qr_codes_dir, project_root).items():
        snapshot[rel_path] = (info["mtime"], info["size"])
    return snapshot


def get_changed_artifacts(
    before_snapshot: dict[str, tuple[float, int]],
    after_snapshot: dict[str, tuple[float, int]],
) -> list[str]:
    """Return rel_paths of new or modified artifacts."""
    changed: list[str] = []
    for rel_path, after_meta in after_snapshot.items():
        before_meta = before_snapshot.get(rel_path)
        if before_meta is None or before_meta != after_meta:
            changed.append(rel_path)
    return sorted(changed)


def render_artifact(
    path: Path,
    key_prefix: str = "artifact",
    *,
    preview_context: PreviewContext = "chat",
    qr_codes_dir: Path | None = None,
) -> None:
    """Render artifact preview and download button in Streamlit."""
    suffix = path.suffix.lower()
    mime = get_mime_type(suffix)
    data = path.read_bytes()
    safe_key = key_prefix.replace("/", "_").replace("\\", "_")

    if suffix in IMAGE_SUFFIXES:
        width = image_preview_width(path, preview_context, qr_codes_dir)
        st.image(str(path), caption=path.name, width=width)
        st.download_button(
            label=f"Скачать {path.name}",
            data=data,
            file_name=path.name,
            mime=mime,
            key=f"{safe_key}_download_{path.name}",
        )
        return

    if suffix in TEXT_PREVIEW_SUFFIXES:
        st.download_button(
            label=f"Скачать {path.name}",
            data=data,
            file_name=path.name,
            mime=mime,
            key=f"{safe_key}_download_{path.name}",
        )
        preview_text = path.read_text(encoding="utf-8", errors="replace")
        with st.expander(f"Предпросмотр {path.name}", expanded=False):
            if suffix == ".json":
                st.code(preview_text, language="json")
            else:
                st.text(preview_text)
        return

    st.download_button(
        label=f"Скачать {path.name}",
        data=data,
        file_name=path.name,
        mime=mime,
        key=f"{safe_key}_download_{path.name}",
    )
