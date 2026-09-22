"""Edit Aja Groq + Cloudflare recurring-free cloud configuration tests."""

from __future__ import annotations

from copy import deepcopy

from hermes_cli.edit_aja_mode import (
    CLOUDFLARE_BASE_URL_TEMPLATE,
    DEFAULT_CLOUDFLARE_MODEL,
    DEFAULT_CLOUDFLARE_VISION_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_MAIN_MODEL,
    GROQ_BASE_URL,
    build_edit_aja_free_cloud_config,
)


def test_free_cloud_profile_uses_only_groq_and_cloudflare():
    original = {
        "providers": {
            "cerebras": {
                "name": "Cerebras",
                "api": "https://api.cerebras.ai/v1",
                "default_model": "gpt-oss-120b",
            },
            "gemini": {
                "name": "Gemini",
                "api": "https://generativelanguage.googleapis.com/v1beta",
            },
        },
        "model": {
            "provider": "cerebras",
            "default": "gpt-oss-120b",
            "base_url": "https://api.cerebras.ai/v1",
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

    assert cfg["model"] == {
        "provider": "groq",
        "default": DEFAULT_GROQ_MODEL,
    }
    assert "api_key" not in cfg["model"]
    assert "base_url" not in cfg["model"]
    assert "api_mode" not in cfg["model"]

    assert "cerebras" not in cfg["providers"]
    assert "gemini" not in cfg["providers"]
    assert cfg["providers"]["groq"]["api"] == GROQ_BASE_URL
    assert cfg["providers"]["groq"]["default_model"] == DEFAULT_GROQ_MODEL
    assert cfg["providers"]["cloudflare"]["api"] == (
        CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890")
    )
    assert cfg["providers"]["cloudflare"]["default_model"] == DEFAULT_CLOUDFLARE_MODEL
    assert DEFAULT_CLOUDFLARE_VISION_MODEL in cfg["providers"]["cloudflare"]["models"]
    assert cfg["providers"]["cloudflare"]["models"][DEFAULT_CLOUDFLARE_VISION_MODEL]["context_length"] == 256_000

    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": DEFAULT_CLOUDFLARE_MODEL},
    ]
    assert "fallback_model" not in cfg

    assert cfg["auxiliary"]["vision"]["provider"] == "cloudflare"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_CLOUDFLARE_VISION_MODEL
    assert "api_key" not in cfg["auxiliary"]["vision"]
    assert "fallback_chain" not in cfg["auxiliary"]["vision"]
    assert cfg["auxiliary"]["compression"]["provider"] == "main"
    assert cfg["auxiliary"]["compression"]["model"] == DEFAULT_GROQ_MODEL

    assert cfg["agent"]["api_max_retries"] == 1
    assert cfg["agent"]["auto_recovery_cycles"] == 0
    assert cfg["fallback"]["min_switch_reset_seconds"] == 60

    assert "gemini" not in cfg["credential_pool_strategies"]
    assert "cerebras" not in cfg["credential_pool_strategies"]
    assert cfg["credential_pool_strategies"]["cloudflare"] == "fill_first"
    assert cfg["credential_pool_strategies"]["groq"] == "fill_first"

    assert cfg["edit_aja"]["ai_profile"] == "groq-cloudflare-free"
    assert cfg["edit_aja"]["primary_provider"] == "groq"
    assert cfg["edit_aja"]["gemini_enabled"] is False
    assert cfg["edit_aja"]["cerebras_enabled"] is False

    assert original == before


def test_without_cloudflare_groq_is_primary_and_only_route():
    cfg = build_edit_aja_free_cloud_config({})

    assert "cloudflare" not in cfg["providers"]
    assert "cerebras" not in cfg["providers"]
    assert "gemini" not in cfg["providers"]
    assert cfg["model"] == {
        "provider": "groq",
        "default": DEFAULT_GROQ_MODEL,
    }
    assert cfg["auxiliary"]["vision"]["provider"] == "main"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_GROQ_MODEL
    assert cfg["fallback_providers"] == []


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
    assert cfg["model"]["provider"] == "groq"
    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": DEFAULT_CLOUDFLARE_MODEL},
    ]


def test_custom_groq_and_cloudflare_models_are_preserved():
    cfg = build_edit_aja_free_cloud_config(
        {},
        main_model="openai/gpt-oss-test",
        cloudflare_account_id="cfaccount123",
        cloudflare_model="@cf/test/model",
    )

    assert cfg["model"] == {
        "provider": "groq",
        "default": "openai/gpt-oss-test",
    }
    assert cfg["providers"]["groq"]["default_model"] == "openai/gpt-oss-test"
    assert cfg["auxiliary"]["compression"]["model"] == "openai/gpt-oss-test"
    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": "@cf/test/model"},
    ]


def test_invalid_cloudflare_account_id_leaves_groq_only():
    cfg = build_edit_aja_free_cloud_config(
        {},
        cloudflare_account_id="https://evil.example/account",
    )

    assert "cloudflare" not in cfg["providers"]
    assert cfg["model"]["provider"] == "groq"
    assert cfg["fallback_providers"] == []


def test_explicit_cloudflare_disable_removes_old_route_and_keeps_groq():
    existing = {
        "providers": {
            "cloudflare": {
                "name": "Cloudflare Workers AI",
                "api": CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="existing123"),
            }
        }
    }

    cfg = build_edit_aja_free_cloud_config(existing, disable_cloudflare=True)

    assert "cloudflare" not in cfg["providers"]
    assert cfg["model"] == {
        "provider": "groq",
        "default": DEFAULT_MAIN_MODEL,
    }
    assert cfg["fallback_providers"] == []
    assert cfg["edit_aja"]["cerebras_enabled"] is False
