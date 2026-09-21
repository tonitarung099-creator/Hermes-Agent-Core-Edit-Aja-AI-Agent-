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
        "edit_aja": {
            "enabled": True,
            "quiet_mode": True,
            "ai_profile": "cerebras-free-cloud",
            "gemini_enabled": False,
        },
        "model": {
            "provider": "cerebras",
            "default": "gpt-oss-120b",
        },
        "fallback_providers": [
            {"provider": "cloudflare", "model": "@cf/zai-org/glm-4.7-flash"},
            {"provider": "groq", "model": "openai/gpt-oss-120b"},
        ],
    }


def _snapshot():
    return {
        "providers": [],
        "rows": [],
        "total": 3,
        "ready": 2,
        "cooldown": 1,
        "dead": 0,
    }


def test_local_intent_is_conservative():
    assert local_intent("model yang kamu pakai apa?") == "model"
    assert local_intent("api saya ada berapa?") == "api"
    assert local_intent("status api cerebras") == "api"
    assert local_intent("gateway hidup?") == "status"
    assert local_intent("/model") is None
    assert local_intent("jelaskan cara kerja Cerebras API") is None
    assert local_intent("buat analisis model video ini secara detail") is None


def test_model_and_compact_status_are_local_and_specific(monkeypatch):
    monkeypatch.setattr("gateway.edit_aja_local.api_snapshot", lambda _cfg=None: _snapshot())
    cfg = _config()

    model = model_status(cfg)
    assert "cerebras" in model.lower()
    assert "gpt-oss-120b" in model
    assert "cloudflare" in model.lower()
    assert "groq" in model.lower()
    assert "Gemini: **DISABLED**" in model

    status = compact_status(cfg)
    assert "Gateway: **ONLINE**" in status
    assert "API credentials: **3**" in status
    assert "Fallbacks: **cloudflare → groq**" in status
    assert "Gemini: **DISABLED**" in status
    assert "Quiet mode: **ON**" in status


def test_api_status_reports_all_route_pools_without_secrets_or_fake_percent(monkeypatch):
    now = time.time()
    pools = {
        "cerebras": [
            SimpleNamespace(
                label="Cerebras 01",
                priority=0,
                last_status="ok",
                last_error_reset_at=None,
                model_cooldowns={},
                request_count=5,
                access_token="secret-cerebras",
            )
        ],
        "cloudflare": [
            SimpleNamespace(
                label="Cloudflare 01",
                priority=0,
                last_status="exhausted",
                last_error_reset_at=now + 600,
                model_cooldowns={},
                request_count=2,
                access_token="secret-cloudflare",
            )
        ],
        "groq": [
            SimpleNamespace(
                label="Groq 01",
                priority=0,
                last_status="ok",
                last_error_reset_at=None,
                model_cooldowns={},
                request_count=1,
                access_token="secret-groq",
            )
        ],
    }

    class FakePool:
        def __init__(self, entries):
            self._entries = entries

        def entries(self):
            return list(self._entries)

    monkeypatch.setattr(
        "agent.credential_pool.load_pool",
        lambda provider: FakePool(pools.get(provider, [])),
    )

    text = api_status(_config())

    assert "Credentials: **3**" in text
    assert "Cerebras 01: **READY**" in text
    assert "Cloudflare 01: **COOLDOWN**" in text
    assert "Groq 01: **READY**" in text
    assert "secret-cerebras" not in text
    assert "secret-cloudflare" not in text
    assert "secret-groq" not in text
    assert "50%" not in text
    assert "never invents a percentage" in text


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
    monkeypatch.setattr("gateway.edit_aja_local.api_snapshot", lambda _cfg=None: _snapshot())

    assert local_reply("model yang kamu pakai apa?", {}) is None
    assert "gpt-oss-120b" in local_reply("model yang kamu pakai apa?", _config())
    assert "API credentials: **3**" in local_reply("agent hidup?", _config())


@pytest.mark.asyncio
async def test_edit_aja_status_handler_returns_before_session_or_llm(monkeypatch):
    cfg = _config()
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: cfg)
    monkeypatch.setattr("gateway.edit_aja_local.api_snapshot", lambda _cfg=None: _snapshot())

    runner = object.__new__(GatewayStatusCommandsMixin)
    result = await runner._handle_status_command(SimpleNamespace())

    assert "EDIT AJA AI AGENT" in result
    assert "gpt-oss-120b" in result
    assert "cerebras" in result.lower()
