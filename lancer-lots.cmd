@echo off
rem Lancé par la tâche planifiée Windows « Publication DECIDE MEDIA » : programme le lot du jour.
cd /d "%~dp0"
"%USERPROFILE%\.sapv\Scripts\python.exe" -m agent lots >> "%~dp0etat\journal-lots.log" 2>&1
