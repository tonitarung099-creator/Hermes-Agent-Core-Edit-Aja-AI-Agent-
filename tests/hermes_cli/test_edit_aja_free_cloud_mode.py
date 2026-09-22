"""Edit Aja recurring-free cloud configuration tests."""

from __future__ import annotations

from copy import deepcopy

from hermes_cli.edit_aja_mode import (
    CLOUDFLARE_BASE_URL_TEMPLATE,
    DEFAULT_CLOUDFLARE_MODEL,
    DEFAULT_CLOUDFLARE_VISION_MODEL,
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    build_edit_aja_free_cloud_config,
)


def test_recurring_free_profile_uses_cloudflare_then_groq_and_never_routes_to_gemini_or_cerebras():
    original = {
        "providers": {
            "cerebras": {
                "name": "Cerebras",
                "api": "https://api.cerebras.ai/v1",
                "default_model": "gpt-oss-120b",
            }
        },
        "model": {
            "provider": "gemini",
            "default": "gemini-old",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key": "must-not-survive",
            "api_mode": "chat_completions",
        },
        "fallback_providers": [
            {"provider": "gemini", "model": "gemini-fallback"},
            {"provider": "cerebras", "model": "gpt-oss-120b"},
        ],
        "fallback_model": {"provider": "gemini", "model": "legacy-gemini"},
        "auxiliary": {
            "vision": {
                "provider": "gemini",
                "model": "gemini-vision",
                "api_key": "inline-secret",
                "fallback_chain": [{"provider": "gemini", "model": "x"}],
            },
        },
        "credential_pool_strategies": {
            "gemini": "fill_first",
            "cerebras": "fill_first",
            "anthropic": "least_used",
        },
    }
    before = deepcopy(original)

    cfg = build_edit_aja_free_cloud_config(
        original,
        cloudflare_account_id="abcdef1234567890",
    )

    assert cfg["model"]["provider"] == "cloudflare"
    assert cfg["model"]["default"] == DEFAULT_CLOUDFLARE_MODEL
    assert "api_key" not in cfg["model"]
    assert "base_url" not in cfg["model"]
    assert "api_mode" not in cfg["model"]

    assert "cerebras" not in cfg["providers"]
    assert cfg["providers"]["cloudflare"]["api"] == (
        CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890")
    )
    assert cfg["providers"]["cloudflare"]["default_model"] == DEFAULT_CLOUDFLARE_MODEL
    assert DEFAULT_CLOUDFLARE_VISION_MODEL in cfg["providers"]["cloudflare"]["models"]
    assert cfg["providers"]["cloudflare"]["models"][DEFAULT_CLOUDFLARE_VISION_MODEL]["context_length"] == 256_000
    assert cfg["providers"]["groq"]["api"] == GROQ_BASE_URL
    assert cfg["providers"]["groq"]["default_model"] == DEFAULT_GROQ_MODEL

    assert cfg["fallback_providers"] == [
        {"provider": "groq", "model": DEFAULT_GROQ_MODEL},
    ]
    assert "fallback_model" not in cfg
    assert all(
        row["provider"] not in {"gemini", "cerebras"}
        for row in cfg["fallback_providers"]
    )

    assert cfg["auxiliary"]["vision"]["provider"] == "cloudflare"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_CLOUDFLARE_VISION_MODEL
    assert "api_key" not in cfg["auxiliary"]["vision"]
    assert "fallback_chain" not in cfg["auxiliary"]["vision"]
    assert cfg["auxiliary"]["compression"]["provider"] == "main"
    assert cfg["auxiliary"]["compression"]["model"] == DEFAULT_CLOUDFLARE_MODEL

    assert cfg["agent"]["api_max_retries"] == 1
    assert cfg["agent"]["auto_recovery_cycles"] == 0
    assert cfg["fallback"]["min_switch_reset_seconds"] == 60

    assert "gemini" not in cfg["credential_pool_strategies"]
    assert "cerebras" not in cfg["credential_pool_strategies"]
    assert cfg["credential_pool_strategies"]["cloudflare"] == "fill_first"
    assert cfg["credential_pool_strategies"]["groq"] == "fill_first"

    assert cfg["edit_aja"]["ai_profile"] == "cloudflare-recurring-free"
    assert cfg["edit_aja"]["primary_provider"] == "cloudflare"
    assert cfg["edit_aja"]["gemini_enabled"] is False
    assert cfg["edit_aja"]["cerebras_enabled"] is False

    # Input is not mutated and secrets are not copied into the generated route.
    assert original == before


def test_without_cloudflare_groq_becomes_primary_instead_of_cerebras():
    cfg = build_edit_aja_free_cloud_config({})

    assert "cloudflare" not in cfg["providers"]
    assert "cerebras" not in cfg["providers"]
    assert cfg["model"] == {
        "provider": "groq",
        "default": DEFAULT_GROQ_MODEL,
    }
    assert cfg["auxiliary"]["vision"]["provider"] == "main"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_GROQ_MODEL
    assert cfg["fallback_providers"] == []
    assert cfg["edit_aja"]["primary_provider"] == "groq"


def test_existing_cloudflare_account_id_survives_reapply():
    existing = {
        "providers": {
            "cloudflare": {
                "name": "Cloudflare Workers AI",
                "api": CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="existing123"),
            }
        }
    }

    cfg = build_edit_aja_free_cloud_config(existing)

    assert "existing123" in cfg["providers"]["cloudflare"]["api"]
    assert cfg["model"]["provider"] == "cloudflare"
    assert cfg["fallback_providers"] == [
        {"provider": "groq", "model": DEFAULT_GROQ_MODEL},
    ]


def test_custom_cloudflare_and_groq_model_overrides_remain_non_gemini_non_cerebras():
    cfg = build_edit_aja_free_cloud_config(
        {},
        cloudflare_account_id="cfaccount123",
        cloudflare_model="@cf/test/model",
        groq_model="openai/gpt-oss-test",
    )

    assert cfg["model"]["provider"] == "cloudflare"
    assert cfg["model"]["default"] == "@cf/test/model"
    assert cfg["auxiliary"]["compression"]["model"] == "@cf/test/model"
    assert cfg["fallback_providers"] == [
        {"provider": "groq", "model": "openai/gpt-oss-test"},
    ]
    assert "cerebras" not in cfg["providers"]


def test_invalid_cloudflare_account_id_falls_back_to_groq_primary():
    cfg = build_edit_aja_free_cloud_config(
        {},
        cloudflare_account_id="https://evil.example/account",
    )

    assert "cloudflare" not in cfg["providers"]
    assert cfg["model"]["provider"] == "groq"
    assert cfg["model"]["default"] == DEFAULT_GROQ_MODEL
    assert cfg["fallback_providers"] == []
