"""Edit Aja Gemini-only configuration tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from hermes_cli.edit_aja_mode import (
    DEFAULT_LIGHT_MODEL,
    DEFAULT_MAIN_MODEL,
    GEMINI_BASE_URL,
    build_edit_aja_gemini_config,
)
from hermes_cli.model_setup_flows import _gemini_tier_ok


def test_edit_aja_profile_forces_gemini_and_disables_other_cloud_fallbacks():
    original = {
        "model": {
            "provider": "openrouter",
            "default": "some-model",
            "base_url": "https://old.example/v1",
            "api_key": "must-not-survive",
            "api_mode": "chat_completions",
        },
        "fallback_providers": [
            {"provider": "openrouter", "model": "fallback-model"},
        ],
        "auxiliary": {
            "vision": {
                "provider": "openrouter",
                "model": "old-vision",
                "api_key": "inline-secret",
                "fallback_chain": [{"provider": "nous"}],
            },
        },
        "credential_pool_strategies": {"anthropic": "least_used"},
    }

    cfg = build_edit_aja_gemini_config(original)

    assert cfg["model"]["provider"] == "gemini"
    assert cfg["model"]["default"] == DEFAULT_MAIN_MODEL
    assert cfg["model"]["base_url"] == GEMINI_BASE_URL
    assert "api_key" not in cfg["model"]
    assert "api_mode" not in cfg["model"]
    assert cfg["fallback_providers"] == []

    assert cfg["auxiliary"]["vision"]["provider"] == "main"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_MAIN_MODEL
    assert "api_key" not in cfg["auxiliary"]["vision"]
    assert "fallback_chain" not in cfg["auxiliary"]["vision"]

    assert cfg["auxiliary"]["compression"]["provider"] == "main"
    assert cfg["auxiliary"]["compression"]["model"] == DEFAULT_LIGHT_MODEL
    assert cfg["credential_pool_strategies"]["gemini"] == "fill_first"
    assert cfg["credential_pool_strategies"]["anthropic"] == "least_used"

    # Input is not mutated.
    assert original["model"]["provider"] == "openrouter"
    assert original["fallback_providers"]


def test_custom_model_choices_stay_on_gemini():
    cfg = build_edit_aja_gemini_config(
        {},
        main_model="gemini-main-test",
        light_model="gemini-light-test",
    )
    assert cfg["model"]["default"] == "gemini-main-test"
    assert cfg["auxiliary"]["vision"]["model"] == "gemini-main-test"
    assert cfg["auxiliary"]["compression"]["model"] == "gemini-light-test"
    assert all(
        block["provider"] == "main"
        for block in cfg["auxiliary"].values()
        if isinstance(block, dict)
    )


def test_free_tier_probe_is_informational_not_a_setup_block(capsys):
    provider = SimpleNamespace(inference_base_url=GEMINI_BASE_URL)
    with (
        patch("agent.gemini_native_adapter.probe_gemini_tier", return_value="free"),
        patch("hermes_cli.model_setup_flows._env_base_url", return_value=""),
    ):
        assert _gemini_tier_ok("test-key", provider, "GEMINI_BASE_URL") is True

    output = capsys.readouterr().out.lower()
    assert "free tier detected" in output
    assert "billing is not required" in output
    assert "not saving gemini" not in output
