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

The setup is interactive. It installs the fork, configures **Gemini-only Edit Aja mode**, lets you add Gemini API keys through Hermes' masked credential prompt, asks for Telegram configuration, registers gateway auto-start, and starts the gateway.

### Install on drive D (recommended when C is low on space)

The Edit Aja bootstrap supports a custom Hermes home. To put the agent, runtime, repository checkout, and large install caches on drive D:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/install-edit-aja-windows.ps1))) -HermesHome "D:\\EditAjaAI"
```

This keeps Hermes under `D:\\EditAjaAI` and also redirects the install-time uv/npm/Electron caches plus the persistent Playwright browser download to that location. The installer changes TEMP/TMP only for its own PowerShell process; it does not move Windows' global temp folder.

After installation, `HERMES_HOME` is persisted for the Windows user so gateway/autostart processes continue using the D: installation after reboot.

## Gemini preparation

Create at least one Gemini API key in Google AI Studio before installing. The Edit Aja fork accepts **Gemini Free Tier** keys; it does not require billing.

During setup, each key is entered through Hermes' masked prompt and stored locally in its credential pool. Keys are never committed to GitHub.

You can add another independently authorized key later with:

```powershell
hermes auth add gemini --type api-key --label "Gemini 02"
```

Inspect the pool with:

```powershell
hermes auth list gemini
hermes auth status gemini
```

Edit Aja uses `fill_first`: one preferred credential stays stable and Hermes' existing health/cooldown logic can move away from a credential that is unavailable. Respect Google's account and quota terms; do not use credential pools to circumvent provider limits.

Default routing installed by Edit Aja:

- Main reasoning / agent model: `gemini-3.7-flash`
- Lightweight side tasks: `gemini-3.5-flash-lite`
- Vision/review-heavy tasks: main Gemini model
- Other cloud-provider fallback chain: disabled
- Local tools remain preferred for deterministic computer work

## Telegram preparation

Before running the installer:

1. Open Telegram.
2. Open **@BotFather**.
3. Send `/newbot`.
4. Create the bot name and username.
5. Keep the bot token private.
6. Get your numeric Telegram user ID (for the Hermes allowlist).

Never commit Telegram bot tokens, Gemini keys, or any other secret to this repository.

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
- Gemini-only provider setup
- local Gemini credential pool
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

These commands are handled locally by the gateway and do not need a Gemini reasoning turn:

```text
/status        Compact Edit Aja runtime status
/model         Current Gemini main/light models
/api           Gemini credential-pool health (READY / COOLDOWN / DEAD)
/quiet on      Final-answer-first Telegram mode
/quiet off     Show technical progress again
/debug on      Alias for technical/debug display
/debug off     Return to Quiet Mode
```

Natural-language status questions such as **"model yang kamu pakai apa?"**, **"api saya ada berapa?"**, and **"gateway hidup?"** are also answered by the local router when Edit Aja mode is enabled.

The API status intentionally does **not** invent a remaining-quota percentage. Gemini does not provide a reliable per-key percentage through the inference path used here, so Edit Aja reports only locally observed credential health.

Quiet Mode is the Edit Aja default. Tool calls, redirect/queue acknowledgements, interim scratch messages, and long-running technical chatter are hidden from Telegram while final answers remain visible. Technical details remain available in local logs and can be shown again with `/debug on`.

