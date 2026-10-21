# Mise en ligne sur GitHub (une seule fois) : autorisation, accès secrets, envoi du code, test.
# Les valeurs des accès ne sont jamais affichées : elles vont directement du PC au coffre « Secrets » du dépôt.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$depot = "Luxcom-Conseil/decide-media-publication"

Write-Host "`n1/4  Autorisation GitHub : une page s'ouvre, cliquez sur « Authorize »." -ForegroundColor Cyan
gh auth refresh -h github.com -s workflow
if ($LASTEXITCODE) { throw "Autorisation GitHub non accordée." }

Write-Host "`n2/4  Envoi des accès (Facebook, YouTube) dans le coffre du dépôt..." -ForegroundColor Cyan
gh secret set -f .env -R $depot
$cle = Get-ChildItem "$env:USERPROFILE\Downloads\decide-publication-*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $cle) { throw "Clé Google Drive (decide-publication-….json) introuvable dans Téléchargements." }
Get-Content $cle.FullName -Raw | gh secret set GOOGLE_SERVICE_ACCOUNT_JSON -R $depot
Write-Host "    Accès enregistrés :"; gh secret list -R $depot

Write-Host "`n3/4  Envoi du code..." -ForegroundColor Cyan
git push -u origin main
if ($LASTEXITCODE) { throw "Envoi du code refusé." }

Write-Host "`n4/4  Test des accès depuis GitHub (rien n'est publié)..." -ForegroundColor Cyan
Start-Sleep -Seconds 5
gh workflow run publier.yml -R $depot -f commande=verifier
Write-Host "`n✅ Terminé. Vous pouvez fermer cette fenêtre." -ForegroundColor Green
