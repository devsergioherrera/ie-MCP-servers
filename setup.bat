@echo off
echo Configurando hooks de Git...
git config core.hooksPath .githooks
echo.
echo Hooks configurados correctamente.
echo Recuerda:
echo   1. Editar .openproject.conf con el PROJECT_ID de tu proyecto
echo   2. Configurar tu API key:
echo      [Environment]::SetEnvironmentVariable("OPENPROJECT_API_KEY","TU_KEY","User")
echo.
pause
