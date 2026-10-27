# Enregistre la clé API Pexels (gratuite) (une seule fois) : dans .env pour le PC et dans le coffre « Secrets » de GitHub.
# Elle sert aux vidéos et photos réalistes de fond des Reels Instagram perso. La clé est saisie masquée et n'est jamais affichée.
# Obtenir la clé : https://www.pexels.com/api/ > « Get started » (compte gratuit), puis copier la clé affichée.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$depot = "Luxcom-Conseil/decide-media-publication"

Write-Host "`nCollez la clé API Pexels (clic droit pour coller ; rien ne s'affiche, c'est normal), puis Entrée :" -ForegroundColor Cyan
$saisie = Read-Host -AsSecureString
$cle = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie)).Trim()
if ($cle.Length -lt 30) { throw "Ce n'est pas une clé Pexels ($($cle.Length) caractères reçus)." }
try {
    Invoke-RestMethod "https://api.pexels.com/v1/search?query=people&per_page=1" -Headers @{ Authorization = $cle } | Out-Null
} catch {
    throw "Pexels refuse cette clé. Vérifiez-la sur https://www.pexels.com/api/ et relancez."
}
Write-Host "    ✓ clé valide"

$lignes = @()
if (Test-Path .env) { $lignes = @(Get-Content .env -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*PEXELS_API_KEY=' }) }
$lignes += "PEXELS_API_KEY=$cle"
[IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), [string[]]$lignes, (New-Object Text.UTF8Encoding $false))
Write-Host "    ✓ enregistrée sur le PC"

$cle | gh secret set PEXELS_API_KEY -R $depot *> $null
if ($LASTEXITCODE) { throw "Enregistrement dans GitHub refusé." }
Write-Host "    ✓ enregistrée dans GitHub"
Write-Host "`n✅ Terminé. Vous pouvez fermer cette fenêtre." -ForegroundColor Green
