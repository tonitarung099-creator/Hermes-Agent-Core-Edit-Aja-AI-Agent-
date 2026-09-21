# Edit Aja AI Agent - free-cloud configuration
# Primary: Cerebras GPT-OSS 120B
# Fallback: Cloudflare Workers AI (optional) -> Groq
# Gemini is not used by this profile.

param(
    [string]$CloudflareAccountId = "",
    [string]$MainModel = "gpt-oss-120b",
    [string]$CloudflareModel = "@cf/zai-org/glm-4.7-flash",
    [string]$GroqModel = "openai/gpt-oss-120b"
)

$ErrorActionPreference = "Stop"

$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$hermes = Join-Path $hermesHome "bin\hermes.exe"
$python = Join-Path $hermesHome "hermes-agent\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $hermes)) {
    throw "Hermes launcher was not found at $hermes. Install Edit Aja AI Agent first."
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Hermes Python runtime was not found at $python."
}

function Ask-YesNo([string]$Prompt, [bool]$DefaultYes = $true) {
    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    $answer = (Read-Host "$Prompt $suffix").Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer -in @("y", "yes")
}

Write-Host ""
Write-Host "============================================================"
Write-Host " Edit Aja AI Agent - Free Cloud Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Primary : Cerebras / $MainModel"
Write-Host "Fallback: Cloudflare Workers AI -> Groq"
Write-Host "Gemini  : DISABLED for Edit Aja routing"
Write-Host ""
Write-Host "API keys are stored by Hermes locally and are not written to GitHub."
Write-Host ""

if ([string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    $CloudflareAccountId = (Read-Host "Cloudflare Account ID (leave empty to skip Cloudflare fallback)").Trim()
}

$argsList = @(
    "-m", "hermes_cli.edit_aja_mode",
    "--main-model", $MainModel,
    "--cloudflare-model", $CloudflareModel,
    "--groq-model", $GroqModel
)
if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    $argsList += @("--cloudflare-account-id", $CloudflareAccountId)
}

Write-Host ""
Write-Host "Applying Cerebras-first Edit Aja routing..."
& $python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply Edit Aja free-cloud configuration."
}

Write-Host ""
if (Ask-YesNo "Add a Cerebras API key now?" $true) {
    & $hermes auth add cerebras --type api-key --label "Cerebras 01"
    if ($LASTEXITCODE -ne 0) { throw "Could not add the Cerebras API key." }
}

if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    Write-Host ""
    if (Ask-YesNo "Add a Cloudflare Workers AI API token now?" $true) {
        & $hermes auth add cloudflare --type api-key --label "Cloudflare 01"
        if ($LASTEXITCODE -ne 0) { throw "Could not add the Cloudflare API token." }
    }
}

Write-Host ""
if (Ask-YesNo "Add a Groq API key now?" $true) {
    & $hermes auth add groq --type api-key --label "Groq 01"
    if ($LASTEXITCODE -ne 0) { throw "Could not add the Groq API key." }
}

Write-Host ""
Write-Host "Configured credential pools:"
$providersToList = @("cerebras")
if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    $providersToList += "cloudflare"
}
$providersToList += "groq"
foreach ($provider in $providersToList) {
    & $hermes auth list $provider
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not read the $provider credential pool. The provider configuration was kept; you can retry with: hermes auth list $provider"
    }
}

Write-Host ""
Write-Host "Free-cloud setup complete."
Write-Host "Primary : cerebras / $MainModel"
if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    Write-Host "Fallback: cloudflare / $CloudflareModel -> groq / $GroqModel"
} else {
    Write-Host "Fallback: groq / $GroqModel"
}
Write-Host "Gemini  : disabled for Edit Aja routing"
