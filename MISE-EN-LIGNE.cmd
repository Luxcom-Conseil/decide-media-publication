@echo off
rem Double-cliquez sur ce fichier : il met l'agent en ligne sur GitHub (une seule fois).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\mise_en_ligne.ps1"
pause
