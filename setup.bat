@echo off
echo ========================================
echo   AI Document Q&A Platform - Setup
echo ========================================
echo.

:menu
echo.
echo Select an option:
echo [1] Check Prerequisites
echo [2] Generate Secret Key
echo [3] Edit .env file
echo [4] Start Application (Docker)
echo [5] Stop Application
echo [6] View Logs
echo [7] Clean Everything (Reset)
echo [8] Health Check
echo [9] Exit
echo.
set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto check_prereq
if "%choice%"=="2" goto generate_key
if "%choice%"=="3" goto edit_env
if "%choice%"=="4" goto start_app
if "%choice%"=="5" goto stop_app
if "%choice%"=="6" goto view_logs
if "%choice%"=="7" goto clean_all
if "%choice%"=="8" goto health_check
if "%choice%"=="9" goto end
goto menu

:check_prereq
echo.
echo Checking prerequisites...
echo.
docker --version
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo Download from: https://www.docker.com/products/docker-desktop
) else (
    echo [OK] Docker is installed
)
echo.
docker-compose --version
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed!
) else (
    echo [OK] Docker Compose is installed
)
echo.
git --version
if errorlevel 1 (
    echo [WARNING] Git is not installed
) else (
    echo [OK] Git is installed
)
echo.
pause
goto menu

:generate_key
echo.
echo Generating SECRET_KEY...
echo.
python -c "import secrets; print('Your SECRET_KEY:', secrets.token_hex(32))"
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Alternative: Use online generator - https://generate-secret.vercel.app/32
)
echo.
echo Copy this key and paste it in .env file
pause
goto menu

:edit_env
echo.
echo Opening backend/.env file in notepad...
notepad backend\.env
echo.
echo Make sure you have filled:
echo - SECRET_KEY
echo - GOOGLE_API_KEY
echo - PINECONE_API_KEY
echo - PINECONE_ENVIRONMENT
pause
goto menu

:start_app
echo.
echo Starting application with Docker Compose...
echo This will take 2-5 minutes on first run...
echo.
docker-compose up --build -d
if errorlevel 1 (
    echo [ERROR] Failed to start application
    echo Check if Docker Desktop is running
    pause
    goto menu
)
echo.
echo ========================================
echo   Application Started Successfully!
echo ========================================
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Use option [6] to view logs
echo Use option [8] to check health
pause
goto menu

:stop_app
echo.
echo Stopping application...
docker-compose down
echo Application stopped.
pause
goto menu

:view_logs
echo.
echo Viewing logs (Press Ctrl+C to exit)...
echo.
docker-compose logs -f
goto menu

:clean_all
echo.
echo WARNING: This will delete all containers, volumes, and data!
set /p confirm="Are you sure? (yes/no): "
if /i "%confirm%"=="yes" (
    echo Cleaning everything...
    docker-compose down -v
    docker system prune -f
    echo Cleanup complete!
) else (
    echo Cancelled.
)
pause
goto menu

:health_check
echo.
echo Checking application health...
echo.
curl -s http://localhost:8000/api/v1/health/ 2>nul
if errorlevel 1 (
    echo [ERROR] Backend is not responding
    echo Make sure application is running (option 4)
) else (
    echo [OK] Backend is healthy
)
echo.
curl -s http://localhost:3000 2>nul
if errorlevel 1 (
    echo [ERROR] Frontend is not responding
) else (
    echo [OK] Frontend is accessible
)
pause
goto menu

:end
echo.
echo Goodbye!
exit
