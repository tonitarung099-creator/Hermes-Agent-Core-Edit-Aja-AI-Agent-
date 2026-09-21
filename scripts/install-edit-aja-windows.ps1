# Edit Aja AI Agent - Windows bootstrap
# Installs the Edit Aja Hermes fork, configures free-cloud AI + messaging, and enables auto-start.
# No secrets are hard-coded in this file.

param(
    [string]$HermesHome = $(if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" })
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$HermesHome = [System.IO.Path]::GetFullPath($HermesHome)
$installDir = Join-Path $HermesHome "hermes-agent"
$cacheRoot = Join-Path $HermesHome ".cache"
$tempRoot = Join-Path $cacheRoot "temp"

# Keep the install and the large dependency caches on the same drive as Hermes.
# TEMP/TMP are process-scoped so this installer does not change Windows' global temp
# location. PLAYWRIGHT_BROWSERS_PATH is persisted because browser automation needs
# to find the downloaded browser again after a reboot.
foreach ($dir in @(
    $HermesHome,
    $cacheRoot,
    $tempRoot,
    (Join-Path $cacheRoot "uv"),
    (Join-Path $cacheRoot "npm"),
    (Join-Path $cacheRoot "electron"),
    (Join-Path $cacheRoot "ms-playwright")
)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$env:HERMES_HOME = $HermesHome
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:UV_CACHE_DIR = Join-Path $cacheRoot "uv"
$env:npm_config_cache = Join-Path $cacheRoot "npm"
$env:ELECTRON_CACHE = Join-Path $cacheRoot "electron"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $cacheRoot "ms-playwright"

[Environment]::SetEnvironmentVariable("HERMES_HOME", $HermesHome, "User")
[Environment]::SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH", $env:PLAYWRIGHT_BROWSERS_PATH, "User")

Write-Host ""
Write-Host "============================================================"
Write-Host " Edit Aja AI Agent - Windows Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Install location : $HermesHome"
Write-Host "Source/runtime   : $installDir"
Write-Host "Large caches     : $cacheRoot"
Write-Host ""
Write-Host "This setup will:"
Write-Host "  1. Install the Edit Aja Hermes fork"
Write-Host "  2. Configure Cerebras-first AI + optional Cloudflare/Groq fallback"
Write-Host "  3. Configure the Telegram gateway"
Write-Host "  4. Start Hermes automatically when you log in to Windows"
Write-Host ""
Write-Host "Before Telegram setup, create a bot with @BotFather and keep"
Write-Host "the bot token ready. Do NOT paste the token into GitHub."
Write-Host ""

$installerUrl = "https://raw.githubusercontent.com/tonitarung099-creator/Hermes-Agent-Core-Edit-Aja-AI-Agent-/main/scripts/install.ps1"
Write-Host "[1/4] Installing Edit Aja AI Agent..."
$installerText = Invoke-RestMethod $installerUrl
& ([scriptblock]::Create($installerText)) -SkipSetup -HermesHome $HermesHome -InstallDir $installDir
if ($LASTEXITCODE -ne 0) {
    throw "Edit Aja AI Agent installation did not complete successfully."
}

$hermes = Join-Path $HermesHome "bin\hermes.exe"
if (-not (Test-Path -LiteralPath $hermes)) {
    throw "Hermes launcher was not found at $hermes"
}

Write-Host ""
Write-Host "[2/4] Cerebras-first free-cloud AI setup..."
$aiSetup = Join-Path $installDir "scripts\configure-edit-aja-free-cloud.ps1"
if (-not (Test-Path -LiteralPath $aiSetup)) {
    throw "Free-cloud setup helper was not found at $aiSetup"
}
$aiSetupText = Get-Content -LiteralPath $aiSetup -Raw
& ([scriptblock]::Create($aiSetupText))
if ($LASTEXITCODE -ne 0) {
    throw "Free-cloud AI setup did not complete successfully."
}

Write-Host ""
Write-Host "[3/4] Telegram setup..."
Write-Host "Choose Telegram and enter your BotFather token + allowed Telegram user ID."
& $hermes gateway setup
if ($LASTEXITCODE -ne 0) {
    throw "Telegram gateway setup did not complete successfully."
}

Write-Host ""
Write-Host "[4/4] Enabling Hermes at Windows login and starting the gateway..."
& $hermes gateway install
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the Hermes gateway auto-start task."
}

& $hermes gateway start
if ($LASTEXITCODE -ne 0) {
    throw "Could not start the Hermes gateway."
}

Write-Host ""
& $hermes gateway status

Write-Host ""
Write-Host "============================================================"
Write-Host " Setup complete."
Write-Host " Installed at: $HermesHome"
Write-Host " Open Telegram and send a message to your bot."
Write-Host " First test: 'Buka Notepad di laptop saya.'"
Write-Host "============================================================"
