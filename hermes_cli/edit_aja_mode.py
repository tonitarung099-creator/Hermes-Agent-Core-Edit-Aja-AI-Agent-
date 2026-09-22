"""Edit Aja recurring-free cloud runtime profile.

Primary AI:
    Groq / openai/gpt-oss-120b

Fallback:
    Cloudflare Workers AI / GLM-4.7-Flash (when an account id is configured)

Groq GPT-OSS 120B is the default reasoning/tool-calling brain. Cloudflare is
the only fallback and also supplies the dedicated vision route when configured.
Both routes use OpenAI-compatible Chat Completions endpoints. Secrets stay in
Hermes' credential pool.

Gemini and Cerebras are intentionally NOT part of the Edit Aja routing chain.
"""

from __future__ import annotations

import argparse
import re
from copy import deepcopy
from typing import Any

from hermes_cli.config import clear_model_endpoint_credentials, load_config, save_config

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
CLOUDFLARE_BASE_URL_TEMPLATE = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_MAIN_MODEL = DEFAULT_GROQ_MODEL
DEFAULT_CLOUDFLARE_MODEL = "@cf/zai-org/glm-4.7-flash"
DEFAULT_CLOUDFLARE_VISION_MODEL = "@cf/google/gemma-4-26b-a4b-it"
DEFAULT_CONTEXT_LENGTH = 131_072

_AUX_TASKS = frozenset({
    "vision",
    "review",
    "triage_specifier",
    "kanban_decomposer",
    "compression",
    "approval",
    "mcp",
    "title_generation",
    "memory_query_rewrite",
    "tts_audio_tags",
    "skills_hub",
    "profile_describer",
    "curator",
})


def _dict_section(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _clean_account_id(value: str | None) -> str:
    raw = str(value or "").strip()
    return raw if re.fullmatch(r"[A-Za-z0-9_-]{6,128}", raw) else ""


def _provider_entry(
    *,
    name: str,
    api: str,
    model: str,
    context_length: int = DEFAULT_CONTEXT_LENGTH,
) -> dict[str, Any]:
    return {
        "name": name,
        "api": api,
        "transport": "chat_completions",
        "default_model": model,
        "discover_models": False,
        "context_length": context_length,
        "models": {
            model: {
                "context_length": context_length,
            }
        },
    }


def _existing_cloudflare_account_id(config: dict[str, Any]) -> str:
    providers = config.get("providers")
    entry = providers.get("cloudflare") if isinstance(providers, dict) else None
    if not isinstance(entry, dict):
        return ""
    url = str(entry.get("api") or entry.get("base_url") or "").strip()
    match = re.search(r"/accounts/([^/]+)/ai/v1/?$", url)
    return _clean_account_id(match.group(1)) if match else ""


def build_edit_aja_free_cloud_config(
    config: dict[str, Any] | None,
    *,
    main_model: str = DEFAULT_MAIN_MODEL,
    cloudflare_account_id: str | None = None,
    cloudflare_model: str = DEFAULT_CLOUDFLARE_MODEL,
    groq_model: str = DEFAULT_GROQ_MODEL,
    disable_cloudflare: bool = False,
) -> dict[str, Any]:
    """Return Edit Aja's Groq-first, Cloudflare-fallback configuration.

    Gemini and Cerebras are removed from active routing. API keys are never
    written into config.yaml. Named custom providers are registered first,
    then Hermes auth stores their secrets locally.
    """

    cfg: dict[str, Any] = deepcopy(config) if isinstance(config, dict) else {}
    requested_main_model = str(main_model or "").strip()
    groq_model = str(groq_model or "").strip()
    if requested_main_model and requested_main_model != DEFAULT_MAIN_MODEL:
        groq_model = requested_main_model
    groq_model = groq_model or DEFAULT_GROQ_MODEL
    cloudflare_model = (
        str(cloudflare_model or DEFAULT_CLOUDFLARE_MODEL).strip()
        or DEFAULT_CLOUDFLARE_MODEL
    )

    cf_account = "" if disable_cloudflare else _clean_account_id(cloudflare_account_id)
    if not disable_cloudflare and not cf_account:
        cf_account = _existing_cloudflare_account_id(cfg)

    providers = _dict_section(cfg, "providers")
    # Remove providers that Edit Aja no longer routes through. Stored credentials
    # remain local in Hermes auth, but this profile will never select them.
    providers.pop("cerebras", None)
    providers.pop("gemini", None)
    providers["groq"] = _provider_entry(
        name="Groq",
        api=GROQ_BASE_URL,
        model=groq_model,
        context_length=DEFAULT_CONTEXT_LENGTH,
    )
    if cf_account:
        providers["cloudflare"] = _provider_entry(
            name="Cloudflare Workers AI",
            api=CLOUDFLARE_BASE_URL_TEMPLATE.format(account_id=cf_account),
            model=cloudflare_model,
            context_length=DEFAULT_CONTEXT_LENGTH,
        )
        # Separate free-plan vision route for screenshots/UI understanding.
        providers["cloudflare"]["models"][DEFAULT_CLOUDFLARE_VISION_MODEL] = {
            "context_length": 256_000,
        }
    else:
        providers.pop("cloudflare", None)
    cfg["providers"] = providers

    model = _dict_section(cfg, "model")
    model["provider"] = "groq"
    model["default"] = groq_model
    for key in ("base_url", "api_key", "key_env", "api_key_env"):
        model.pop(key, None)
    clear_model_endpoint_credentials(model, clear_api_mode=True)
    cfg["model"] = model

    fallback_chain: list[dict[str, str]] = []
    if cf_account:
        fallback_chain.append({
            "provider": "cloudflare",
            "model": cloudflare_model,
        })
    cfg["fallback_providers"] = fallback_chain
    cfg.pop("fallback_model", None)

    auxiliary = _dict_section(cfg, "auxiliary")
    for task in sorted(_AUX_TASKS):
        block = auxiliary.get(task)
        block = dict(block) if isinstance(block, dict) else {}
        block["provider"] = "main"
        block["model"] = groq_model
        for key in ("base_url", "api_key", "key_env", "fallback_chain"):
            block.pop(key, None)
        auxiliary[task] = block

    # Groq GPT-OSS is the reasoning/tool brain, while Cloudflare Gemma is
    # used for image/screenshot understanding when Cloudflare is present.
    if cf_account:
        vision = dict(auxiliary.get("vision") or {})
        vision["provider"] = "cloudflare"
        vision["model"] = DEFAULT_CLOUDFLARE_VISION_MODEL
        for key in ("base_url", "api_key", "key_env", "fallback_chain"):
            vision.pop(key, None)
        auxiliary["vision"] = vision

    cfg["auxiliary"] = auxiliary

    agent = _dict_section(cfg, "agent")
    agent["api_max_retries"] = 1
    agent["auto_recovery_cycles"] = 0
    cfg["agent"] = agent

    fallback_cfg = _dict_section(cfg, "fallback")
    fallback_cfg["min_switch_reset_seconds"] = 60
    cfg["fallback"] = fallback_cfg

    strategies = _dict_section(cfg, "credential_pool_strategies")
    strategies.pop("gemini", None)
    strategies.pop("cerebras", None)
    strategies["cloudflare"] = "fill_first"
    strategies["groq"] = "fill_first"
    cfg["credential_pool_strategies"] = strategies

    edit_aja = _dict_section(cfg, "edit_aja")
    edit_aja.update({
        "enabled": True,
        "ai_profile": "groq-cloudflare-free",
        "primary_provider": "groq",
        "gemini_enabled": False,
        "cerebras_enabled": False,
    })
    cfg["edit_aja"] = edit_aja

    from gateway.edit_aja_local import apply_quiet_mode
    cfg = apply_quiet_mode(cfg, True)
    return cfg


def apply_edit_aja_free_cloud_defaults(
    *,
    main_model: str = DEFAULT_MAIN_MODEL,
    cloudflare_account_id: str | None = None,
    cloudflare_model: str = DEFAULT_CLOUDFLARE_MODEL,
    groq_model: str = DEFAULT_GROQ_MODEL,
    disable_cloudflare: bool = False,
) -> dict[str, Any]:
    cfg = build_edit_aja_free_cloud_config(
        load_config(),
        main_model=main_model,
        cloudflare_account_id=cloudflare_account_id,
        cloudflare_model=cloudflare_model,
        groq_model=groq_model,
        disable_cloudflare=disable_cloudflare,
    )
    save_config(cfg)
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Configure Edit Aja with Groq primary, optional Cloudflare fallback/vision, "
            "and no Gemini/Cerebras routing."
        )
    )
    parser.add_argument("--main-model", default=DEFAULT_MAIN_MODEL)
    parser.add_argument("--cloudflare-account-id", default="")
    parser.add_argument(
        "--no-cloudflare",
        action="store_true",
        help="Remove/skip the optional Cloudflare fallback/vision route even if an old account id exists.",
    )
    parser.add_argument("--cloudflare-model", default=DEFAULT_CLOUDFLARE_MODEL)
    parser.add_argument("--groq-model", default=DEFAULT_GROQ_MODEL)
    args = parser.parse_args(argv)

    cfg = apply_edit_aja_free_cloud_defaults(
        main_model=args.main_model,
        cloudflare_account_id=args.cloudflare_account_id,
        cloudflare_model=args.cloudflare_model,
        groq_model=args.groq_model,
        disable_cloudflare=args.no_cloudflare,
    )
    fallbacks = cfg.get("fallback_providers") or []

    print("Edit Aja recurring-free mode configured.")
    print(f"  Primary:     groq / {cfg['model']['default']}")
    if any(row.get("provider") == "cloudflare" for row in fallbacks if isinstance(row, dict)):
        print(f"  Fallback #1: cloudflare / {args.cloudflare_model}")
    else:
        print("  Cloudflare:  skipped (no account id configured; Groq remains primary)")
        print("  Fallback:    none")
    print("  Gemini:      disabled for Edit Aja routing")
    print("  Cerebras:    disabled for Edit Aja routing")
    print("  API retries: 1 per provider call")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
