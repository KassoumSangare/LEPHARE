@echo off
REM LE PHARE en production : API sous waitress (serveur_production.py) et interface compilee (vite preview).
REM Remplace "python manage.py runserver" et "npm run dev", serveurs de developpement trop lents en production.
REM Voir LISEZMOI_PRODUCTION.md
cd /d "%~dp0"

set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

%PY% -c "import waitress" 2>nul
if errorlevel 1 (
  echo Installation de waitress...
  %PY% -m pip install waitress || goto erreur
)

start "LEPHARE API (waitress)" cmd /k "%PY% serveur_production.py"

cd frontend
echo Compilation de l'interface (npm run build)...
call npm run build || goto erreur
start "LEPHARE Interface (vite preview)" cmd /k "npm run preview"
echo.
echo LE PHARE demarre : http://localhost:3000
exit /b 0

:erreur
echo.
echo Le demarrage a echoue : lisez le message ci-dessus.
pause
exit /b 1
