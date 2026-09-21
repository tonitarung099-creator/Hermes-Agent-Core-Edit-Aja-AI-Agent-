"""Edit Aja Cerebras-first free-cloud configuration tests."""

from __future__ import annotations

from copy import deepcopy

from hermes_cli.edit_aja_mode import (
    CEREBRAS_BASE_URL,
    CLOUDFLARE_BASE_URL_TEMPLATE,
    DEFAULT_CLOUDFLARE_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_MAIN_MODEL,
    GROQ_BASE_URL,
    build_edit_aja_free_cloud_config,
)


def test_free_cloud_profile_uses_cerebras_and_never_routes_to_gemini():
    original = {
        "model": {
            "provider": "gemini",
            "default": "gemini-old",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key": "must-not-survive",
            "api_mode": "chat_completions",
        },
        "fallback_providers": [
            {"provider": "gemini", "model": "gemini-fallback"},
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
            "anthropic": "least_used",
        },
    }
    before = deepcopy(original)

    cfg = build_edit_aja_free_cloud_config(
        original,
        cloudflare_account_id="abcdef1234567890",
    )

    assert cfg["model"]["provider"] == "cerebras"
    assert cfg["model"]["default"] == DEFAULT_MAIN_MODEL
    assert "api_key" not in cfg["model"]
    assert "base_url" not in cfg["model"]
    assert "api_mode" not in cfg["model"]

    assert cfg["providers"]["cerebras"]["api"] == CEREBRAS_BASE_URL
    assert cfg["providers"]["cerebras"]["default_model"] == DEFAULT_MAIN_MODEL
    assert cfg["providers"]["cloudflare"]["api"] == (
        CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890")
    )
    assert cfg["providers"]["cloudflare"]["default_model"] == DEFAULT_CLOUDFLARE_MODEL
    assert cfg["providers"]["groq"]["api"] == GROQ_BASE_URL
    assert cfg["providers"]["groq"]["default_model"] == DEFAULT_GROQ_MODEL

    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": DEFAULT_CLOUDFLARE_MODEL},
        {"provider": "groq", "model": DEFAULT_GROQ_MODEL},
    ]
    assert "fallback_model" not in cfg
    assert all(row["provider"] != "gemini" for row in cfg["fallback_providers"])

    assert cfg["auxiliary"]["vision"]["provider"] == "main"
    assert cfg["auxiliary"]["vision"]["model"] == DEFAULT_MAIN_MODEL
    assert "api_key" not in cfg["auxiliary"]["vision"]
    assert "fallback_chain" not in cfg["auxiliary"]["vision"]

    assert cfg["agent"]["api_max_retries"] == 1
    assert cfg["agent"]["auto_recovery_cycles"] == 0
    assert cfg["fallback"]["min_switch_reset_seconds"] == 60

    assert "gemini" not in cfg["credential_pool_strategies"]
    assert cfg["credential_pool_strategies"]["cerebras"] == "fill_first"
    assert cfg["credential_pool_strategies"]["cloudflare"] == "fill_first"
    assert cfg["credential_pool_strategies"]["groq"] == "fill_first"

    assert cfg["edit_aja"]["ai_profile"] == "cerebras-free-cloud"
    assert cfg["edit_aja"]["primary_provider"] == "cerebras"
    assert cfg["edit_aja"]["gemini_enabled"] is False

    # Input is not mutated and secrets are not copied into the generated route.
    assert original == before


def test_cloudflare_is_optional_but_groq_stays_available():
    cfg = build_edit_aja_free_cloud_config({})

    assert "cloudflare" not in cfg["providers"]
    assert cfg["fallback_providers"] == [
        {"provider": "groq", "model": DEFAULT_GROQ_MODEL},
    ]


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
    assert cfg["fallback_providers"][0]["provider"] == "cloudflare"


def test_custom_model_overrides_remain_non_gemini():
    cfg = build_edit_aja_free_cloud_config(
        {},
        main_model="gpt-oss-test",
        cloudflare_account_id="cfaccount123",
        cloudflare_model="@cf/test/model",
        groq_model="openai/gpt-oss-test",
    )

    assert cfg["model"]["provider"] == "cerebras"
    assert cfg["model"]["default"] == "gpt-oss-test"
    assert cfg["auxiliary"]["compression"]["model"] == "gpt-oss-test"
    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": "@cf/test/model"},
        {"provider": "groq", "model": "openai/gpt-oss-test"},
    ]


def test_invalid_cloudflare_account_id_is_not_written_into_url():
    cfg = build_edit_aja_free_cloud_config(
        {},
        cloudflare_account_id="https://evil.example/account",
    )

    assert "cloudflare" not in cfg["providers"]
    assert all(row["provider"] != "cloudflare" for row in cfg["fallback_providers"])
