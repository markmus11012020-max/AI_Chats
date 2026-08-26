@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "VENV_PY=%PROJECT_DIR%venv\Scripts\python.exe"

echo ============================================
echo   AllTokens Chat - быстрый запуск
echo ============================================
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
"%VENV_PY%" -m streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false
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