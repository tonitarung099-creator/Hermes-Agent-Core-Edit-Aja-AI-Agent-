# START HERE — Edit Aja AI Agent on Windows

This repository is the **Hermes Agent Core → Edit Aja AI Agent** fork.

## First milestone

Do not start by automating Filmora or the full Edit Aja workflow.

The first milestone is intentionally small:

1. Edit Aja AI Agent runs natively on Windows.
2. The Hermes gateway starts automatically when the Windows user logs in.
3. A private Telegram bot can reach the local agent.
4. A Telegram instruction such as **"Buka Notepad di laptop saya"** can trigger a local tool/action.
5. Only after this works reliably should video-editing workflows be added.

## Important behavior

The gateway can stay running all day without continuously sending screenshots to an LLM. It waits for messages/events and invokes the agent when work arrives.

The laptop still needs to be **powered on, logged in, connected to the internet, and not sleeping** for Telegram commands to reach the local Hermes gateway.

## Easy Windows install

Open **PowerShell** and run:

```powershell
iex (irm https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/install-edit-aja-windows.ps1)
```

The setup is interactive. It installs the fork, configures **Cerebras-first recurring-free Edit Aja mode**, lets you add Cloudflare and Groq credentials through Hermes' masked credential prompt, asks for Telegram configuration, registers gateway auto-start, and starts the gateway.

### Install on drive D (recommended when C is low on space)

The Edit Aja bootstrap supports a custom Hermes home. To put the agent, runtime, repository checkout, and large install caches on drive D:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/install-edit-aja-windows.ps1))) -HermesHome "D:\\EditAjaAI"
```

This keeps Hermes under `D:\\EditAjaAI` and also redirects the install-time uv/npm/Electron caches plus the persistent Playwright browser download to that location. The installer changes TEMP/TMP only for its own PowerShell process; it does not move Windows' global temp folder.

After installation, `HERMES_HOME` is persisted for the Windows user so gateway/autostart processes continue using the D: installation after reboot.

## AI provider preparation

Edit Aja no longer uses Gemini in its active routing profile.

Default routing:

- Primary: **Cloudflare Workers AI** — `@cf/zai-org/glm-4.7-flash`
- Vision/screenshots: **Cloudflare Gemma 4 26B** — `@cf/google/gemma-4-26b-a4b-it`
- Primary: **Cerebras** — `gpt-oss-120b`
- Optional extra free pool + vision: **Cloudflare Workers AI** — `@cf/zai-org/glm-4.7-flash` plus Gemma vision
- Fallback: **Groq** — `openai/gpt-oss-120b`
- Gemini: **disabled for Edit Aja routing**
- API retry count: **1** per provider call
- Automatic post-exhaustion retry loops: **disabled**
- Deterministic/local tools remain preferred before any LLM call

Prepare a **Cerebras API key** first; it is the primary Edit Aja provider. Also prepare a **Groq API key** as an independent fallback. Cloudflare is optional: if you provide an Account ID + Workers AI token, Edit Aja keeps it as an additional free fallback and dedicated vision route.

Credentials are entered through Hermes' masked prompt and stored locally in Hermes' credential pool. They are never committed to GitHub.

Inspect the pools with:

```powershell
hermes auth list cloudflare
hermes auth list groq
```

For Cloudflare Workers AI, the setup asks for your **Cloudflare Account ID** because the OpenAI-compatible endpoint includes it in the URL. Never paste the API token into GitHub or chat; enter it only at Hermes' masked credential prompt.

### Existing installation: switch away from Gemini

For an existing Windows install, use the migration helper. It updates the fork, applies the Cloudflare-first recurring-free profile, restarts the gateway, and verifies status:

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/switch-edit-aja-free-cloud.ps1"))) -HermesHome "D:\EditAjaAI"
```

The helper asks for Cerebras and Groq credentials through Hermes' masked prompts, with Cloudflare optional. Existing Gemini credentials may remain stored locally, but the Edit Aja profile will not route normal requests to Gemini.

## Telegram preparation

Before running the installer:

1. Open Telegram.
2. Open **@BotFather**.
3. Send `/newbot`.
4. Create the bot name and username.
5. Keep the bot token private.
6. Get your numeric Telegram user ID (for the Hermes allowlist).

Never commit Telegram bot tokens, AI provider keys/tokens, or any other secret to this repository.

## After setup

Useful commands:

```powershell
hermes gateway status
hermes gateway start
hermes gateway stop
hermes gateway restart
```

The Windows gateway auto-start is installed through Hermes' native `hermes gateway install` command.

## Development order

Keep the project progression in this order:

**Phase 1 — Foundation**
- Windows installation
- Cerebras-first recurring-free provider setup with Groq fallback and optional Cloudflare vision
- Groq fallback pool
- Telegram private access
- gateway auto-start
- local command execution

**Phase 2 — Laptop control**
- open/close applications
- file/folder operations
- process inspection
- browser control
- Windows UI automation
- screenshots/vision only when needed

**Phase 3 — Edit Aja integration**
- expose Edit Aja functions as deterministic local tools
- project/file discovery
- FFmpeg operations
- subtitle/video workflows
- task reporting back to Telegram

**Phase 4 — Long-running automation**
- scheduler/cron
- job queue
- recovery after failures
- notifications
- API/model routing and cost controls

The core rule is: **use deterministic/local tools first; call an LLM only when reasoning is actually needed.**

## Edit Aja local commands

These commands are handled locally by the gateway and do not need an LLM reasoning turn:

```text
/status        Compact Edit Aja runtime status
/model         Current primary + fallback model routes
/api           Cloudflare/Groq pool health (READY / COOLDOWN / DEAD)
/quiet on      Final-answer-first Telegram mode
/quiet off     Show technical progress again
/debug on      Alias for technical/debug display
/debug off     Return to Quiet Mode
```

Natural-language status questions such as **"model yang kamu pakai apa?"**, **"api saya ada berapa?"**, and **"gateway hidup?"** are also answered by the local router when Edit Aja mode is enabled.

The API status intentionally does **not** invent a remaining-quota percentage. Edit Aja reports locally observed credential health and provider errors instead of making up a quota percentage.

Quiet Mode is the Edit Aja default. Tool calls, redirect/queue acknowledgements, interim scratch messages, and long-running technical chatter are hidden from Telegram while final answers remain visible. Technical details remain available in local logs and can be shown again with `/debug on`.

