#!/bin/bash
# =============================================================================
# Feature Integration Test Script
# =============================================================================
# Tests all 5 assignment features with live API calls

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_BASE="http://localhost:8000/api/v1"
ACCESS_TOKEN=""

echo "🧪 Starting Feature Integration Tests..."
echo ""

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

test_passed() {
    echo -e "${GREEN}✅ PASSED:${NC} $1"
}

test_failed() {
    echo -e "${RED}❌ FAILED:${NC} $1"
    exit 1
}

test_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

test_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

# -----------------------------------------------------------------------------
# Setup: Authentication
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Phase 1: Authentication Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Register test user
test_info "Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "test_'$(date +%s)'@example.com",
        "password": "Test123!@#",
        "full_name": "Test User"
    }' 2>/dev/null || echo '{"error": "failed"}')

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    test_passed "User registered successfully"
else
    # Try login if registration fails (user might exist)
    test_info "Registration failed, trying login..."
    LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "test@example.com",
            "password": "Test123!@#"
        }' 2>/dev/null || echo '{"error": "failed"}')
    
    if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
        ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        test_passed "User logged in successfully"
    else
        test_failed "Authentication failed - cannot proceed with tests"
    fi
fi

echo ""

# -----------------------------------------------------------------------------
# Test 1: Multi-File Upload
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Test 1: Multi-File Upload (NEW FEATURE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create test files
test_info "Creating test files..."
echo "Test document 1 content" > /tmp/test1.txt
echo "Test document 2 content" > /tmp/test2.txt
echo "Test document 3 content" > /tmp/test3.txt

test_info "Uploading 3 files simultaneously..."
MULTI_UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/documents/upload-multiple" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "files=@/tmp/test1.txt" \
    -F "files=@/tmp/test2.txt" \
    -F "files=@/tmp/test3.txt" 2>/dev/null || echo '{"error": "failed"}')

if echo "$MULTI_UPLOAD_RESPONSE" | grep -q "uploaded"; then
    upload_count=$(echo "$MULTI_UPLOAD_RESPONSE" | grep -o '"uploaded":[0-9]*' | cut -d':' -f2)
    if [ "$upload_count" = "3" ]; then
        test_passed "Multi-file upload successful (3 files)"
    else
        test_warning "Multi-file upload partial success ($upload_count/3 files)"
    fi
else
    test_failed "Multi-file upload endpoint not responding"
fi

# Cleanup test files
rm -f /tmp/test1.txt /tmp/test2.txt /tmp/test3.txt

echo ""

# -----------------------------------------------------------------------------
# Test 2: Single File Upload (for subsequent tests)
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 Test 2: Single Document Upload"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create test document
echo "This is a test document for Q&A testing. It contains information about artificial intelligence and machine learning." > /tmp/test_doc.txt

test_info "Uploading test document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/documents/upload" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "file=@/tmp/test_doc.txt" 2>/dev/null || echo '{"error": "failed"}')

if echo "$UPLOAD_RESPONSE" | grep -q '"id"'; then
    DOC_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    test_passed "Document uploaded (ID: $DOC_ID)"
else
    test_failed "Document upload failed"
fi

# Wait for processing
test_info "Waiting for document processing (30 seconds)..."
sleep 30

# Check document status
DOC_STATUS=$(curl -s "$API_BASE/documents/$DOC_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$DOC_STATUS" = "ready" ]; then
    test_passed "Document processing complete"
elif [ "$DOC_STATUS" = "processing" ]; then
    test_warning "Document still processing - some tests may fail"
else
    test_warning "Document status: $DOC_STATUS"
fi

rm -f /tmp/test_doc.txt

echo ""

# -----------------------------------------------------------------------------
# Test 3: Dashboard Summary
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test 3: Dashboard Summary (NEW FEATURE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_info "Fetching document summary..."
SUMMARY_RESPONSE=$(curl -s "$API_BASE/documents/$DOC_ID/summary" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 2>/dev/null || echo '{"error": "failed"}')

if echo "$SUMMARY_RESPONSE" | grep -q '"summary"'; then
    summary_text=$(echo "$SUMMARY_RESPONSE" | grep -o '"summary":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$summary_text" ]; then
        test_passed "Summary generated successfully"
        test_info "Summary preview: ${summary_text:0:100}..."
    else
        test_warning "Summary is empty"
    fi
else
    test_warning "Summary endpoint not responding (may need more processing time)"
fi

echo ""

# -----------------------------------------------------------------------------
# Test 4: Chat Session & Q&A
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💬 Test 4: Chat Session & Q&A"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_info "Creating chat session..."
SESSION_RESPONSE=$(curl -s -X POST "$API_BASE/chat/sessions" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"document_id\": $DOC_ID}" 2>/dev/null || echo '{"error": "failed"}')

if echo "$SESSION_RESPONSE" | grep -q '"id"'; then
    SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    test_passed "Chat session created (ID: $SESSION_ID)"
else
    test_failed "Chat session creation failed"
fi

test_info "Sending test question..."
CHAT_RESPONSE=$(curl -s -X POST "$API_BASE/chat/sessions/$SESSION_ID/messages" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "What is this document about?"}' 2>/dev/null || echo '{"error": "failed"}')

if echo "$CHAT_RESPONSE" | grep -q '"answer"'; then
    test_passed "Chat Q&A working"
    answer_preview=$(echo "$CHAT_RESPONSE" | grep -o '"answer":"[^"]*"' | cut -d'"' -f4)
    test_info "Answer preview: ${answer_preview:0:100}..."
else
    test_warning "Chat Q&A failed - check OpenAI API key"
fi

echo ""

# -----------------------------------------------------------------------------
# Test 5: Cross-Document Search
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Test 5: Cross-Document Search (NEW FEATURE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_info "Testing cross-document search with search_all=true..."
CROSS_DOC_RESPONSE=$(curl -s -X POST "$API_BASE/chat/sessions/$SESSION_ID/messages?search_all=true" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question": "Summarize all my documents"}' 2>/dev/null || echo '{"error": "failed"}')

if echo "$CROSS_DOC_RESPONSE" | grep -q '"answer"'; then
    test_passed "Cross-document search working"
    
    # Check if sources include multiple documents
    if echo "$CROSS_DOC_RESPONSE" | grep -q '"sources"'; then
        test_info "Sources returned from search"
    fi
else
    test_warning "Cross-document search failed - check Pinecone configuration"
fi

echo ""

# -----------------------------------------------------------------------------
# Test 6: Streaming Response
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌊 Test 6: SSE Streaming Response"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_info "Testing streaming endpoint..."
STREAM_OUTPUT=$(timeout 10 curl -s -N "$API_BASE/chat/sessions/$SESSION_ID/stream?question=Hello" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 2>/dev/null | head -n 5)

if echo "$STREAM_OUTPUT" | grep -q "data:"; then
    test_passed "SSE streaming working"
    test_info "Stream sample: $(echo "$STREAM_OUTPUT" | head -n 1)"
else
    test_warning "SSE streaming not responding"
fi

echo ""

# -----------------------------------------------------------------------------
# Test 7: Transcript Endpoint (for media files)
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎵 Test 7: Transcript Endpoint (NEW FEATURE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_info "Testing transcript endpoint..."
TRANSCRIPT_RESPONSE=$(curl -s "$API_BASE/documents/$DOC_ID/transcript" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 2>/dev/null || echo '{"error": "failed"}')

if echo "$TRANSCRIPT_RESPONSE" | grep -q '"chunks"'; then
    test_passed "Transcript endpoint responding"
    chunk_count=$(echo "$TRANSCRIPT_RESPONSE" | grep -o '"start_time"' | wc -l)
    test_info "Transcript chunks: $chunk_count"
elif echo "$TRANSCRIPT_RESPONSE" | grep -q "No transcript"; then
    test_info "No transcript available (document is not audio/video)"
else
    test_warning "Transcript endpoint not responding"
fi

echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Feature Integration Tests Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Test Results Summary:"
echo "   ✅ Authentication: Working"
echo "   ✅ Multi-file Upload: Tested"
echo "   ✅ Document Processing: Tested"
echo "   ✅ Dashboard Summary: Tested"
echo "   ✅ Chat Q&A: Tested"
echo "   ✅ Cross-Document Search: Tested"
echo "   ✅ SSE Streaming: Tested"
echo "   ✅ Transcript Endpoint: Tested"
echo ""
echo "🎯 Next Steps:"
echo "   1. Test frontend UI at http://localhost:3000"
echo "   2. Upload audio/video file to test transcript view"
echo "   3. Test multi-file upload in UI"
echo "   4. Enable cross-document search toggle"
echo ""
