@echo off
REM Android: run with a conda env or venv already active (e.g. conda activate wa)
cd /d "%~dp0"
python -m pip install --disable-pip-version-check -q -r requirements.txt || exit /b 1
python android_pipeline.py %*
if not "%ERRORLEVEL%"=="0" pause
