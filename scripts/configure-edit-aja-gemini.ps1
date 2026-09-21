# Edit Aja AI Agent - Gemini-only configuration
# API keys are entered through Hermes' masked prompt and are never written here.

param(
    [int]$KeyCount = 0,
    [string]$MainModel = "gemini-3.7-flash",
    [string]$LightModel = "gemini-3.5-flash-lite"
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

Write-Host ""
Write-Host "============================================================"
Write-Host " Edit Aja AI Agent - Gemini Setup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Gemini API keys are stored by Hermes locally, not in GitHub."
Write-Host "Only add credentials you are authorized to use and respect Google's quotas."
Write-Host ""

if ($KeyCount -le 0) {
    $answer = Read-Host "How many Gemini API keys do you want to add now? [1]"
    if ([string]::IsNullOrWhiteSpace($answer)) {
        $KeyCount = 1
    } elseif (-not [int]::TryParse($answer, [ref]$KeyCount) -or $KeyCount -lt 1) {
        throw "Key count must be a positive whole number."
    }
}

for ($i = 1; $i -le $KeyCount; $i++) {
    $label = "Gemini {0:D2}" -f $i
    Write-Host ""
    Write-Host "Adding $label ..."
    Write-Host "Paste the API key into Hermes' masked prompt."
    & $hermes auth add gemini --type api-key --label $label
    if ($LASTEXITCODE -ne 0) {
        throw "Could not add $label."
    }
}

Write-Host ""
Write-Host "Applying Gemini-only Edit Aja routing..."
& $python -m hermes_cli.edit_aja_mode --main-model $MainModel --light-model $LightModel
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply Edit Aja Gemini-only configuration."
}

Write-Host ""
Write-Host "Gemini credential pool:"
& $hermes auth list gemini

Write-Host ""
Write-Host "Gemini setup complete."
Write-Host "Main model : $MainModel"
Write-Host "Light model: $LightModel"
