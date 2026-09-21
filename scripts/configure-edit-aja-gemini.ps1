# Compatibility wrapper.
# Gemini routing was retired from Edit Aja. This file remains so old install
# instructions do not accidentally re-enable Gemini.

param(
    [int]$KeyCount = 0,
    [string]$MainModel = "",
    [string]$LightModel = ""
)

$ErrorActionPreference = "Stop"

$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$replacement = Join-Path $hermesHome "hermes-agent\scripts\configure-edit-aja-free-cloud.ps1"

Write-Host ""
Write-Host "Gemini setup has been retired from Edit Aja."
Write-Host "Switching to Cerebras-first free-cloud setup instead."
Write-Host ""

if (-not (Test-Path -LiteralPath $replacement)) {
    throw "Free-cloud setup helper was not found at $replacement."
}

$replacementText = Get-Content -LiteralPath $replacement -Raw
& ([scriptblock]::Create($replacementText))
