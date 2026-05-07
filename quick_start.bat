@echo off
echo ========================================
echo   AI Document Q&A - Quick Start
echo ========================================
echo.

echo Step 1: Stopping old containers...
docker-compose down
echo.

echo Step 2: Starting fresh build...
echo (This will take 2-5 minutes on first run)
docker-compose up --build -d
echo.

echo Step 3: Waiting for services to start...
timeout /t 30 /nobreak >nul
echo.

echo Step 4: Running database migrations...
docker-compose exec -T backend alembic upgrade head
echo.

echo ========================================
echo   Application Started Successfully!
echo ========================================
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Checking health...
timeout /t 5 /nobreak >nul
curl -s http://localhost:8000/api/v1/health/
echo.
echo.
echo Press any key to view logs (Ctrl+C to exit)...
pause >nul
docker-compose logs -f
