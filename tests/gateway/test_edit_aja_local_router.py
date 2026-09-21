"""Tests for Edit Aja's local-first Telegram control/status layer."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from gateway.edit_aja_local import (
    api_status,
    apply_quiet_mode,
    compact_status,
    local_intent,
    local_reply,
    model_status,
)
from gateway.slash_commands_status import GatewayStatusCommandsMixin


def _config():
    return {
        "edit_aja": {"enabled": True, "quiet_mode": True},
        "model": {
            "provider": "gemini",
            "default": "gemini-3.7-flash",
        },
        "auxiliary": {
            "compression": {
                "provider": "main",
                "model": "gemini-3.5-flash-lite",
            }
        },
    }


def test_local_intent_is_conservative():
    assert local_intent("model yang kamu pakai apa?") == "model"
    assert local_intent("api saya ada berapa?") == "api"
    assert local_intent("gateway hidup?") == "status"
    assert local_intent("/model") is None
    assert local_intent("jelaskan cara kerja Gemini API") is None
    assert local_intent("buat analisis model video ini secara detail") is None


def test_model_and_compact_status_are_local_and_specific(monkeypatch):
    monkeypatch.setattr(
        "gateway.edit_aja_local.api_snapshot",
        lambda _cfg=None: {
            "rows": [],
            "total": 2,
            "ready": 2,
            "cooldown": 0,
            "dead": 0,
            "preferred": "Gemini 01",
        },
    )
    cfg = _config()

    model = model_status(cfg)
    assert "gemini-3.7-flash" in model
    assert "gemini-3.5-flash-lite" in model
    assert "gemini" in model.lower()

    status = compact_status(cfg)
    assert "Gateway: **ONLINE**" in status
    assert "Gemini keys: **2**" in status
    assert "Quiet mode: **ON**" in status


def test_api_status_reports_pool_health_without_secrets_or_fake_percent(monkeypatch):
    now = time.time()
    entries = [
        SimpleNamespace(
            label="Gemini 01",
            priority=0,
            last_status="ok",
            last_error_reset_at=None,
            model_cooldowns={},
            request_count=5,
            access_token="secret-one",
        ),
        SimpleNamespace(
            label="Gemini 02",
            priority=1,
            last_status="exhausted",
            last_error_reset_at=now + 600,
            model_cooldowns={},
            request_count=2,
            access_token="secret-two",
        ),
    ]

    class FakePool:
        def entries(self):
            return list(entries)

    monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: FakePool())

    text = api_status(_config())

    assert "Keys: **2**" in text
    assert "Gemini 01: **READY**" in text
    assert "Gemini 02: **COOLDOWN**" in text
    assert "not available reliably" in text
    assert "secret-one" not in text
    assert "secret-two" not in text
    assert "50%" not in text
    assert "Preferred next key: **Gemini 01**" in text


def test_quiet_mode_configures_telegram_final_answer_first():
    cfg = apply_quiet_mode(_config(), True)
    telegram = cfg["display"]["platforms"]["telegram"]

    assert cfg["edit_aja"]["enabled"] is True
    assert cfg["edit_aja"]["quiet_mode"] is True
    assert cfg["display"]["tool_progress_command"] is True
    assert telegram["tool_progress"] == "off"
    assert telegram["interim_assistant_messages"] is False
    assert telegram["long_running_notifications"] is False
    assert telegram["busy_ack_enabled"] is False
    assert telegram["busy_ack_detail"] is False
    assert telegram["busy_steer_ack_enabled"] is False

    debug = apply_quiet_mode(cfg, False)
    telegram_debug = debug["display"]["platforms"]["telegram"]
    assert debug["edit_aja"]["quiet_mode"] is False
    assert telegram_debug["tool_progress"] == "all"
    assert telegram_debug["interim_assistant_messages"] is True
    assert telegram_debug["busy_ack_enabled"] is True


def test_local_reply_requires_edit_aja_marker(monkeypatch):
    monkeypatch.setattr(
        "gateway.edit_aja_local.api_snapshot",
        lambda _cfg=None: {
            "rows": [],
            "total": 2,
            "ready": 2,
            "cooldown": 0,
            "dead": 0,
            "preferred": "Gemini 01",
        },
    )
    assert local_reply("model yang kamu pakai apa?", {}) is None
    assert "gemini-3.7-flash" in local_reply("model yang kamu pakai apa?", _config())
    assert "Gemini keys: **2**" in local_reply("agent hidup?", _config())


@pytest.mark.asyncio
async def test_edit_aja_status_handler_returns_before_session_or_llm(monkeypatch):
    cfg = _config()
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: cfg)
    monkeypatch.setattr(
        "gateway.edit_aja_local.api_snapshot",
        lambda _cfg=None: {
            "rows": [],
            "total": 2,
            "ready": 2,
            "cooldown": 0,
            "dead": 0,
            "preferred": "Gemini 01",
        },
    )

    runner = object.__new__(GatewayStatusCommandsMixin)
    # Deliberately do not attach async_session_store. The Edit Aja fast path must
    # return before upstream session/agent code is touched.
    result = await runner._handle_status_command(SimpleNamespace())

    assert "EDIT AJA AI AGENT" in result
    assert "gemini-3.7-flash" in result
