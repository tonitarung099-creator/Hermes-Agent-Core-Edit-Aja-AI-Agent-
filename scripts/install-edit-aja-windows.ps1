# Edit Aja AI Agent - Windows bootstrap
# Installs the Edit Aja Hermes fork, configures messaging, and enables auto-start.
# No secrets are hard-coded in this file.

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host ""
Write-Host "============================================================"
Write-Host " Edit Aja AI Agent - Windows Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "This setup will:"
Write-Host "  1. Install the Edit Aja Hermes fork"
Write-Host "  2. Run the normal Hermes model/provider setup"
Write-Host "  3. Configure the Telegram gateway"
Write-Host "  4. Start Hermes automatically when you log in to Windows"
Write-Host ""
Write-Host "Before Telegram setup, create a bot with @BotFather and keep"
Write-Host "the bot token ready. Do NOT paste the token into GitHub."
Write-Host ""

$installerUrl = "https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/install.ps1"
Write-Host "[1/4] Installing Edit Aja AI Agent..."
$installerText = Invoke-RestMethod $installerUrl
& ([scriptblock]::Create($installerText))

$hermes = Join-Path $env:LOCALAPPDATA "hermes\bin\hermes.exe"
if (-not (Test-Path -LiteralPath $hermes)) {
    throw "Hermes launcher was not found at $hermes"
}

Write-Host ""
Write-Host "[2/4] Telegram setup..."
Write-Host "Choose Telegram and enter your BotFather token + allowed Telegram user ID."
& $hermes gateway setup
if ($LASTEXITCODE -ne 0) {
    throw "Telegram gateway setup did not complete successfully."
}

Write-Host ""
Write-Host "[3/4] Enabling Hermes at Windows login..."
& $hermes gateway install
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the Hermes gateway auto-start task."
}

Write-Host ""
Write-Host "[4/4] Starting Hermes gateway..."
& $hermes gateway start
if ($LASTEXITCODE -ne 0) {
    throw "Could not start the Hermes gateway."
}

Write-Host ""
& $hermes gateway status

Write-Host ""
Write-Host "============================================================"
Write-Host " Setup complete."
Write-Host " Open Telegram and send a message to your bot."
Write-Host " First test: 'Buka Notepad di laptop saya.'"
Write-Host "============================================================"
