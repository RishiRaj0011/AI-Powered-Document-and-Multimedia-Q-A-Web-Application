# 🚀 QUICK START GUIDE - AI Document Q&A Platform

## ✅ CURRENT STATUS: FULLY OPERATIONAL

**All services are running and healthy!**

---

## 📋 Prerequisites (Already Installed)

- ✅ Docker Desktop (Running)
- ✅ Git (Installed)
- ✅ Windows 10/11

---

## 🎯 ONE-COMMAND START

```cmd
cd "d:\SDE Intern Project"
docker-compose up -d
```

**That's it!** Wait 30 seconds, then open: http://localhost:3000

---

## 🔑 API Keys Configuration

Your API keys are already configured in `backend/.env`:

```bash
# ✅ Google Gemini (Generate new key from https://aistudio.google.com/app/apikey)
GOOGLE_API_KEY=YOUR_NEW_GOOGLE_API_KEY_HERE

# ✅ Pinecone (Generate new key from https://app.pinecone.io/)
PINECONE_API_KEY=YOUR_NEW_PINECONE_API_KEY_HERE

# ⚠️ OpenAI (Optional - Not configured)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
```

**Note:** OpenAI is optional. The system uses Google Gemini by default.

---

## 🌐 Access URLs

| Service | URL | Status |
|---------|-----|--------|
| **Frontend (Main App)** | http://localhost:3000 | ✅ Running |
| **Backend API** | http://localhost:8000 | ✅ Healthy |
| **API Documentation** | http://localhost:8000/docs | ✅ Available |
| **Health Check** | http://localhost:8000/api/v1/health/ | ✅ Passing |

---

## 📱 How to Use the Application

### Step 1: Open Frontend
Open your browser and go to: **http://localhost:3000**

### Step 2: Register Account
- Click "Register" or "Sign Up"
- Enter email: `test@example.com`
- Enter password: `Test@1234` (must have uppercase, number)
- Enter full name: `Test User`
- Click "Register"

### Step 3: Upload Document
- Click "Upload Document" or "+" button
- Select a file:
  - **PDF**: Any PDF document
  - **Audio**: MP3, WAV, M4A files
  - **Video**: MP4, MOV files
  - **Text**: TXT, DOCX files
- Wait for processing (30-60 seconds)

### Step 4: Ask Questions
- Click on the uploaded document
- Type your question in the chat box
- Press Enter or click Send
- Get AI-powered answers!

---

## 🎬 Example Workflow

```
1. Register → test@example.com / Test@1234
2. Upload → sample.pdf (any PDF file)
3. Wait → Processing... (30 seconds)
4. Ask → "What is this document about?"
5. Get Answer → AI responds with summary
```

---

## 🛠️ Useful Commands

### Start Application:
```cmd
docker-compose up -d
```

### Stop Application:
```cmd
docker-compose down
```

### View Logs:
```cmd
docker-compose logs -f
```

### Check Status:
```cmd
docker-compose ps
```

### Restart After Changes:
```cmd
docker-compose restart backend
```

### Complete Reset:
```cmd
docker-compose down -v
docker-compose up -d
```

---

## 🔍 Verification

Run the verification script:
```cmd
verify_project.bat
```

Or manually test:
```cmd
# Test backend
curl http://localhost:8000/api/v1/health/

# Test frontend
curl http://localhost:3000/health
```

---

## ⚡ Quick Troubleshooting

### Backend not responding?
```cmd
docker-compose logs backend --tail=50
docker-compose restart backend
```

### Frontend not loading?
```cmd
docker-compose logs frontend --tail=30
docker-compose restart frontend
```

### Database issues?
```cmd
docker-compose down -v
docker-compose up -d
```

**For detailed troubleshooting, see:** `TROUBLESHOOTING.md`

---

## 📊 System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space
- **CPU**: 2 cores minimum, 4 cores recommended
- **Network**: Internet connection for API calls

---

## 🎯 Features Available

### ✅ Working Features:
- User registration and authentication
- JWT token-based security
- PDF document upload and processing
- Audio/Video transcription (Whisper)
- Text extraction from documents
- Vector embeddings (Pinecone)
- AI-powered Q&A (Gemini)
- Real-time streaming responses
- Document summarization
- Multi-document search
- Session management
- Rate limiting
- Redis caching

### 🔄 Processing Pipeline:
```
Upload → Validate → Save → Extract Text → 
Chunk → Generate Embeddings → Store in Pinecone → 
Ready for Q&A
```

---

## 📝 Sample Test Files

You can test with these types of files:

### PDF Documents:
- Research papers
- Books
- Reports
- Presentations (exported as PDF)

### Audio Files:
- Podcasts (MP3)
- Lectures (WAV)
- Interviews (M4A)

### Video Files:
- Recorded meetings (MP4)
- Tutorials (MOV)
- Presentations (MP4)

### Text Files:
- Plain text (TXT)
- Word documents (DOCX)

---

## 🔐 Security Notes

- ✅ JWT authentication enabled
- ✅ Password hashing (bcrypt)
- ✅ Rate limiting active
- ✅ CORS configured
- ✅ SQL injection protection
- ✅ XSS protection
- ⚠️ API keys in .env (not committed to Git)

---

## 📈 Performance Tips

### For faster processing:
1. Use smaller files initially (< 10MB)
2. PDF works faster than audio/video
3. Clear text documents process quickest

### For better responses:
1. Ask specific questions
2. Reference document sections
3. Use follow-up questions

---

## 🆘 Need Help?

### Check these files:
1. `TROUBLESHOOTING.md` - Detailed solutions
2. `SETUP_SUCCESS.md` - Setup verification
3. `README.md` - Full documentation

### Run diagnostics:
```cmd
verify_project.bat
```

### View logs:
```cmd
docker-compose logs -f
```

---

## ✅ Success Checklist

Before using the application, verify:

- [ ] Docker Desktop is running
- [ ] All containers are healthy (`docker-compose ps`)
- [ ] Backend health check passes
- [ ] Frontend loads in browser
- [ ] Can register new account
- [ ] Can login successfully
- [ ] Can upload files
- [ ] Can ask questions

---

## 🎉 You're All Set!

Your AI Document Q&A Platform is ready to use!

**Start here:** http://localhost:3000

**Questions?** Check `TROUBLESHOOTING.md`

**Happy chatting with your documents!** 🚀📄💬

---

**Last Updated:** May 7, 2026  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
