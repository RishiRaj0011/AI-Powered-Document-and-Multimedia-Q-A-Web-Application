@echo off
REM =============================================================================
REM Infrastructure Health Check Script (Windows)
REM =============================================================================

echo.
echo ========================================
echo   Infrastructure Health Check
echo ========================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check Docker Compose services
echo Checking Docker Compose services...
docker compose ps

echo.
echo Checking individual services...

REM Check PostgreSQL
docker compose exec -T postgres pg_isready -U docqa >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] PostgreSQL is ready
) else (
    echo [ERROR] PostgreSQL is not ready
)

REM Check Redis
docker compose exec -T redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis is ready
) else (
    echo [ERROR] Redis is not ready
)

REM Check Backend Health
echo.
echo Checking Backend API...
curl -s http://localhost:8000/api/v1/health/ >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Backend API is responding
) else (
    echo [ERROR] Backend API is not responding
)

REM Check Frontend
echo.
echo Checking Frontend...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend is accessible
) else (
    echo [ERROR] Frontend is not accessible
)

echo.
echo ========================================
echo   Health Check Complete
echo ========================================
echo.
echo Service URLs:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.

pause
