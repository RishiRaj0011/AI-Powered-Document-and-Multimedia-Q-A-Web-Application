@echo off
REM Gemini Integration Verification Script
echo.
echo ========================================
echo   GEMINI INTEGRATION CHECK
echo ========================================
echo.

REM Check .env file
echo [1] Checking .env file...
if exist .env (
    echo [OK] .env file exists
    findstr /C:"GOOGLE_API_KEY" .env >nul
    if %errorlevel% equ 0 (
        echo [OK] GOOGLE_API_KEY found in .env
        findstr /C:"GOOGLE_API_KEY=YOUR_GOOGLE" .env >nul
        if %errorlevel% equ 0 (
            echo [WARNING] GOOGLE_API_KEY is placeholder - needs real key!
            echo          Get key from: https://aistudio.google.com/app/apikey
        ) else (
            echo [OK] GOOGLE_API_KEY appears to be set
        )
    ) else (
        echo [ERROR] GOOGLE_API_KEY not found in .env
    )
    
    findstr /C:"OPENAI_API_KEY=sk-" .env >nul
    if %errorlevel% equ 0 (
        echo [WARNING] OPENAI_API_KEY is set - will prefer OpenAI over Gemini
    ) else (
        echo [OK] OPENAI_API_KEY is empty - will use Gemini
    )
) else (
    echo [ERROR] .env file not found!
)
echo.

REM Check service files
echo [2] Checking service files...
if exist backend\app\services\llm_service.py (
    echo [OK] Unified LLM Service exists
) else (
    echo [ERROR] llm_service.py NOT FOUND!
)

if exist backend\app\services\gemini_service.py (
    echo [OK] Gemini Service exists
) else (
    echo [ERROR] gemini_service.py NOT FOUND!
)

if exist backend\app\services\chat_service.py (
    echo [OK] Chat Service exists
    findstr /C:"get_llm" backend\app\services\chat_service.py >nul
    if %errorlevel% equ 0 (
        echo [OK] Chat Service uses unified LLM
    ) else (
        echo [ERROR] Chat Service still uses direct OpenAI!
    )
) else (
    echo [ERROR] chat_service.py NOT FOUND!
)

if exist backend\app\services\embedding_service.py (
    echo [OK] Embedding Service exists
    findstr /C:"get_llm_service" backend\app\services\embedding_service.py >nul
    if %errorlevel% equ 0 (
        echo [OK] Embedding Service uses unified LLM
    ) else (
        echo [ERROR] Embedding Service still uses direct OpenAI!
    )
) else (
    echo [ERROR] embedding_service.py NOT FOUND!
)
echo.

REM Check config
echo [3] Checking configuration...
if exist backend\app\core\config.py (
    echo [OK] config.py exists
    findstr /C:"GOOGLE_API_KEY" backend\app\core\config.py >nul
    if %errorlevel% equ 0 (
        echo [OK] GOOGLE_API_KEY defined in config
    ) else (
        echo [ERROR] GOOGLE_API_KEY not in config!
    )
) else (
    echo [ERROR] config.py NOT FOUND!
)
echo.

REM Check requirements
echo [4] Checking requirements...
if exist backend\requirements.txt (
    echo [OK] requirements.txt exists
    findstr /C:"google-generativeai" backend\requirements.txt >nul
    if %errorlevel% equ 0 (
        echo [OK] google-generativeai package listed
    ) else (
        echo [ERROR] google-generativeai NOT in requirements!
    )
) else (
    echo [ERROR] requirements.txt NOT FOUND!
)
echo.

REM Check transcription service
echo [5] Checking transcription service...
if exist backend\app\services\transcription_service.py (
    echo [OK] transcription_service.py exists
    echo [INFO] Uses OpenAI Whisper for audio/video
    echo       This is EXPECTED - Gemini doesn't support audio
    echo       Audio/video features require OpenAI API key
) else (
    echo [ERROR] transcription_service.py NOT FOUND!
)
echo.

REM Summary
echo ========================================
echo   SUMMARY
echo ========================================
echo.
echo [WORKING WITH GEMINI - FREE]:
echo   - Document upload (PDF, TXT, DOCX)
echo   - Chat Q^&A
echo   - Streaming responses
echo   - Document summarization
echo   - Cross-document search
echo   - Embeddings generation
echo   - Multi-file upload
echo.
echo [REQUIRES OPENAI - OPTIONAL]:
echo   - Audio transcription (MP3, WAV)
echo   - Video transcription (MP4)
echo.
echo [SETUP INSTRUCTIONS]:
echo   1. Get FREE Gemini key: https://aistudio.google.com/app/apikey
echo   2. Edit .env file:
echo      GOOGLE_API_KEY=AIzaSy...
echo      OPENAI_API_KEY=  (leave empty)
echo   3. Rebuild: docker compose up --build -d
echo   4. Verify: docker compose logs backend ^| findstr "LLM Provider"
echo      Should show: "LLM Provider: gemini"
echo.
echo [COST]:
echo   - With Gemini only: $0 (FREE)
echo   - With OpenAI for audio: ~$0.006/minute
echo.

pause
