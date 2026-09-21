"""Edit Aja opinionated Gemini-only runtime defaults.

This module deliberately changes configuration, not Hermes' provider engine. The
core keeps its upstream provider/plugin machinery intact so future upstream
updates remain mergeable, while the Edit Aja installer pins every AI task to the
main Gemini route and removes cloud-provider fallback chains.

Run:
    python -m hermes_cli.edit_aja_mode
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from typing import Any

from hermes_cli.config import clear_model_endpoint_credentials, load_config, save_config

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MAIN_MODEL = "gemini-3.7-flash"
DEFAULT_LIGHT_MODEL = "gemini-3.5-flash-lite"

# Tasks that benefit from the main model's stronger multimodal/reasoning path.
_STRONG_AUX_TASKS = frozenset({
    "vision",
    "review",
    "triage_specifier",
    "kanban_decomposer",
})

# Side tasks where a smaller Gemini model is preferred to reduce latency and
# free-tier consumption while keeping every AI request on Gemini.
_LIGHT_AUX_TASKS = frozenset({
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
    if isinstance(value, dict):
        return dict(value)
    return {}


def build_edit_aja_gemini_config(
    config: dict[str, Any] | None,
    *,
    main_model: str = DEFAULT_MAIN_MODEL,
    light_model: str = DEFAULT_LIGHT_MODEL,
) -> dict[str, Any]:
    """Return config with Edit Aja's Gemini-only policy applied.

    Secrets are never copied into config.yaml. Gemini API keys continue to live
    in Hermes' credential pool / secret store. The main provider is Gemini,
    cloud fallback providers are disabled, and auxiliary tasks inherit the main
    provider while selecting either the main or lightweight Gemini model.
    """

    cfg: dict[str, Any] = deepcopy(config) if isinstance(config, dict) else {}

    model = _dict_section(cfg, "model")
    model["provider"] = "gemini"
    model["default"] = str(main_model or DEFAULT_MAIN_MODEL).strip() or DEFAULT_MAIN_MODEL
    model["base_url"] = GEMINI_BASE_URL
    # Provider-native routing owns auth and API mode. Do not leave an inline key
    # or stale OpenAI-compat mode in config.yaml.
    clear_model_endpoint_credentials(model, clear_api_mode=True)
    cfg["model"] = model

    # Do not silently escape to another cloud model. Credential failover within
    # the Gemini provider remains available through Hermes' credential pool.
    cfg["fallback_providers"] = []

    auxiliary = _dict_section(cfg, "auxiliary")
    for task in sorted(_STRONG_AUX_TASKS | _LIGHT_AUX_TASKS):
        block = auxiliary.get(task)
        block = dict(block) if isinstance(block, dict) else {}
        block["provider"] = "main"
        block["model"] = (
            model["default"] if task in _STRONG_AUX_TASKS
            else str(light_model or DEFAULT_LIGHT_MODEL).strip() or DEFAULT_LIGHT_MODEL
        )
        # Remove direct endpoint/provider escape hatches from the generated
        # profile. Users can still change them manually later if they choose.
        for key in ("base_url", "api_key", "fallback_chain"):
            block.pop(key, None)
        auxiliary[task] = block
    cfg["auxiliary"] = auxiliary

    # Fill-first keeps one preferred credential stable. Hermes' existing health
    # and cooldown machinery may select another independently authorized Gemini
    # credential when the preferred credential is unavailable.
    strategies = _dict_section(cfg, "credential_pool_strategies")
    strategies["gemini"] = "fill_first"
    cfg["credential_pool_strategies"] = strategies

    # Edit Aja is designed as a personal Telegram assistant. Default its
    # messaging surface to final-answer-first: internal tool/redirect chatter
    # remains available in local logs and can be re-enabled with /debug on.
    from gateway.edit_aja_local import apply_quiet_mode
    cfg = apply_quiet_mode(cfg, True)

    return cfg


def apply_edit_aja_gemini_defaults(
    *,
    main_model: str = DEFAULT_MAIN_MODEL,
    light_model: str = DEFAULT_LIGHT_MODEL,
) -> dict[str, Any]:
    cfg = build_edit_aja_gemini_config(
        load_config(),
        main_model=main_model,
        light_model=light_model,
    )
    save_config(cfg)
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure Hermes as the Gemini-only Edit Aja AI Agent."
    )
    parser.add_argument("--main-model", default=DEFAULT_MAIN_MODEL)
    parser.add_argument("--light-model", default=DEFAULT_LIGHT_MODEL)
    args = parser.parse_args(argv)

    cfg = apply_edit_aja_gemini_defaults(
        main_model=args.main_model,
        light_model=args.light_model,
    )
    print("Edit Aja Gemini-only mode configured.")
    print(f"  Main model:  {cfg['model']['default']}")
    print(f"  Light model: {args.light_model}")
    print("  Provider:    gemini")
    print("  Fallbacks:   other cloud providers disabled")
    print("  Key pool:    hermes auth list gemini")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
