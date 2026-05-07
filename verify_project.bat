@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   PROJECT VERIFICATION SCRIPT
echo ========================================
echo.

:: Colors for output (using echo with special characters)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "NC=[0m"

echo [Step 1/5] Checking Docker Status...
echo ----------------------------------------
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%NC% Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
) else (
    echo %GREEN%[PASS]%NC% Docker is running
)
echo.

echo [Step 2/5] Checking Container Status...
echo ----------------------------------------
docker-compose ps
echo.

echo [Step 3/5] Testing Backend Health...
echo ----------------------------------------
curl -s http://localhost:8000/api/v1/health/ > temp_health.json 2>nul
if errorlevel 1 (
    echo %RED%[FAIL]%NC% Backend is not responding
    echo.
    echo Checking backend logs:
    docker-compose logs backend --tail=20
) else (
    type temp_health.json
    echo.
    echo %GREEN%[PASS]%NC% Backend is healthy
    del temp_health.json
)
echo.

echo [Step 4/5] Testing Frontend...
echo ----------------------------------------
curl -s http://localhost:3000/health > nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%NC% Frontend is not responding
) else (
    echo %GREEN%[PASS]%NC% Frontend is accessible
)
echo.

echo [Step 5/5] Checking API Keys Configuration...
echo ----------------------------------------
findstr /C:"YOUR_GOOGLE_API_KEY_HERE" "backend\.env" >nul 2>&1
if not errorlevel 1 (
    echo %YELLOW%[WARN]%NC% Google API Key not configured
    echo Please add your API key to backend\.env
) else (
    echo %GREEN%[PASS]%NC% Google API Key is configured
)

findstr /C:"YOUR_PINECONE_API_KEY_HERE" "backend\.env" >nul 2>&1
if not errorlevel 1 (
    echo %YELLOW%[WARN]%NC% Pinecone API Key not configured
    echo Please add your API key to backend\.env
) else (
    echo %GREEN%[PASS]%NC% Pinecone API Key is configured
)
echo.

echo ========================================
echo   VERIFICATION COMPLETE
echo ========================================
echo.
echo Access URLs:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo Next Steps:
echo   1. Open http://localhost:3000 in browser
echo   2. Register a new account
echo   3. Upload a PDF or audio file
echo   4. Ask questions about the content
echo.
pause
