# Edit Aja AI Agent - migrate an existing Windows install to recurring-free routing.
# Updates the fork, applies Cerebras-first + optional Cloudflare + Groq fallback, then reloads the gateway.

param(
    [string]$HermesHome = $(if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" })
)

$ErrorActionPreference = "Stop"
$HermesHome = [System.IO.Path]::GetFullPath($HermesHome)
$env:HERMES_HOME = $HermesHome

$hermes = Join-Path $HermesHome "bin\hermes.exe"
$repoDir = Join-Path $HermesHome "hermes-agent"

if (-not (Test-Path -LiteralPath $hermes)) {
    throw "Hermes launcher was not found at $hermes."
}
if (-not (Test-Path -LiteralPath $repoDir)) {
    throw "Hermes source/runtime directory was not found at $repoDir."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Edit Aja - Switch to Cerebras Free Cloud"
Write-Host "============================================================"
Write-Host ""
Write-Host "Install : $HermesHome"
Write-Host "Primary : Cerebras / gpt-oss-120b"
Write-Host "Fallback: Cloudflare optional -> Groq / openai/gpt-oss-120b"
Write-Host "Gemini  : disabled"
Write-Host "Cerebras: enabled as primary"
Write-Host ""

Write-Host "[1/4] Updating Edit Aja from GitHub main..."
& $hermes update --yes --branch main
if ($LASTEXITCODE -ne 0) {
    throw "Hermes update failed. The existing installation was left in place."
}

$setup = Join-Path $repoDir "scripts\configure-edit-aja-free-cloud.ps1"
if (-not (Test-Path -LiteralPath $setup)) {
    throw "Recurring-free setup helper was not found after update: $setup"
}

Write-Host ""
Write-Host "[2/4] Configuring Cerebras-first recurring-free routing..."
$setupText = Get-Content -LiteralPath $setup -Raw
& ([scriptblock]::Create($setupText))
if ($LASTEXITCODE -ne 0) {
    throw "Recurring-free AI setup failed."
}

Write-Host ""
Write-Host "[3/4] Reloading the Telegram gateway..."
& $hermes gateway restart
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Gateway restart did not complete. Trying a normal start."
    & $hermes gateway start
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restart or start the gateway."
    }
}

Write-Host ""
Write-Host "[4/4] Verifying gateway..."
& $hermes gateway status
if ($LASTEXITCODE -ne 0) {
    throw "Gateway status check failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Migration complete."
Write-Host " Telegram tests:"
Write-Host "   /model"
Write-Host "   /api"
Write-Host "   Buka Notepad di laptop saya"
Write-Host "============================================================"
