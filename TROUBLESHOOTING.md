# Troubleshooting Guide

## Common Issues & Solutions

---

## 1. API Connection Issues

### Issue: "❌ API Disconnected" in Streamlit

**Symptoms:**
- Red indicator in Streamlit saying "Cannot connect to API"
- Generation fails immediately
- No loading spinner appears

**Diagnose:**
```bash
# 1. Check if backend is running
curl http://localhost:5050/api/health

# 2. If command fails, backend isn't running
# 3. Check if port 5050 is available
```

**Solutions:**

**Solution A: Backend Not Running**
```bash
# Terminal 1: Start backend
cd backend
python app_new.py

# Wait for output:
# INFO:     Uvicorn running on http://0.0.0.0:5050
```

**Solution B: Wrong API URL in Streamlit Config**
```bash
# Fix: Update frontend/.streamlit/secrets.toml
cat > frontend/.streamlit/secrets.toml << EOF
API_BASE_URL = "http://localhost:5050"
EOF

# Refresh Streamlit app (press R or restart)
```

**Solution C: Port 5050 Already in Use**
```bash
# Windows: Find process using port 5050
netstat -ano | findstr :5050

# Kill the process
taskkill /PID [PID] /F

# Or use different port in backend:
# Edit backend/app_new.py:
# uvicorn.run(app, host="0.0.0.0", port=8000)

# Then update Streamlit config:
# API_BASE_URL = "http://localhost:8000"
```

**Solution D: Firewall Blocking**
- Check Windows Firewall settings
- Ensure port 5050 is allowed
- Try connecting from another machine on network

---

## 2. API Key Issues

### Issue: "Authentication failed" or "Unauthorized"

**Symptoms:**
- Generation starts but fails after a few seconds
- Error message mentions "API key" or "authentication"
- One generator works, other doesn't

**Diagnose:**

```bash
# Check if .env file exists and has keys
cat .env

# Check if keys are being loaded
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'GEMINI_API_KEY: {bool(os.getenv(\"GEMINI_API_KEY\"))}')
print(f'OPENAI_API_KEY: {bool(os.getenv(\"OPENAI_API_KEY\"))}')
"
```

**Solutions:**

**Solution A: Missing .env File**
```bash
# Create .env in project root
cat > .env << EOF
GEMINI_API_KEY=your_actual_key_here
OPENAI_API_KEY=your_actual_key_here
EOF

# Get keys from:
# Gemini: https://aistudio.google.com/app/apikey
# OpenAI: https://platform.openai.com/account/api-keys
```

**Solution B: Invalid API Key**
```bash
# Test Gemini key:
python -c "
import google.genai
genai.configure(api_key='your_key')
print('✅ Gemini key valid')
"

# Test OpenAI key:
python -c "
from openai import OpenAI
client = OpenAI(api_key='your_key')
print('✅ OpenAI key valid')
"
```

**Solution C: API Key in Wrong Format**
```bash
# Gemini keys start with: AIza...
# OpenAI keys start with: sk-...

# Check your .env file - they should look like:
# GEMINI_API_KEY=AIzaSy...
# OPENAI_API_KEY=sk-proj-...
```

**Solution D: Expired or Revoked Key**
- Go to service dashboard
- Regenerate new key
- Update .env
- Restart backend

**Solution E: Key Has No Credits/Quota**
```bash
# Check usage in:
# Gemini: https://makersuite.google.com/app/settings
# OpenAI: https://platform.openai.com/account/usage/overview

# Free tier may have daily limits
# May need to add payment method
```

---

## 3. Generation Failures

### Issue: Generation Fails for One Generator

**Symptoms:**
- DALL-E 3 works, Gemini fails (or vice versa)
- API health shows one client not ready
- Error appears after clicking Generate

**Diagnose:**

```bash
# Check which client is having issues
curl http://localhost:5050/api/health | jq '.'

# If gemini_ready: false, Gemini has problem
# If openai_ready: false, OpenAI has problem
```

**Solutions for DALL-E 3 Failures:**

**Issue: "Usage limit exceeded"**
- Upgrade OpenAI account to paid
- Check billing settings
- Wait for monthly quota reset

**Issue: "This model doesn't support image generation"**
- Verify `dall-e-3` is available in your region
- Some regions have restrictions
- Use VPN if necessary

**Issue: "Invalid request format"**
- Check advanced parameters aren't too long
- Elements to include/avoid should be concise
- Brand mission should be < 200 characters

---

**Solutions for Gemini Failures:**

**Issue: "Model not found"**
- Check if `gemini-2.0-flash-001` is available
- May need to use `gemini-pro-vision` or check Google docs
- Verify API key has access to this model

**Issue: "Content blocked"**
- Gemini has safety filters
- Try with different description/style
- Avoid sensitive words
- Be more specific with brand mission

**Issue: "File could not be created"**
- Check permissions on `backend/generated_logos/` directory
- Directory should exist and be writable
- In Windows, check file isn't locked by another process

---

## 4. Frontend Issues

### Issue: Streamlit App Won't Load

**Symptoms:**
- Page blank or stuck on loading
- "Streamlit is starting..." stays permanent
- Console shows errors (F12 to see)

**Solutions:**

**Solution A: Streamlit Config Error**
```bash
# Check for syntax errors in config
cat frontend/.streamlit/secrets.toml

# Should be valid TOML:
# API_BASE_URL = "http://localhost:5050"

# If invalid, delete and recreate:
rm frontend/.streamlit/secrets.toml
mkdir -p frontend/.streamlit
echo 'API_BASE_URL = "http://localhost:5050"' > frontend/.streamlit/secrets.toml
```

**Solution B: Missing Streamlit Cache**
```bash
# Clear Streamlit cache
rm -r ~/.streamlit/

# Restart app:
streamlit run frontend/streamlit_app.py
```

**Solution C: Port 8501 Already in Use**
```bash
# Windows: Find and kill process
netstat -ano | findstr :8501
taskkill /PID [PID] /F

# Or use different port:
streamlit run frontend/streamlit_app.py --server.port 9000
```

**Solution D: Python Module Not Found**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific packages
pip install streamlit requests pillow
```

---

### Issue: Form Won't Submit / Button Doesn't Work

**Symptoms:**
- Click Generate but nothing happens
- No loading spinner appears
- No error message

**Solutions:**

**Solution A: Missing Brand Name**
- Streamlit may silently fail
- Check that "Brand Name" field is filled
- Try typing something in it again

**Solution B: API Not Connected**
- Check red "❌ API Disconnected" indicator
- See "API Connection Issues" section above
- Restart backend and Streamlit

**Solution C: Browser Issues**
- Clear browser cache: Ctrl+Shift+Delete
- Try different browser
- Try incognito window

**Solution D: Socket.io Connection Lost**
- Streamlit lost connection to backend
- Refresh page (F5)
- Restart backend and Streamlit

---

## 5. Image Quality Issues

### Issue: Generated Image is Low Quality / Doesn't Match Description

**Symptoms:**
- DALL-E 3 produces blocky or pixelated image
- Gemini generates irrelevant image
- Advanced options seem ignored

**Solutions for DALL-E 3:**

**Solution A: Prompt Too Short**
- Add more context in Description field
- Use advanced options to elaborate
- Mention style, colors, mood

**Solution B: Conflicting Requirements**
- Check "Elements to Avoid" don't conflict with "Include"
- Example: "Include: Modern Design" + "Avoid: Modern Design" = confused
- Use clear, non-contradictory instructions

**Solution C: Request Against Policy**
- DALL-E won't generate certain content
- Avoid: faces, trademarked logos, violent content
- Keep descriptions professional and appropriate

**Solutions for Gemini:**

**Solution A: Description Too Generic**
- Gemini needs clear direction
- Instead of "technology company", say "AI cloud platform"
- Be specific about industry and vision

**Solution B: Style and Palette Mismatch**
- Choose combinations that make sense
- "Vintage" style with "Neon" palette = conflicting
- Use coherent style/palette pairs

**Solution C: Safety Content Filter**
- Gemini is more conservative than DALL-E
- Avoid sensitive topics
- Keep brand mission professional

---

## 6. Download Issues

### Issue: Download Button Doesn't Work

**Symptoms:**
- Click download, nothing happens
- No file appears in Downloads folder
- Browser shows "Failed to download"

**Solutions:**

**Solution A: DALL-E URL Expired**
- DALL-E URLs expire after 1 hour
- Download immediately after generation
- Can't download old images from Gallery if > 1 hour old

**Solution B: Gemini File Not Found**
- Check `backend/generated_logos/` directory exists
- Check file is actually there:
  ```bash
  ls -la backend/generated_logos/
  ```
- File may have been deleted
- Regenerate to create new file

**Solution C: Browser Download Settings**
- Check browser is allowed to download
- Check Downloads folder permissions
- Try different browser

**Solution D: Large File Size**
- DALL-E images may be large (1-5 MB)
- Gemini images typically smaller (500 KB - 2 MB)
- Check available disk space

---

## 7. Performance Issues

### Issue: Generation Too Slow

**Symptoms:**
- DALL-E takes > 60 seconds
- Gemini takes > 45 seconds
- Seems stuck with loading spinner

**Solutions:**

**Solution A: Network Latency**
- Check internet connection speed
- Poor connection adds latency
- Try on faster WiFi or wired connection

**Solution B: API Rate Limiting**
- Both services have rate limits
- If you're generating lots in quick succession
- Wait 1-2 minutes between generations
- Use free tier limits

**Solution C: Server Overload**
- OpenAI/Gemini may be busy
- Try again in a few minutes
- Can't fix—service provider issue

**Solution D: Slow Computer**
- If backend or Streamlit running on slow machine
- Close other applications
- Increase available RAM

---

## 8. Generator Isolation Problems

### Issue: "DALL-E is calling Gemini" or vice versa

**Symptoms:**
- Selected DALL-E but Gemini is being used
- Wrong model appears in prompt
- Wrong type of output (URL vs file)

**Diagnose:**

```bash
# Check backend logs during generation
# Look at the terminal running python app_new.py

# Should see:
# For DALL-E: "Initializing OpenAI client..."
# For Gemini: "Initializing Gemini client..."

# Should NOT see both
```

**Solutions:**

**Solution A: Wrong Generator Selection**
- Verify correct generator is selected in form
- Look for dropdown showing "dalle-3" or "gemini"
- Sometimes reverts to default after error

**Solution B: Frontend Caching**
- Clear Streamlit cache:
  ```bash
  rm -r ~/.streamlit/
  ```
- Restart app:
  ```bash
  streamlit run frontend/streamlit_app.py
  ```

**Solution C: Backend Not Updated**
- Ensure latest `services.py` has isolation code
- Check that `LLMService` has two methods:
  - `generate_logo_with_dalle()`
  - `generate_logo_with_gemini()`
- If not present, need to update files

---

## 9. Database/File Issues

### Issue: "Cannot write to generated_logos directory"

**Symptoms:**
- Gemini generation fails
- Error: "Permission denied" or "Cannot create file"
- Only Gemini affected, DALL-E works

**Solutions:**

**Solution A: Directory Doesn't Exist**
```bash
# Create it explicitly
mkdir -p backend/generated_logos

# Change to project directory first:
cd /path/to/Logo-Generator
mkdir -p backend/generated_logos
```

**Solution B: Permission Issues**
```bash
# Windows: Check folder properties
# Right-click → Properties → Security → Edit
# Ensure your user has "Full Control"

# Or run command prompt as Admin:
mkdir backend\generated_logos
```

**Solution C: Disk Full**
- Check available disk space
- Delete old generated logos
- May need to set up cleanup script

**Solution D: File Already Locked**
- Another process has the file open
- Close image viewer showing the file
- Restart backend

---

## 10. Advanced Parameter Issues

### Issue: Advanced Options Not Working

**Symptoms:**
- Advanced fields don't appear in prompt
- Changes to advanced fields don't affect output
- Sidebar toggle doesn't work

**Solutions:**

**Solution A: Toggle Not Showing**
```bash
# Check streamlit_app.py has:
with st.sidebar:
    show_advanced = st.checkbox("⚙️ Show Advanced Options", value=False)
    if show_advanced:
        # Advanced fields here
```

**Solution B: Fields Not Being Passed to Backend**
- Check form submission includes all fields
- Look at network tab in browser (F12)
- Verify POST request includes:
  - tagline
  - typography
  - elements_to_include
  - elements_to_avoid
  - brand_mission

**Solution C: Backend Not Using Advanced Fields**
- Check `services.py` has parameters in method signatures
- Check prompts are constructed with all parameters
- May need to restart backend after code changes

---

## 11. Database Connection Issues

### Issue: History/Gallery not loading

**Symptoms:**
- Gallery tab is empty
- Previously generated images not showing
- History appears to be lost

**Note:** Current implementation uses Streamlit session state, not persistent database.

**Solutions:**

**Solution A: Session State Lost After Refresh**
- This is normal - session state is temporary
- Gallery only shows generation from current session
- To persist history, would need database implementation

**Solution B: Too Many Generations**
- Streamlit session state has memory limits
- If generating 100+ logos, memory may be consumed
- Restart app to clear history

---

## 12. Logging & Debugging

### Enable Debug Mode

**Backend Debug:**
```bash
# In backend/app_new.py, change:
# import logging
# logging.basicConfig(level=logging.DEBUG)

# Or run with:
PYTHONUNBUFFERED=1 python backend/app_new.py
```

**Frontend Debug:**
```bash
# Run Streamlit with verbose logging:
streamlit run frontend/streamlit_app.py --logger.level=debug
```

**Browser Console:**
- Press F12 to open DevTools
- Click "Console" tab
- Check for JavaScript errors (red text)

---

### View Network Traffic

**See API Requests:**
1. Open browser DevTools (F12)
2. Click "Network" tab
3. Generate a logo
4. See all HTTP requests to `http://localhost:5050`

**View Request/Response:**
- Click on POST `/api/generate` request
- See full request JSON
- See full response JSON

---

## 13. Reset & Start Fresh

### Complete Reset

If nothing else works, do a complete reset:

```bash
# 1. Delete all generated images
rm -rf backend/generated_logos

# 2. Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
find . -name "*.pyc" -delete

# 3. Clear Streamlit cache
rm -rf ~/.streamlit

# 4. Reinstall dependencies
pip install --upgrade -r requirements.txt

# 5. Restart services
# Terminal 1:
cd backend
python app_new.py

# Terminal 2:
cd frontend
streamlit run streamlit_app.py
```

---

## 14. Get Help

If you've tried everything above and still having issues:

1. **Check the logs** (see section 12)
2. **Verify setup** using: `python verify_setup.py`
3. **Review documentation:**
   - [QUICK_START.md](QUICK_START.md)
   - [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
   - [INTEGRATION_TESTING.md](INTEGRATION_TESTING.md)
4. **Check API status pages:**
   - Gemini: https://status.cloud.google.com/
   - OpenAI: https://status.openai.com/

---

## Quick Reference Table

| Issue | Quick Fix |
|-------|-----------|
| "API Disconnected" | `python backend/app_new.py` |
| "Auth failed" | Check `.env` has API keys |
| "Port in use" | Use different port or kill process |
| "Streamlit won't load" | `rm -r ~/.streamlit` then restart |
| "DALL-E too slow" | Check network, API quota |
| "Gemini won't generate" | Try different description |
| "Can't download" | For DALL-E, download within 1 hour |
| "App crashed" | Check terminal logs |
| "Wrong generator used" | Verify selection, clear cache |
| "Advanced options ignored" | Verify fields in request (F12) |

---

## Still Need Help?

Key files to check:
- `.env` - API keys
- `backend/app_new.py` - Backend setup
- `frontend/.streamlit/secrets.toml` - Frontend config
- `backend/generated_logos/` - Output directory
- Terminal output - Detailed error messages

Good luck! 🚀
