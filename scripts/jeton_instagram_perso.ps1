# Enregistre le jeton du compte Instagram personnel (connexion Instagram directe, sans Page Facebook) :
# dans .env pour le PC et dans le coffre « Secrets » de GitHub, avec une clé de chiffrement qui permet à l'agent de
# renouveler le jeton tout seul chaque semaine. Le jeton est saisi masqué et n'est jamais affiché.
#
# Avant : developers.facebook.com > votre application > Instagram > « API setup with Instagram login » >
# « Generate token » à côté du compte stephane_nzesseu (testeur Instagram accepté dans l'app Instagram).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$depot = "Luxcom-Conseil/decide-media-publication"
$python = Join-Path $env:USERPROFILE ".sapv\Scripts\python.exe"

Write-Host "`nCollez le jeton Instagram (clic droit pour coller ; rien ne s'affiche, c'est normal), puis Entrée :" -ForegroundColor Cyan
$saisie = Read-Host -AsSecureString
$jeton = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($saisie)).Trim()
if ($jeton.Length -lt 50) { throw "Ce n'est pas un jeton Instagram ($($jeton.Length) caractères reçus)." }

try {
    $moi = Invoke-RestMethod "https://graph.instagram.com/me?fields=user_id,username&access_token=$jeton"
} catch {
    throw "Instagram refuse ce jeton. Régénérez-le dans le tableau de bord Meta et relancez."
}
Write-Host "    ✓ jeton valide pour @$($moi.username)"

$cle = & $python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if ($LASTEXITCODE -or -not $cle) { throw "Impossible de créer la clé de chiffrement." }

$lignes = @()
if (Test-Path .env) { $lignes = @(Get-Content .env -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*INSTAGRAM_PERSO_(TOKEN|CLE)=' }) }
$lignes += "INSTAGRAM_PERSO_TOKEN=$jeton"
$lignes += "INSTAGRAM_PERSO_CLE=$cle"
[IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), [string[]]$lignes, (New-Object Text.UTF8Encoding $false))
Write-Host "    ✓ enregistré sur le PC"

$jeton | gh secret set INSTAGRAM_PERSO_TOKEN -R $depot *> $null
if ($LASTEXITCODE) { throw "Enregistrement du jeton dans GitHub refusé." }
$cle | gh secret set INSTAGRAM_PERSO_CLE -R $depot *> $null
if ($LASTEXITCODE) { throw "Enregistrement de la clé dans GitHub refusé." }
Write-Host "    ✓ enregistré dans GitHub"
Write-Host "`n✅ Terminé. Vous pouvez fermer cette fenêtre." -ForegroundColor Green
