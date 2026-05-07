# 🚨 SECURITY INCIDENT - API KEY EXPOSURE

## ⚠️ CRITICAL: IMMEDIATE ACTION REQUIRED

**Date:** May 7, 2026  
**Severity:** HIGH  
**Status:** EXPOSED API KEYS DETECTED

GitGuardian has detected exposed API keys in your public GitHub repository.

---

## 🔴 STEP-BY-STEP REMEDIATION (DO THIS NOW!)

### ⏰ **STEP 1: REVOKE EXPOSED KEYS (5 minutes)**

#### A. Revoke Pinecone API Key

**Exposed Key:** `pcsk_6ppCvc_QTzgPJAbcd7N6L4HebuWnBXGKvC4TTAvQgY7QDirf2w9vHgUXAbnjRLDmonDzqM`

1. Go to: https://app.pinecone.io/
2. Login with your credentials
3. Navigate to: **API Keys** (left sidebar)
4. Find the exposed key
5. Click **"Delete"** or **"Revoke"**
6. Confirm deletion
7. Click **"Create API Key"**
8. Name it: `docqa-secure-key-2026`
9. **COPY THE NEW KEY** (you'll only see it once!)
10. Save it securely (password manager recommended)

#### B. Revoke Google Gemini API Key

**Exposed Key:** `AIzaSyDclhdnAXULUekjz6vbRCqSmE6hIVMsr5E`

1. Go to: https://aistudio.google.com/app/apikey
2. Login with your Google account
3. Find the exposed key in the list
4. Click the **trash icon** to delete
5. Confirm deletion
6. Click **"Create API Key"**
7. Select your Google Cloud project
8. **COPY THE NEW KEY**
9. Save it securely

---

### 🔧 **STEP 2: UPDATE LOCAL CONFIGURATION (2 minutes)**

#### Update backend/.env file:

Open: `d:\SDE Intern Project\backend\.env`

Replace these lines:
```bash
# OLD (EXPOSED - DO NOT USE)
PINECONE_API_KEY=pcsk_6ppCvc_...
GOOGLE_API_KEY=AIzaSyDclhdnAXULUekjz6vbRCqSmE6hIVMsr5E

# NEW (PASTE YOUR NEW KEYS HERE)
PINECONE_API_KEY=<YOUR_NEW_PINECONE_KEY>
GOOGLE_API_KEY=<YOUR_NEW_GOOGLE_KEY>
```

**Save the file** (Ctrl+S)

---

### 🧹 **STEP 3: CLEAN GIT HISTORY (10 minutes)**

The exposed keys are in Git history. We need to remove them completely.

#### Option A: Using BFG Repo-Cleaner (Recommended)

```cmd
# 1. Download BFG
# Go to: https://rtyley.github.io/bfg-repo-cleaner/
# Download bfg.jar

# 2. Create a file with exposed keys
echo pcsk_6ppCvc_QTzgPJAbcd7N6L4HebuWnBXGKvC4TTAvQgY7QDirf2w9vHgUXAbnjRLDmonDzqM > secrets.txt
echo AIzaSyDclhdnAXULUekjz6vbRCqSmE6hIVMsr5E >> secrets.txt

# 3. Run BFG to remove secrets
java -jar bfg.jar --replace-text secrets.txt .git

# 4. Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Force push (WARNING: Rewrites history!)
git push origin main --force
```

#### Option B: Using git-filter-repo

```cmd
# 1. Install git-filter-repo
pip install git-filter-repo

# 2. Remove backend/.env from history
git filter-repo --invert-paths --path backend/.env --force

# 3. Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. Force push
git push origin main --force
```

#### Option C: Nuclear Option (Easiest but loses history)

```cmd
# 1. Delete .git folder
rmdir /s /q .git

# 2. Reinitialize repository
git init
git add .
git commit -m "Initial commit with secure configuration"

# 3. Force push to GitHub
git remote add origin https://github.com/RishiRaj0011/AI-Powered-Document-and-Multimedia-Q-A-Web-Application.git
git push origin main --force
```

---

### 🔄 **STEP 4: RESTART APPLICATION (1 minute)**

```cmd
cd "d:\SDE Intern Project"

# Restart backend with new keys
docker-compose restart backend

# Verify it's working
curl http://localhost:8000/api/v1/health/
```

---

### ✅ **STEP 5: VERIFY REMEDIATION (2 minutes)**

#### Check 1: Keys Revoked
- [ ] Old Pinecone key deleted from dashboard
- [ ] Old Google key deleted from console
- [ ] New keys generated and saved securely

#### Check 2: Local Files Updated
- [ ] `backend/.env` has new keys
- [ ] No exposed keys in any file
- [ ] `.env` files in `.gitignore`

#### Check 3: Git History Cleaned
- [ ] Git history rewritten
- [ ] Force pushed to GitHub
- [ ] No secrets in commit history

#### Check 4: Application Working
- [ ] Backend restarted successfully
- [ ] Health check passing
- [ ] Can upload documents
- [ ] Can ask questions

---

## 🛡️ PREVENT FUTURE EXPOSURES

### 1. **Add .env to .gitignore (Already Done)**

Verify `.gitignore` contains:
```
.env
.env.local
.env.*.local
backend/.env
frontend/.env
```

### 2. **Use Environment Variables Template**

Keep only `.env.example` files in Git:
```bash
# .env.example (SAFE to commit)
PINECONE_API_KEY=your_pinecone_key_here
GOOGLE_API_KEY=your_google_key_here
```

### 3. **Install Pre-commit Hooks**

```cmd
# Install ggshield (GitGuardian CLI)
pip install ggshield

# Initialize in your repo
ggshield install

# This will scan commits before pushing
```

### 4. **Use Secret Management Tools**

Consider using:
- **AWS Secrets Manager**
- **HashiCorp Vault**
- **Azure Key Vault**
- **1Password** (for local development)

### 5. **Enable GitHub Secret Scanning**

1. Go to: https://github.com/RishiRaj0011/AI-Powered-Document-and-Multimedia-Q-A-Web-Application/settings/security_analysis
2. Enable **"Secret scanning"**
3. Enable **"Push protection"**

---

## 📋 SECURITY CHECKLIST

### Immediate (Do Now):
- [ ] Revoke Pinecone API key
- [ ] Revoke Google Gemini API key
- [ ] Generate new keys
- [ ] Update local `.env` files
- [ ] Clean Git history
- [ ] Force push to GitHub
- [ ] Restart application
- [ ] Verify everything works

### Short-term (This Week):
- [ ] Install ggshield pre-commit hooks
- [ ] Enable GitHub secret scanning
- [ ] Review all commits for other secrets
- [ ] Audit who has access to repository
- [ ] Change database passwords
- [ ] Rotate JWT secret key

### Long-term (This Month):
- [ ] Implement secret management solution
- [ ] Set up automated secret rotation
- [ ] Create security incident response plan
- [ ] Train team on security best practices
- [ ] Regular security audits

---

## 🔍 HOW TO CHECK IF KEYS WERE COMPROMISED

### 1. Check Pinecone Usage
- Go to: https://app.pinecone.io/
- Check **"Usage"** tab
- Look for unusual activity
- Check if index was accessed by unknown IPs

### 2. Check Google Cloud Usage
- Go to: https://console.cloud.google.com/
- Navigate to **"APIs & Services" > "Credentials"**
- Check API usage metrics
- Look for unusual spikes

### 3. Monitor for Unusual Charges
- Check Pinecone billing
- Check Google Cloud billing
- Set up billing alerts

---

## 📞 IF KEYS WERE ALREADY USED BY ATTACKERS

### Immediate Actions:
1. **Contact Support:**
   - Pinecone: support@pinecone.io
   - Google Cloud: https://cloud.google.com/support

2. **Report Incident:**
   - Document what happened
   - Note when keys were exposed
   - List any unusual activity

3. **Assess Damage:**
   - Check if data was accessed
   - Check if data was modified
   - Check if data was deleted

4. **Notify Users (if applicable):**
   - If user data was compromised
   - Follow data breach notification laws

---

## 🎓 LESSONS LEARNED

### What Went Wrong:
1. ❌ API keys committed to Git
2. ❌ `.env` file not in `.gitignore` initially
3. ❌ No pre-commit hooks to catch secrets
4. ❌ No secret scanning enabled

### What to Do Better:
1. ✅ Always use `.env.example` templates
2. ✅ Never commit actual `.env` files
3. ✅ Use pre-commit hooks (ggshield)
4. ✅ Enable GitHub secret scanning
5. ✅ Use secret management tools
6. ✅ Regular security audits

---

## 📚 ADDITIONAL RESOURCES

### Tools:
- **GitGuardian CLI:** https://github.com/GitGuardian/ggshield
- **BFG Repo-Cleaner:** https://rtyley.github.io/bfg-repo-cleaner/
- **git-filter-repo:** https://github.com/newren/git-filter-repo
- **TruffleHog:** https://github.com/trufflesecurity/trufflehog

### Guides:
- **GitHub Secret Scanning:** https://docs.github.com/en/code-security/secret-scanning
- **Removing Sensitive Data:** https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- **GitGuardian Guide:** https://blog.gitguardian.com/secrets-api-management/

---

## ✅ VERIFICATION COMMANDS

After completing all steps, run these to verify:

```cmd
# 1. Check no secrets in current files
findstr /S /I "pcsk_6ppCvc" *.*
findstr /S /I "AIzaSyDclhdnAXULUekjz6vbRCqSmE6hIVMsr5E" *.*

# Should return: No matches found

# 2. Check Git history
git log --all --full-history --source --pretty=format:"%H" -- backend/.env

# Should be empty or show removal commits only

# 3. Test application
curl http://localhost:8000/api/v1/health/

# Should return: {"status":"healthy",...}
```

---

## 🚨 EMERGENCY CONTACTS

- **GitGuardian Support:** support@gitguardian.com
- **GitHub Security:** https://github.com/security
- **Pinecone Support:** support@pinecone.io
- **Google Cloud Security:** https://cloud.google.com/security

---

**REMEMBER: Security is not a one-time task. It's an ongoing process!**

**Status:** ⚠️ REMEDIATION IN PROGRESS  
**Priority:** 🔴 CRITICAL  
**Action Required:** ✅ IMMEDIATE

---

**Last Updated:** May 7, 2026  
**Document Version:** 1.0
