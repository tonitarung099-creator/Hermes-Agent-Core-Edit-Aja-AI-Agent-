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

The setup is interactive. It installs the fork, runs Hermes setup, asks for Telegram configuration, registers gateway auto-start, and starts the gateway.

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
- model/provider setup
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
