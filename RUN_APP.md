# Run Logo Generator

## Quick Start

### 1. Setup Environment
```bash
# Create virtual environment (if not done)
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys
Create `.env` file in project root:
```env
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 3. Start Backend (Terminal 1)
```bash
cd backend
python app_new.py
```
Backend runs on: http://localhost:5050

### 4. Start Frontend (Terminal 2)
```bash
cd frontend
streamlit run streamlit_app.py
```
Frontend opens at: http://localhost:8501

### 5. Generate Your Logo!
- Open http://localhost:8501
- Enter brand name
- Click "🚀 Generate Logo"
- Choose DALL-E 3 or Gemini
- Download result

---

## Verification

Before running, verify everything:
```bash
python verify_setup.py
```

Should show: ✅ ALL CRITICAL CHECKS PASSED

---

## Troubleshooting

### "API Disconnected"
- Backend not running
- Run: `cd backend && python app_new.py`

### "Secrets file not found"
- Already created automatically at `frontend/.streamlit/secrets.toml`
- If missing, it will use localhost:5050 as default

### Generation fails
- Check API keys in `.env`
- Verify API quotas
- Check terminal logs for details

See: TROUBLESHOOTING.md for more solutions
