@echo off
rem Double-cliquez sur ce fichier pour enregistrer la clé API du second compte Buffer (« Histoires vraies d'argent »).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cle_buffer.ps1" -Nom BUFFER_API_KEY_HISTOIRES
pause
