"""Streamlit web UI for the local AI agent toolbox."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from agent.agent import ask_agent
from agent.logging_config import LOG_FILE, setup_logging
from agent.memory import clear_memory, summarize_memory_for_prompt
from agent.tool_catalog import DEMO_PROMPTS_RU, TOOL_CATALOG
from app.ui_helpers import (
    SIDEBAR_QR_WIDTH,
    get_changed_artifacts,
    list_artifacts,
    render_artifact,
    snapshot_artifacts,
)

setup_logging()

FILES_DIR = PROJECT_ROOT / "data" / "files"
QR_CODES_DIR = PROJECT_ROOT / "data" / "qr_codes"


def _read_log_tail(lines: int = 40) -> str:
    if not LOG_FILE.exists():
        return "Файл agent.log пока пуст."
    content = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def _latest_qr_image() -> Path | None:
    if not QR_CODES_DIR.exists():
        return None
    png_files = sorted(QR_CODES_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return png_files[0] if png_files else None


def _render_message_artifacts(artifact_paths: list[str], key_prefix: str) -> None:
    if not artifact_paths:
        return
    st.markdown("**📎 Артефакты этого запроса**")
    artifacts = list_artifacts(FILES_DIR, QR_CODES_DIR, PROJECT_ROOT)
    for rel_path in artifact_paths:
        info = artifacts.get(rel_path)
        if info is None:
            continue
        render_artifact(
            info["path"],
            key_prefix=f"{key_prefix}_{rel_path}",
            preview_context="chat",
            qr_codes_dir=QR_CODES_DIR,
        )


def _render_chat_message(message: dict, index: int) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            _render_message_artifacts(
                message.get("artifacts", []),
                key_prefix=f"chat_{index}",
            )


def _render_sidebar_files() -> None:
    artifacts = list_artifacts(FILES_DIR, QR_CODES_DIR, PROJECT_ROOT)
    file_items = sorted(
        (info for info in artifacts.values() if info["path"].parent == FILES_DIR),
        key=lambda item: item["name"],
    )
    if not file_items:
        st.caption("(пусто)")
        return
    for info in file_items:
        st.markdown(f"**{info['name']}**")
        render_artifact(
            info["path"],
            key_prefix=f"sidebar_file_{info['rel_path']}",
            preview_context="sidebar_file",
            qr_codes_dir=QR_CODES_DIR,
        )


def _render_sidebar_qr_codes() -> None:
    artifacts = list_artifacts(FILES_DIR, QR_CODES_DIR, PROJECT_ROOT)
    qr_items = sorted(
        (info for info in artifacts.values() if info["path"].parent == QR_CODES_DIR),
        key=lambda item: item["name"],
    )
    latest_qr = _latest_qr_image()
    if latest_qr:
        st.image(
            str(latest_qr),
            caption=f"Последний QR: {latest_qr.name}",
            width=SIDEBAR_QR_WIDTH,
        )

    if not qr_items:
        st.caption("(пусто)")
        return

    for info in qr_items:
        st.markdown(f"**{info['name']}**")
        render_artifact(
            info["path"],
            key_prefix=f"sidebar_qr_{info['rel_path']}",
            preview_context="sidebar_qr_list",
            qr_codes_dir=QR_CODES_DIR,
        )


st.set_page_config(page_title="Локальный AI-агент Toolbox", page_icon="🧰", layout="wide")

st.title("🧰 Локальный AI-агент Toolbox")
st.caption(
    "11 инструментов: поиск, погода, крипта, файлы, память, валюты, QR, "
    "напоминания, калькулятор, конвертер и статистика текста."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("🛠️ Инструменты")
    for tool in TOOL_CATALOG:
        st.markdown(f"**{tool['title_ru']}** (`{tool['name']}`)")
        st.caption(tool["description_ru"])

    st.divider()
    st.subheader("⚡ Демо-запросы")
    for prompt in DEMO_PROMPTS_RU:
        if st.button(prompt, use_container_width=True, key=f"demo_{hash(prompt)}"):
            st.session_state.pending_prompt = prompt

    st.divider()
    st.subheader("🧠 Память")
    st.text_area(
        "Последние записи",
        summarize_memory_for_prompt(limit=6),
        height=160,
        disabled=True,
        label_visibility="collapsed",
    )
    if st.button("Очистить память", use_container_width=True):
        clear_memory()
        st.success("Память очищена")
        st.rerun()

    st.divider()
    st.subheader("📁 Файлы")
    _render_sidebar_files()

    st.divider()
    st.subheader("🔳 QR-коды")
    _render_sidebar_qr_codes()

    st.divider()
    with st.expander("🧾 Технические логи", expanded=False):
        st.code(_read_log_tail(), language="text")

for index, message in enumerate(st.session_state.messages):
    _render_chat_message(message, index)

prompt = st.chat_input("Напиши задачу для агента…")
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    before_snapshot = snapshot_artifacts(FILES_DIR, QR_CODES_DIR, PROJECT_ROOT)

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Агент думает…"):
            try:
                response = ask_agent(prompt)
            except RuntimeError as exc:
                response = str(exc)
        st.markdown(response)

        after_snapshot = snapshot_artifacts(FILES_DIR, QR_CODES_DIR, PROJECT_ROOT)
        changed_artifacts = get_changed_artifacts(before_snapshot, after_snapshot)
        if changed_artifacts:
            _render_message_artifacts(changed_artifacts, key_prefix="live")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "artifacts": changed_artifacts,
        }
    )
    st.rerun()
