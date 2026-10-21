# Envoie les dernières modifications sur GitHub ; avec -Essai, lance aussi un Short d'essai (rien n'est publié).
param([switch]$Essai)
Set-Location (Split-Path $PSScriptRoot -Parent)
git pull --rebase -q
git push -q
if ($Essai) { gh workflow run publier.yml -R Luxcom-Conseil/decide-media-publication -f commande=essai-video }
Write-Host "✅ Envoyé." -ForegroundColor Green
