"""Runtime/auth integration checks for Edit Aja's recurring-free providers.

These tests verify that Hermes treats Groq and optional Cloudflare as configured
auth targets and can bind pooled credentials to their OpenAI-compatible routes.
No network access is used.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hermes_cli.edit_aja_mode import (
    CLOUDFLARE_BASE_URL_TEMPLATE,
    DEFAULT_CLOUDFLARE_MODEL,
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    build_edit_aja_free_cloud_config,
)


def _free_cloud_config():
    return build_edit_aja_free_cloud_config(
        {},
        cloudflare_account_id="abcdef1234567890",
    )


@pytest.mark.parametrize(
    ("provider", "expected_url"),
    [
        ("groq", GROQ_BASE_URL),
        (
            "cloudflare",
            CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890"),
        ),
    ],
)
def test_auth_cli_recognizes_edit_aja_named_providers(monkeypatch, provider, expected_url):
    from hermes_cli import auth_commands
    from hermes_cli import config as config_mod

    cfg = _free_cloud_config()
    monkeypatch.setattr(config_mod, "load_config", lambda: cfg)

    normalized = auth_commands._normalize_provider(provider)
    configured = auth_commands._configured_provider_entry(normalized)

    assert normalized == provider
    assert configured is not None
    assert configured["provider_key"] == provider
    assert configured["base_url"] == expected_url
    assert auth_commands._provider_base_url(provider) == expected_url
    assert auth_commands._is_known_provider(provider, configured) is True


@pytest.mark.parametrize(
    ("provider", "model", "expected_url"),
    [
        ("groq", DEFAULT_GROQ_MODEL, GROQ_BASE_URL),
        (
            "cloudflare",
            DEFAULT_CLOUDFLARE_MODEL,
            CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890"),
        ),
    ],
)
def test_runtime_resolves_edit_aja_provider_from_credential_pool(
    monkeypatch, provider, model, expected_url
):
    from hermes_cli import runtime_provider

    cfg = _free_cloud_config()
    secret = f"fixture-secret-{provider}"

    class FakePool:
        def has_credentials(self):
            return True

        def select(self):
            return SimpleNamespace(
                access_token=secret,
                runtime_api_key=secret,
                base_url=expected_url,
                runtime_base_url=expected_url,
            )

    monkeypatch.setattr(runtime_provider, "load_config", lambda: cfg)
    monkeypatch.setattr(
        runtime_provider,
        "custom_provider_pool_key_candidates",
        lambda base_url, provider_name=None: [provider],
    )
    monkeypatch.setattr(
        runtime_provider,
        "load_pool",
        lambda pool_key: FakePool() if pool_key == provider else None,
    )

    runtime = runtime_provider.resolve_runtime_provider(
        requested=provider,
        target_model=model,
    )

    assert runtime["provider"] == "custom"
    assert runtime["requested_provider"] == provider
    assert runtime["base_url"] == expected_url
    assert runtime["api_mode"] == "chat_completions"
    assert runtime["api_key"] == secret
    assert runtime["model"] == model
    assert runtime["source"] == f"pool:{provider}"


def test_recurring_free_primary_and_fallback_order_uses_only_groq_and_cloudflare():
    cfg = _free_cloud_config()

    assert cfg["model"] == {
        "provider": "groq",
        "default": DEFAULT_GROQ_MODEL,
    }
    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": DEFAULT_CLOUDFLARE_MODEL},
    ]
    assert "cerebras" not in cfg["providers"]
    assert "gemini" not in cfg["providers"]
    assert cfg["edit_aja"]["gemini_enabled"] is False
    assert cfg["edit_aja"]["cerebras_enabled"] is False
