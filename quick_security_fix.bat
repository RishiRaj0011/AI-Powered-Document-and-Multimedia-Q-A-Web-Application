@echo off
echo ========================================
echo   QUICK FIX: Remove Exposed API Keys
echo ========================================
echo.
echo This script will:
echo 1. Remove backend/.env from Git tracking
echo 2. Commit the changes
echo 3. Push to GitHub
echo.
echo IMPORTANT: Make sure you have already:
echo - Revoked old API keys from Pinecone and Google
echo - Generated new API keys
echo - Updated backend/.env with new keys
echo.
pause

echo.
echo Step 1: Removing backend/.env from Git...
git rm --cached backend/.env

echo.
echo Step 2: Committing changes...
git add .gitignore
git commit -m "Security: Remove exposed API keys and update .gitignore

- Remove backend/.env from Git tracking
- Add explicit paths to .gitignore
- API keys have been revoked and regenerated
- See SECURITY_INCIDENT.md for details"

echo.
echo Step 3: Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo   BASIC CLEANUP COMPLETE
echo ========================================
echo.
echo NEXT STEPS:
echo 1. Go to GitHub and verify backend/.env is not visible
echo 2. For complete history cleanup, see SECURITY_INCIDENT.md
echo 3. Restart backend: docker-compose restart backend
echo.
pause
