# Enregistre la clé API Gemini (Google AI Studio, gratuite) (une seule fois) : dans .env pour le PC et dans le coffre « Secrets » de GitHub.
# Elle sert à écrire le script simplifié des Shorts (gabarit v2). La clé est saisie masquée et n'est jamais affichée.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$depot = "Luxcom-Conseil/decide-media-publication"

Write-Host "`nCollez la clé API Gemini, qui commence par AIza (clic droit pour coller ; rien ne s'affiche, c'est normal), puis Entrée :" -ForegroundColor Cyan
$saisie = Read-Host -AsSecureString
$cle = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie)).Trim()
if (-not $cle.StartsWith("AIza")) { throw "Ce n'est pas une clé Gemini (elle doit commencer par AIza)." }

$lignes = @()
if (Test-Path .env) { $lignes = @(Get-Content .env -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*GEMINI_API_KEY=' }) }
$lignes += "GEMINI_API_KEY=$cle"
[IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), [string[]]$lignes, (New-Object Text.UTF8Encoding $false))
Write-Host "    ✓ enregistrée sur le PC ($($cle.Length) caractères)"

$cle | gh secret set GEMINI_API_KEY -R $depot *> $null
if ($LASTEXITCODE) { throw "Enregistrement dans GitHub refusé." }
Write-Host "    ✓ enregistrée dans GitHub"
Write-Host "`n✅ Terminé. Vous pouvez fermer cette fenêtre." -ForegroundColor Green
