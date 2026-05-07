@echo off
echo ========================================
echo   EMERGENCY: Remove Exposed API Keys
echo ========================================
echo.
echo WARNING: This will rewrite Git history!
echo Make sure you have a backup before proceeding.
echo.
pause

echo.
echo Step 1: Installing git-filter-repo (if needed)...
pip install git-filter-repo

echo.
echo Step 2: Creating backup...
xcopy /E /I /Y .git .git_backup
echo Backup created in .git_backup folder

echo.
echo Step 3: Removing sensitive files from Git history...
git filter-repo --invert-paths --path backend/.env --force

echo.
echo Step 4: Cleaning up...
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo.
echo Step 5: Force pushing to GitHub...
echo WARNING: This will overwrite remote history!
pause
git push origin main --force

echo.
echo ========================================
echo   CLEANUP COMPLETE
echo ========================================
echo.
echo Next steps:
echo 1. Verify GitHub repository
echo 2. Add new API keys to backend/.env
echo 3. Restart application: docker-compose restart backend
echo.
pause
