@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "VENV_PY=%PROJECT_DIR%venv\Scripts\python.exe"
set "PORT=8501"

echo ============================================
echo   AllTokens Chat - быстрый запуск
echo ============================================
echo.

REM === Сброс предыдущего запуска и очистка кэша ========================
echo [RESET] Останавливаю предыдущие процессы Streamlit/Python...

REM 1) Убиваем процессы, слушающие порт Streamlit
set "KILLED=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R "[: ]%PORT% .*LISTENING"') do (
    taskkill /F /PID %%P >nul 2>&1
    if not errorlevel 1 set "KILLED=1"
)

REM 2) Убиваем все процессы streamlit на всякий случай
taskkill /F /IM streamlit.exe >nul 2>&1

REM 3) Убиваем python.exe, оставшиеся от прошлого запуска из нашего venv
for /f "delims=" %%P in ('
    powershell -NoProfile -Command "$vw=[Environment]::GetEnvironmentVariable('VIRTUAL_ENV','Process'); Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine -match [regex]::Escape($vw) } | ForEach-Object { $_.ProcessId }"
') do (
    if not "%%P"=="" taskkill /F /PID %%P >nul 2>&1
)

REM Даём ОС освободить порт
timeout /t 2 /nobreak >nul

REM === Очистка кэша ====================================================
echo [CLEAN] Очищаю кэш (__pycache__, .streamlit, .pytest_cache)...

REM Python bytecode
for /d /r "%PROJECT_DIR%" %%D in (__pycache__) do @if exist "%%D" rd /s /q "%%D" >nul 2>&1
del /s /q "%PROJECT_DIR%*.pyc" >nul 2>&1

REM Streamlit cache
if exist "%PROJECT_DIR%\.streamlit\cache" rd /s /q "%PROJECT_DIR%\.streamlit\cache" >nul 2>&1
if exist "%USERPROFILE%\.streamlit\cache" rd /s /q "%USERPROFILE%\.streamlit\cache" >nul 2>&1

REM Прочие кэши
if exist "%PROJECT_DIR%\.pytest_cache" rd /s /q "%PROJECT_DIR%\.pytest_cache" >nul 2>&1
if exist "%PROJECT_DIR%\.ruff_cache"     rd /s /q "%PROJECT_DIR%\.ruff_cache"     >nul 2>&1
if exist "%PROJECT_DIR%\.mypy_cache"     rd /s /q "%PROJECT_DIR%\.mypy_cache"     >nul 2>&1

if "%KILLED%"=="1" (
    echo [OK]    Старый процесс на порту %PORT% остановлен.
) else (
    echo [OK]    Активных процессов не было.
)
echo.

REM --- Проверка venv ---------------------------------------------------
if not exist "%VENV_PY%" (
    echo [INFO] venv не найден, создаю...
    py -3 -m venv venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать venv. Установите Python 3.10+
        pause
        exit /b 1
    )
)

REM --- Проверка/установка зависимостей ----------------------------------
"%VENV_PY%" -c "import streamlit, openai, dotenv" 2>nul
if errorlevel 1 (
    echo [INFO] Устанавливаю зависимости из requirements.txt...
    "%VENV_PY%" -m pip install --upgrade pip >nul
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Не удалось установить зависимости.
        pause
        exit /b 1
    )
)

REM --- Проверка .env ----------------------------------------------------
if not exist ".env" (
    echo [WARN] Файл .env не найден. Создайте его и укажите ALLTOKENS_API_KEY
    notepad .env
)

echo.
echo Выберите режим запуска:
echo   1 - Веб-интерфейс (Streamlit)   http://localhost:8501
echo   2 - Чат в консоли               python chat.py
echo   3 - Установить/обновить зависимости
echo   0 - Выход
echo.
set /p MODE="Ваш выбор [1]: "

if "%MODE%"=="" set "MODE=1"

if "%MODE%"=="1" goto :streamlit
if "%MODE%"=="2" goto :console
if "%MODE%"=="3" goto :deps
if "%MODE%"=="0" exit /b 0
echo [ERROR] Неверный выбор.
pause
exit /b 1

:streamlit
echo.
echo [START] Запускаю Streamlit на http://localhost:8501
echo         Для остановки нажмите Ctrl+C
echo.
"%VENV_PY%" -m streamlit run app.py --server.port %PORT% --server.headless false --browser.gatherUsageStats false
goto :end

:console
echo.
echo [START] Запускаю консольный чат (для выхода: exit)
echo.
"%VENV_PY%" chat.py
goto :end

:deps
echo.
echo [UPDATE] Обновляю зависимости...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt --upgrade
pause
goto :end

:end
endlocal