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


def model_status(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}
    model = _model_config(config)
    main_model = str(model.get("default") or "unknown")
    provider = str(model.get("provider") or "unknown")
    light_model = str(
        _aux_config(config, "compression").get("model")
        or _aux_config(config, "title_generation").get("model")
        or main_model
    )
    return "\n".join([
        "🤖 **Edit Aja AI Model**",
        f"Provider: **{provider}**",
        f"Main model: `{main_model}`",
        f"Light model: `{light_model}`",
    ])


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


def api_snapshot(config: dict[str, Any] | None = None) -> dict[str, Any]:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}
    main_model = str(_model_config(config).get("default") or "")
    try:
        from agent.credential_pool import load_pool
        pool = load_pool("gemini")
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
            "label": str(getattr(entry, "label", "") or f"Gemini {index:02d}"),
            "priority": int(getattr(entry, "priority", index - 1) or 0),
            "state": _entry_state(
                entry, main_model=main_model, now=now, sole_credential=sole_credential
            ),
            "request_count": int(getattr(entry, "request_count", 0) or 0),
        })

    ready = [row for row in rows if row["state"] == "READY"]
    preferred = ready[0]["label"] if ready else None
    return {
        "rows": rows,
        "total": len(rows),
        "ready": sum(row["state"] == "READY" for row in rows),
        "cooldown": sum(row["state"] == "COOLDOWN" for row in rows),
        "dead": sum(row["state"] == "DEAD" for row in rows),
        "preferred": preferred,
    }


def api_status(config: dict[str, Any] | None = None) -> str:
    snap = api_snapshot(config)
    lines = [
        "🔑 **Gemini API Pool**",
        f"Keys: **{snap['total']}**  |  READY: **{snap['ready']}**  |  COOLDOWN: **{snap['cooldown']}**  |  DEAD: **{snap['dead']}**",
    ]
    for row in snap["rows"]:
        icon = "✅" if row["state"] == "READY" else "⏳" if row["state"] == "COOLDOWN" else "❌"
        lines.append(f"{icon} {row['label']}: **{row['state']}**")
    if snap["preferred"]:
        lines.append(f"Preferred next key: **{snap['preferred']}**")
    lines.extend([
        "",
        "Quota remaining (%): **not available reliably from Gemini API**.",
        "Edit Aja will not invent a percentage.",
    ])
    return "\n".join(lines)


def compact_status(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from hermes_cli.config import load_config
        config = load_config()
    config = config if isinstance(config, dict) else {}
    model = _model_config(config)
    snap = api_snapshot(config)
    light_model = str(
        _aux_config(config, "compression").get("model")
        or _aux_config(config, "title_generation").get("model")
        or model.get("default")
        or "unknown"
    )
    quiet = "ON" if _quiet_enabled(config) else "OFF"
    return "\n".join([
        "🟢 **EDIT AJA AI AGENT**",
        f"Gateway: **ONLINE** (PID {os.getpid()})",
        f"Provider: **{model.get('provider') or 'unknown'}**",
        f"Main model: `{model.get('default') or 'unknown'}`",
        f"Light model: `{light_model}`",
        f"Gemini keys: **{snap['total']}** ({snap['ready']} ready, {snap['cooldown']} cooldown, {snap['dead']} dead)",
        f"Quiet mode: **{quiet}**",
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
    # language so generic questions about "Gemini API" still reach the LLM.
    api_terms = ("api", "api key", "key gemini", "gemini key")
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
