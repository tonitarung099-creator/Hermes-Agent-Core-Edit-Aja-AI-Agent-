"""Edit Aja local control/status router.

This module intentionally answers small operational questions without an LLM.
It never exposes credential values. It reads only local Hermes config and the
credential-pool health metadata already maintained by Hermes.
"""

from __future__ import annotations

import os
import re
import time
from copy import deepcopy
from typing import Any

_EDIT_AJA_KEY = "edit_aja"


def edit_aja_enabled(config: dict[str, Any] | None) -> bool:
    if not isinstance(config, dict):
        return False
    section = config.get(_EDIT_AJA_KEY)
    return isinstance(section, dict) and section.get("enabled") is True


def _model_config(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("model")
    return value if isinstance(value, dict) else {}


def _aux_config(config: dict[str, Any], task: str) -> dict[str, Any]:
    aux = config.get("auxiliary")
    if not isinstance(aux, dict):
        return {}
    value = aux.get(task)
    return value if isinstance(value, dict) else {}


def _quiet_enabled(config: dict[str, Any]) -> bool:
    section = config.get(_EDIT_AJA_KEY)
    if isinstance(section, dict) and isinstance(section.get("quiet_mode"), bool):
        return bool(section["quiet_mode"])
    display = config.get("display")
    if isinstance(display, dict):
        platforms = display.get("platforms")
        if isinstance(platforms, dict):
            telegram = platforms.get("telegram")
            if isinstance(telegram, dict) and telegram.get("busy_ack_enabled") is False:
                return True
    return False


def _fallback_routes(config: dict[str, Any]) -> list[tuple[str, str]]:
    raw = config.get("fallback_providers")
    routes: list[tuple[str, str]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").strip()
        model = str(item.get("model") or "").strip()
        if provider and model:
            routes.append((provider, model))
    return routes


def model_status(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}
    model = _model_config(config)
    main_model = str(model.get("default") or "unknown")
    provider = str(model.get("provider") or "unknown")
    lines = [
        "🤖 **Edit Aja AI Model**",
        f"Primary: **{provider}** / `{main_model}`",
    ]
    for index, (fallback_provider, fallback_model) in enumerate(_fallback_routes(config), start=1):
        lines.append(
            f"Fallback {index}: **{fallback_provider}** / `{fallback_model}`"
        )
    if (config.get("edit_aja") or {}).get("gemini_enabled") is False:
        lines.append("Gemini: **DISABLED**")
    return "\n".join(lines)


def _entry_state(
    entry: Any, *, main_model: str, now: float, sole_credential: bool = False
) -> str:
    from agent.credential_pool import STATUS_DEAD, STATUS_EXHAUSTED, _exhausted_until

    if getattr(entry, "last_status", None) == STATUS_DEAD:
        return "DEAD"

    cooldowns = getattr(entry, "model_cooldowns", None) or {}
    cooldown_until = cooldowns.get(main_model)
    if isinstance(cooldown_until, (int, float)) and cooldown_until > now:
        return "COOLDOWN"

    if getattr(entry, "last_status", None) == STATUS_EXHAUSTED:
        exhausted_until = _exhausted_until(entry, sole_credential=sole_credential)
        return "COOLDOWN" if exhausted_until is None or exhausted_until > now else "READY"

    return "READY"


def _provider_model(config: dict[str, Any], provider: str) -> str:
    model = _model_config(config)
    if str(model.get("provider") or "").strip().lower() == provider.lower():
        return str(model.get("default") or "")
    for fallback_provider, fallback_model in _fallback_routes(config):
        if fallback_provider.lower() == provider.lower():
            return fallback_model
    providers = config.get("providers")
    entry = providers.get(provider) if isinstance(providers, dict) else None
    if isinstance(entry, dict):
        return str(entry.get("default_model") or entry.get("model") or "")
    return ""


def _provider_snapshot(
    provider: str, model: str, *, display_name: str | None = None
) -> dict[str, Any]:
    try:
        from agent.credential_pool import load_pool
        pool = load_pool(provider)
        entries = sorted(pool.entries(), key=lambda item: (item.priority, item.label))
    except Exception:
        entries = []

    now = time.time()
    non_dead_count = sum(getattr(entry, "last_status", None) != "dead" for entry in entries)
    sole_credential = non_dead_count <= 1
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        rows.append({
            "index": index,
            "label": str(getattr(entry, "label", "") or f"{provider} {index:02d}"),
            "priority": int(getattr(entry, "priority", index - 1) or 0),
            "state": _entry_state(
                entry, main_model=model, now=now, sole_credential=sole_credential
            ),
            "request_count": int(getattr(entry, "request_count", 0) or 0),
        })

    ready = [row for row in rows if row["state"] == "READY"]
    return {
        "provider": provider,
        "display_name": display_name or provider,
        "model": model,
        "rows": rows,
        "total": len(rows),
        "ready": sum(row["state"] == "READY" for row in rows),
        "cooldown": sum(row["state"] == "COOLDOWN" for row in rows),
        "dead": sum(row["state"] == "DEAD" for row in rows),
        "preferred": ready[0]["label"] if ready else None,
    }


def api_snapshot(config: dict[str, Any] | None = None) -> dict[str, Any]:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}

    model = _model_config(config)
    routes: list[tuple[str, str]] = []
    primary_provider = str(model.get("provider") or "").strip()
    primary_model = str(model.get("default") or "").strip()
    if primary_provider:
        routes.append((primary_provider, primary_model))
    routes.extend(_fallback_routes(config))

    seen: set[str] = set()
    providers: list[dict[str, Any]] = []
    labels = {
        "cerebras": "Cerebras",
        "cloudflare": "Cloudflare",
        "groq": "Groq",
    }
    for provider, route_model in routes:
        key = provider.lower()
        if key in seen:
            continue
        seen.add(key)
        providers.append(
            _provider_snapshot(
                provider,
                route_model or _provider_model(config, provider),
                display_name=labels.get(key, provider),
            )
        )

    all_rows = [row for provider in providers for row in provider["rows"]]
    return {
        "providers": providers,
        "rows": all_rows,
        "total": len(all_rows),
        "ready": sum(row["state"] == "READY" for row in all_rows),
        "cooldown": sum(row["state"] == "COOLDOWN" for row in all_rows),
        "dead": sum(row["state"] == "DEAD" for row in all_rows),
    }


def api_status(config: dict[str, Any] | None = None) -> str:
    snap = api_snapshot(config)
    lines = [
        "🔑 **Edit Aja API Pools**",
        f"Credentials: **{snap['total']}**  |  READY: **{snap['ready']}**  |  COOLDOWN: **{snap['cooldown']}**  |  DEAD: **{snap['dead']}**",
    ]
    for provider in snap["providers"]:
        lines.append("")
        lines.append(
            f"**{provider['display_name']}** — `{provider['model'] or 'model unknown'}`"
        )
        if not provider["rows"]:
            lines.append("⚪ No API key stored")
            continue
        for row in provider["rows"]:
            icon = "✅" if row["state"] == "READY" else "⏳" if row["state"] == "COOLDOWN" else "❌"
            lines.append(f"{icon} {row['label']}: **{row['state']}**")
    lines.extend([
        "",
        "Remaining quota (%): **not reliably available from these inference APIs**.",
        "Edit Aja reports observed key health and never invents a percentage.",
    ])
    return "\n".join(lines)


def compact_status(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}
    model = _model_config(config)
    snap = api_snapshot(config)
    quiet = "ON" if _quiet_enabled(config) else "OFF"
    fallbacks = _fallback_routes(config)
    fallback_text = " → ".join(provider for provider, _ in fallbacks) or "none"
    return "\n".join([
        "🟢 **EDIT AJA AI AGENT**",
        f"Gateway: **ONLINE** (PID {os.getpid()})",
        f"Primary: **{model.get('provider') or 'unknown'}** / `{model.get('default') or 'unknown'}`",
        f"Fallbacks: **{fallback_text}**",
        f"API credentials: **{snap['total']}** ({snap['ready']} ready, {snap['cooldown']} cooldown, {snap['dead']} dead)",
        f"Quiet mode: **{quiet}**",
        f"Gemini: **{'DISABLED' if (config.get('edit_aja') or {}).get('gemini_enabled') is False else 'not configured by Edit Aja'}**",
        "Laptop: **ONLINE**",
    ])

def apply_quiet_mode(config: dict[str, Any] | None, enabled: bool) -> dict[str, Any]:
    """Return a config copy with Edit Aja Telegram quiet/debug display settings."""
    cfg = deepcopy(config) if isinstance(config, dict) else {}
    edit_aja = cfg.setdefault(_EDIT_AJA_KEY, {})
    if not isinstance(edit_aja, dict):
        edit_aja = {}
        cfg[_EDIT_AJA_KEY] = edit_aja
    edit_aja["enabled"] = True
    edit_aja["quiet_mode"] = bool(enabled)

    display = cfg.setdefault("display", {})
    if not isinstance(display, dict):
        display = {}
        cfg["display"] = display
    display["tool_progress_command"] = True

    platforms = display.setdefault("platforms", {})
    if not isinstance(platforms, dict):
        platforms = {}
        display["platforms"] = platforms
    telegram = platforms.setdefault("telegram", {})
    if not isinstance(telegram, dict):
        telegram = {}
        platforms["telegram"] = telegram

    if enabled:
        telegram.update({
            "tool_progress": "off",
            "interim_assistant_messages": False,
            "thinking_progress": False,
            "long_running_notifications": False,
            "busy_ack_enabled": False,
            "busy_ack_detail": False,
            "busy_steer_ack_enabled": False,
            "cleanup_progress": True,
        })
    else:
        telegram.update({
            "tool_progress": "all",
            "interim_assistant_messages": True,
            "thinking_progress": False,
            "long_running_notifications": True,
            "busy_ack_enabled": True,
            "busy_ack_detail": True,
            "busy_steer_ack_enabled": True,
            "cleanup_progress": False,
        })
    return cfg


def set_quiet_mode(enabled: bool) -> str:
    from hermes_cli.config import load_config, save_config
    cfg = apply_quiet_mode(load_config(), enabled)
    save_config(cfg)
    return (
        "🔕 **Quiet Mode ON**\nTelegram will show mainly final answers; technical progress stays in local logs.\n"
        "Use `/debug on` or `/quiet off` to show technical progress again."
        if enabled
        else
        "🛠 **Debug display ON**\nTelegram will show tool/progress details again.\n"
        "Use `/debug off` or `/quiet on` to return to Quiet Mode."
    )


def quiet_status(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    return f"Quiet mode: **{'ON' if _quiet_enabled(config or {}) else 'OFF'}**"


def _normalise_text(text: str) -> str:
    value = re.sub(r"[^a-z0-9/]+", " ", (text or "").lower())
    return re.sub(r"\s+", " ", value).strip()


def local_intent(text: str) -> str | None:
    """Conservative local-intent classifier. Returns status|model|api, else None."""
    raw = (text or "").strip()
    if not raw or raw.startswith("/"):
        return None
    value = _normalise_text(raw)
    if len(value) > 140:
        return None

    # API/key count and health questions. Deliberately requires count/status
    # language so generic provider questions still reach the LLM.
    api_terms = (
        "api", "api key", "cerebras key", "key cerebras",
        "cloudflare key", "key cloudflare", "groq key", "key groq",
    )
    if any(term in value for term in api_terms) and (
        any(term in value for term in ("berapa", "jumlah", "masih berapa", "status", "tersisa", "sisa", "ready", "cooldown"))
        or re.search(r"\bhow many\b", value)
    ):
        return "api"

    model_markers = (
        "model apa", "model yang kamu pakai", "model kamu pakai", "model yang dipakai",
        "model aktif", "model sekarang", "modelmu", "model kamu", "which model",
        "what model", "current model",
    )
    if any(marker in value for marker in model_markers):
        return "model"

    status_markers = (
        "agent hidup", "agent online", "status agent", "gateway hidup", "gateway online",
        "status gateway", "hermes hidup", "hermes online", "status hermes",
        "apakah agent hidup", "is the agent online", "is gateway running",
    )
    if any(marker in value for marker in status_markers):
        return "status"
    return None


def local_reply(text: str, config: dict[str, Any] | None = None) -> str | None:
    intent = local_intent(text)
    if intent is None:
        return None
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    if not edit_aja_enabled(config):
        return None
    if intent == "api":
        return api_status(config)
    if intent == "model":
        return model_status(config)
    if intent == "status":
        return compact_status(config)
    return None
