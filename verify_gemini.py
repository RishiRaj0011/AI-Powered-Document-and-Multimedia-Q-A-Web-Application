#!/usr/bin/env python3
"""
Gemini Integration Verification Script
Checks if all services are properly configured to use Gemini
"""

import os
import sys

def check_env_file():
    """Check .env file configuration"""
    print("=" * 60)
    print("1. Checking .env Configuration")
    print("=" * 60)
    
    env_path = ".env"
    if not os.path.exists(env_path):
        print("❌ .env file not found!")
        return False
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_gemini = "GOOGLE_API_KEY" in content
    gemini_set = "GOOGLE_API_KEY=AIza" in content or "GOOGLE_API_KEY=YOUR_GOOGLE" in content
    
    has_openai = "OPENAI_API_KEY" in content
    openai_empty = "OPENAI_API_KEY=" in content and "OPENAI_API_KEY=sk-" not in content
    
    print(f"✓ .env file exists")
    print(f"✓ GOOGLE_API_KEY present: {has_gemini}")
    
    if "GOOGLE_API_KEY=YOUR_GOOGLE" in content:
        print("⚠️  GOOGLE_API_KEY is placeholder - needs real key!")
        print("   Get key from: https://aistudio.google.com/app/apikey")
    elif "GOOGLE_API_KEY=AIza" in content:
        print("✓ GOOGLE_API_KEY appears to be set")
    
    if openai_empty:
        print("✓ OPENAI_API_KEY is empty (will use Gemini)")
    else:
        print("⚠️  OPENAI_API_KEY is set (will prefer OpenAI over Gemini)")
    
    print()
    return True


def check_service_files():
    """Check if service files use unified LLM"""
    print("=" * 60)
    print("2. Checking Service Files")
    print("=" * 60)
    
    files_to_check = {
        "backend/app/services/llm_service.py": "Unified LLM Service",
        "backend/app/services/gemini_service.py": "Gemini Service",
        "backend/app/services/chat_service.py": "Chat Service",
        "backend/app/services/embedding_service.py": "Embedding Service",
    }
    
    all_good = True
    for file_path, name in files_to_check.items():
        if os.path.exists(file_path):
            print(f"✓ {name} exists")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            if file_path == "backend/app/services/chat_service.py":
                if "get_llm_service" in content or "get_llm_client" in content:
                    print(f"  ✓ Uses unified LLM service")
                else:
                    print(f"  ❌ Still uses direct OpenAI client!")
                    all_good = False
            
            if file_path == "backend/app/services/embedding_service.py":
                if "get_llm_service" in content:
                    print(f"  ✓ Uses unified LLM service")
                else:
                    print(f"  ❌ Still uses direct OpenAI client!")
                    all_good = False
        else:
            print(f"❌ {name} NOT FOUND!")
            all_good = False
    
    print()
    return all_good


def check_config():
    """Check config.py for Gemini settings"""
    print("=" * 60)
    print("3. Checking Configuration")
    print("=" * 60)
    
    config_path = "backend/app/core/config.py"
    if not os.path.exists(config_path):
        print("❌ config.py not found!")
        return False
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    has_google_key = "GOOGLE_API_KEY" in content
    has_gemini_model = "GEMINI_MODEL" in content
    
    print(f"✓ config.py exists")
    print(f"{'✓' if has_google_key else '❌'} GOOGLE_API_KEY defined")
    print(f"{'✓' if has_gemini_model else '❌'} GEMINI_MODEL defined")
    
    print()
    return has_google_key


def check_requirements():
    """Check if google-generativeai is in requirements"""
    print("=" * 60)
    print("4. Checking Requirements")
    print("=" * 60)
    
    req_path = "backend/requirements.txt"
    if not os.path.exists(req_path):
        print("❌ requirements.txt not found!")
        return False
    
    with open(req_path, 'r') as f:
        content = f.read()
    
    has_gemini = "google-generativeai" in content
    has_openai = "openai" in content
    
    print(f"✓ requirements.txt exists")
    print(f"{'✓' if has_gemini else '❌'} google-generativeai package")
    print(f"{'✓' if has_openai else '⚠️ '} openai package (optional for audio)")
    
    print()
    return has_gemini


def check_transcription_service():
    """Check transcription service"""
    print("=" * 60)
    print("5. Checking Transcription Service")
    print("=" * 60)
    
    trans_path = "backend/app/services/transcription_service.py"
    if not os.path.exists(trans_path):
        print("❌ transcription_service.py not found!")
        return False
    
    with open(trans_path, 'r') as f:
        content = f.read()
    
    uses_openai = "AsyncOpenAI" in content
    
    print(f"✓ transcription_service.py exists")
    if uses_openai:
        print(f"⚠️  Uses OpenAI Whisper for audio/video transcription")
        print(f"   This is EXPECTED - Gemini doesn't support audio transcription")
        print(f"   Audio/video features require OpenAI API key")
    
    print()
    return True


def print_summary():
    """Print summary and recommendations"""
    print("=" * 60)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 60)
    print()
    print("✅ WORKING WITH GEMINI (FREE):")
    print("   - Document upload (PDF, TXT, DOCX)")
    print("   - Chat Q&A")
    print("   - Streaming responses")
    print("   - Document summarization")
    print("   - Cross-document search")
    print("   - Embeddings generation")
    print("   - Multi-file upload")
    print()
    print("⚠️  REQUIRES OPENAI (OPTIONAL):")
    print("   - Audio transcription (MP3, WAV)")
    print("   - Video transcription (MP4)")
    print()
    print("💡 SETUP INSTRUCTIONS:")
    print("   1. Get FREE Gemini key: https://aistudio.google.com/app/apikey")
    print("   2. Edit .env file:")
    print("      GOOGLE_API_KEY=AIzaSy...")
    print("      OPENAI_API_KEY=  (leave empty)")
    print("   3. Rebuild: docker compose up --build -d")
    print("   4. Verify: docker compose logs backend | findstr 'LLM Provider'")
    print("      Should show: 'LLM Provider: gemini'")
    print()
    print("🎯 COST:")
    print("   - With Gemini only: $0 (FREE)")
    print("   - With OpenAI for audio: ~$0.006/minute")
    print()


def main():
    print()
    print("GEMINI INTEGRATION VERIFICATION")
    print()
    
    results = []
    results.append(check_env_file())
    results.append(check_service_files())
    results.append(check_config())
    results.append(check_requirements())
    results.append(check_transcription_service())
    
    print_summary()
    
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print("   System is ready to use Gemini (after adding API key)")
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("   Please review the issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
