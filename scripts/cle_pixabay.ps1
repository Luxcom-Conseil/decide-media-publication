# Enregistre la clé API Pixabay (gratuite) (une seule fois) : dans .env pour le PC et dans le coffre « Secrets » de GitHub.
# Elle sert aux vidéos et photos réalistes de fond des Reels Instagram perso. La clé est saisie masquée et n'est jamais affichée.
# Obtenir la clé : créer un compte gratuit sur https://pixabay.com, puis ouvrir https://pixabay.com/api/docs/ :
# la clé est affichée dans la section « Parameters » (ligne « key », sur fond vert).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$depot = "Luxcom-Conseil/decide-media-publication"

# La clé est lue dans le presse-papiers (copiée juste avant sur pixabay.com) : le collage dans une saisie masquée ne
# marche pas dans tous les terminaux (panneau Terminal de Claude, 27/10/2026). Sinon, saisie masquée.
$cle = "$(Get-Clipboard)".Trim()
if ($cle -match '^\d+-[0-9a-f]{20,}$') {
    Write-Host "`nClé Pixabay trouvée dans le presse-papiers ($($cle.Length) caractères)."
    Set-Clipboard -Value " "  # on ne la laisse pas traîner dans le presse-papiers
} else {
    Write-Host "`nPas de clé Pixabay dans le presse-papiers. Collez-la (Ctrl+V), rien ne s'affiche, puis Entrée :" -ForegroundColor Cyan
    $saisie = Read-Host -AsSecureString
    $cle = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie)).Trim()
}
if ($cle.Length -lt 20) { throw "Ce n'est pas une clé Pixabay ($($cle.Length) caractères reçus)." }
try {
    Invoke-RestMethod "https://pixabay.com/api/videos/?key=$cle&q=people&per_page=3" | Out-Null
} catch {
    throw "Pixabay refuse cette clé. Vérifiez-la sur https://pixabay.com/api/docs/ et relancez."
}
Write-Host "    ✓ clé valide"

$lignes = @()
if (Test-Path .env) { $lignes = @(Get-Content .env -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*PIXABAY_API_KEY=' }) }
$lignes += "PIXABAY_API_KEY=$cle"
[IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), [string[]]$lignes, (New-Object Text.UTF8Encoding $false))
Write-Host "    ✓ enregistrée sur le PC"

$cle | gh secret set PIXABAY_API_KEY -R $depot *> $null
if ($LASTEXITCODE) { throw "Enregistrement dans GitHub refusé." }
Write-Host "    ✓ enregistrée dans GitHub"
Write-Host "`n✅ Terminé. Vous pouvez fermer cette fenêtre." -ForegroundColor Green
