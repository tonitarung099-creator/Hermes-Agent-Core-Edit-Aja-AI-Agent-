# Edit Aja AI Agent - recurring-free cloud configuration
# Primary: Cloudflare Workers AI / GLM-4.7-Flash
# Fallback: Groq / GPT-OSS 120B
# Gemini and Cerebras are not used by this profile.

param(
    [string]$CloudflareAccountId = "",
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
Write-Host " Edit Aja AI Agent - Recurring Free Cloud Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Recommended primary : Cloudflare Workers AI / $CloudflareModel"
Write-Host "Fallback            : Groq / $GroqModel"
Write-Host "Gemini              : DISABLED"
Write-Host "Cerebras            : DISABLED (not a recurring-free default)"
Write-Host ""
Write-Host "API credentials are stored by Hermes locally and are not written to GitHub."
Write-Host ""

if ([string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    $CloudflareAccountId = (Read-Host "Cloudflare Account ID (leave empty to use Groq as primary)").Trim()
}

$argsList = @(
    "-m", "hermes_cli.edit_aja_mode",
    "--cloudflare-model", $CloudflareModel,
    "--groq-model", $GroqModel
)
if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    $argsList += @("--cloudflare-account-id", $CloudflareAccountId)
} else {
    # Explicitly remove an old Cloudflare route if the user chose to skip it.
    $argsList += "--no-cloudflare"
}

Write-Host ""
Write-Host "Applying recurring-free Edit Aja routing..."
& $python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply Edit Aja recurring-free configuration."
}

$providersToList = @()

if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    Write-Host ""
    if (Ask-YesNo "Add a Cloudflare Workers AI API token now?" $true) {
        & $hermes auth add cloudflare --type api-key --label "Cloudflare 01"
        if ($LASTEXITCODE -ne 0) { throw "Could not add the Cloudflare API token." }
    }
    $providersToList += "cloudflare"
} else {
    Write-Host ""
    Write-Host "Cloudflare skipped. Groq will be the primary provider."
}

Write-Host ""
if (Ask-YesNo "Add a Groq API key now?" $true) {
    & $hermes auth add groq --type api-key --label "Groq 01"
    if ($LASTEXITCODE -ne 0) { throw "Could not add the Groq API key." }
}
$providersToList += "groq"

Write-Host ""
Write-Host "Configured active credential pools:"
foreach ($provider in $providersToList) {
    & $hermes auth list $provider
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not read the $provider credential pool. You can retry with: hermes auth list $provider"
    }
}

Write-Host ""
Write-Host "Recurring-free setup complete."
if (-not [string]::IsNullOrWhiteSpace($CloudflareAccountId)) {
    Write-Host "Primary : cloudflare / $CloudflareModel"
    Write-Host "Fallback: groq / $GroqModel"
} else {
    Write-Host "Primary : groq / $GroqModel"
    Write-Host "Fallback: none"
}
Write-Host "Gemini  : disabled for Edit Aja routing"
Write-Host "Cerebras: disabled for Edit Aja routing"
