"""Runtime/auth integration checks for Edit Aja's free-cloud providers.

These tests go beyond config-shape assertions: they verify that Hermes treats the
provider IDs written by edit_aja_mode as configured auth targets and that the
runtime resolver can bind a pooled credential to each OpenAI-compatible route.
No network access is used.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hermes_cli.edit_aja_mode import (
    CEREBRAS_BASE_URL,
    CLOUDFLARE_BASE_URL_TEMPLATE,
    DEFAULT_CLOUDFLARE_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_MAIN_MODEL,
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
        ("cerebras", CEREBRAS_BASE_URL),
        (
            "cloudflare",
            CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890"),
        ),
        ("groq", GROQ_BASE_URL),
    ],
)
def test_auth_cli_recognizes_edit_aja_named_providers(monkeypatch, provider, expected_url):
    """hermes auth add/list <provider> must recognize the IDs created by Edit Aja."""
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
        ("cerebras", DEFAULT_MAIN_MODEL, CEREBRAS_BASE_URL),
        (
            "cloudflare",
            DEFAULT_CLOUDFLARE_MODEL,
            CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id="abcdef1234567890"),
        ),
        ("groq", DEFAULT_GROQ_MODEL, GROQ_BASE_URL),
    ],
)
def test_runtime_resolves_edit_aja_provider_from_credential_pool(
    monkeypatch, provider, model, expected_url
):
    """Configured provider + pooled key must resolve without falling into another provider."""
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

    # Named custom providers intentionally resolve to the shared "custom"
    # transport class while retaining their durable requested_provider identity.
    assert runtime["provider"] == "custom"
    assert runtime["requested_provider"] == provider
    assert runtime["base_url"] == expected_url
    assert runtime["api_mode"] == "chat_completions"
    assert runtime["api_key"] == secret
    assert runtime["model"] == model
    assert runtime["source"] == f"pool:{provider}"


def test_free_cloud_primary_and_fallback_order_is_independent_of_gemini():
    cfg = _free_cloud_config()

    assert cfg["model"] == {
        "provider": "cerebras",
        "default": DEFAULT_MAIN_MODEL,
    }
    assert cfg["fallback_providers"] == [
        {"provider": "cloudflare", "model": DEFAULT_CLOUDFLARE_MODEL},
        {"provider": "groq", "model": DEFAULT_GROQ_MODEL},
    ]
    assert cfg["edit_aja"]["gemini_enabled"] is False
    assert all(
        row["provider"] != "gemini"
        for row in cfg["fallback_providers"]
    )
