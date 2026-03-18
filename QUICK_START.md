# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.9+
- GEMINI_API_KEY (from Google AI Studio)
- OPENAI_API_KEY (from OpenAI)

---

## Step 1: Environment Setup

```bash
# Create .env file in project root
cat > .env << EOF
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
EOF
```

**Where to get API Keys:**
- **GEMINI_API_KEY**: https://aistudio.google.com/app/apikey
- **OPENAI_API_KEY**: https://platform.openai.com/account/api-keys

---

## Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

---

## Step 3: Start Backend (Terminal 1)

```bash
# Navigate to backend directory
cd backend

# Run the FastAPI server
python app_new.py
```

✅ **Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:5050
INFO:     Application startup complete
INFO:     Gemini client initialized: Ready
INFO:     OpenAI client initialized: Ready
```

Test the backend:
```bash
curl http://localhost:5050/api/health
```

Should return:
```json
{"status": "ok", "gemini_ready": true, "openai_ready": true}
```

---

## Step 4: Start Frontend (Terminal 2)

```bash
# Navigate to frontend directory
cd frontend

# Create Streamlit config (if not exists)
mkdir -p .streamlit
echo 'API_BASE_URL = "http://localhost:5050"' > .streamlit/secrets.toml

# Run the Streamlit app
streamlit run streamlit_app.py
```

✅ **Expected Output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

---

## Step 5: Open Browser

1. **Open Streamlit UI**: http://localhost:8501
2. **Look for**: ✅ API Connected (green indicator)
3. **You're Ready to Generate!**

---

## Generate Your First Logo

### Simple Generation (2 fields)
1. Enter **Brand Name**: `TechVision`
2. Select **Generator**: `dalle-3`
3. Click **🎨 Generate Logo**
4. Wait 15-30 seconds
5. See your generated logo!

### Advanced Generation (all fields)
1. Click **⚙️ Show Advanced Options** in sidebar
2. Fill additional fields:
   - Typography: `Modern Sans-Serif`
   - Tagline: `Innovation at Speed`
   - Include Elements: `Gear, Cloud`
   - Avoid Elements: `Abstract Shapes`
   - Brand Mission: `Empower businesses`
3. Click **🎨 Generate Logo**
4. View advanced prompt used
5. Download the result

---

## 📚 View Generation History

1. Click **📚 Gallery** tab
2. See all your generated logos
3. View generation details (timestamp, generator, prompt)
4. Download any previous generation

---

## ℹ️ Check API Status

1. Click **ℹ️ Info** tab
2. View API Health Status
3. See available generators
4. Read feature descriptions

---

## 🎨 Generator Selection Guide

### DALL-E 3 (Recommended for Quality)
✅ **Best for:**
- Professional logos
- High-quality outputs
- Cloud-hosted images (disposable URLs)
- When time isn't a concern

⏱️ **Speed:** 15-30 seconds
📍 **Storage:** Cloud (OpenAI servers)
💾 **Download:** Direct URL

### Gemini (Recommended for Speed)
✅ **Best for:**
- Fast iterations
- Testing multiple concepts
- Local file storage
- Direct generation without refinement

⏱️ **Speed:** 10-20 seconds  
📍 **Storage:** Local files
💾 **Download:** PNG file

---

## 🎯 Common Tasks

### Download a Logo
1. Go to **📚 Gallery** tab
2. Find your logo
3. Click **📥 Download** button
4. Save to your computer

### View the Prompt Used
1. After generation, expand **📋 Prompt Used** section
2. See the full prompt sent to the generator
3. Useful for understanding generation quality

### Check API Connection
1. Open **ℹ️ Info** tab
2. Look at **API Health Status**
3. Shows both Gemini and OpenAI status

### Change Generators
1. In **🎨 Generate** tab
2. Switch between `dalle-3` and `gemini`
3. Keep all other fields the same
4. Generate to compare results

---

## ⚠️ Troubleshooting

### Problem: "Cannot connect to API"

**Check if backend is running:**
```bash
curl http://localhost:5050/api/health
```

**If not running:**
```bash
cd backend
python app_new.py
```

---

### Problem: "API Connected but generator not ready"

**Check .env file:**
```bash
cat .env
# Should show both GEMINI_API_KEY and OPENAI_API_KEY
```

**Verify API keys are valid:**
- Test GEMINI key: https://aistudio.google.com/app/
- Test OPENAI key: https://platform.openai.com/account/

**Restart backend:**
```bash
# Press Ctrl+C in backend terminal
# Then run:
python app_new.py
```

---

### Problem: Generation fails with error

**Check the error message in Streamlit:**
- DALL-E errors: Usually quota or API key issues
- Gemini errors: Usually API key or quota issues

**Solutions:**
1. Verify API keys in `.env`
2. Check API quotas
3. Ensure API billing is enabled
4. Check API rate limits

---

### Problem: Download button doesn't work

**For DALL-E 3:**
- Images are temporary URLs (expire in 1 hour)
- Download immediately after generation
- May fail if URL expired

**For Gemini:**
- Check if `backend/generated_logos/` directory was created
- Ensure write permissions on that directory
- Files should be saved as PNG

---

## 🔧 Advanced Configuration

### Change API Server Port

**Edit `backend/app_new.py`:**
```python
# Change this line:
uvicorn.run(app, host="0.0.0.0", port=5050)

# To your desired port:
uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Then update Streamlit config:**
```bash
echo 'API_BASE_URL = "http://localhost:8000"' > frontend/.streamlit/secrets.toml
```

### Change Streamlit Port

```bash
streamlit run frontend/streamlit_app.py --server.port 9000
# Access at http://localhost:9000
```

### Disable Browser Auto-Open

```bash
streamlit run frontend/streamlit_app.py --logger.level=error
```

---

## 📊 Performance Tips

### Faster Generations with Gemini
- Use `gemini` generator (10-20 sec vs 15-30 sec)
- Keep descriptions short and focused
- Avoid very stylized requests

### Better Quality with DALL-E 3
- Use `dalle-3` generator
- Provide detailed descriptions
- Use advanced options for precise control
- Allow 20-30 seconds for generation

### Optimize Advanced Options
- Be specific with what to include/avoid
- Use clear, simple language
- Avoid conflicting requirements

---

## 🚀 Next Steps

1. **Generate 5-10 logos** to test both generators
2. **Compare quality** between DALL-E 3 and Gemini
3. **Try advanced options** with different settings
4. **Download** your favorite logos
5. **Review** generation history in Gallery tab

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **INTEGRATION_GUIDE.md** | Complete setup & troubleshooting |
| **QUICK_START.md** | This file - get started fast |
| **backend/ARCHITECTURE.md** | Backend structure & design |
| **backend/DIAGRAMS_AND_FLOWS.md** | Visual flow diagrams |

---

## 💡 Pro Tips

1. **Bookmark the URLs:**
   - Streamlit UI: http://localhost:8501
   - API Docs: http://localhost:5050/docs

2. **Test with simple inputs first:**
   - Just brand name + style + palette
   - Then add advanced options

3. **Use generator comparison:**
   - Generate same logo with both
   - DALL-E for quality, Gemini for speed

4. **Save your favorites:**
   - Use Gallery tab to view all generations
   - Download keeps a local copy

5. **Read the Info tab:**
   - Shows all available styles and palettes
   - Lists supported features

---

## ❓ Need Help?

1. **Check Streamlit UI** for error messages (red text)
2. **Check terminal** where backend is running for API errors
3. **Check .env file** for correct API keys
4. **Check API status** in Info tab
5. **Check firewall** if port 5050 is blocked

---

## 🎉 You're All Set!

Your Logo Generator with DALL-E 3 and Gemini support is ready to use.

Generate amazing logos! 🎨
