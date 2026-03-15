# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Verify Setup (1 min)

```bash
# Navigate to backend
cd backend

# Check Python
python --version  # Should be 3.8+

# Check dependencies
pip list | grep -E "fastapi|pydantic|google-genai|openai|pillow"
```

### Step 2: Check Environment Variables (1 min)

```bash
# Verify .env file exists
cat ../.env

# Should contain:
# GEMINI_API_KEY=your_key
# OPENAI_API_KEY=your_key
```

### Step 3: Run Tests (2 min)

```bash
# Run comprehensive tests
python test_refactored.py

# Expected output:
# ✅ Gemini Client: Ready
# ✅ OpenAI Client: Ready
# ✅ DALL-E 3 generation successful!
# ✅ Gemini generation successful!
```

### Step 4: Start Server (1 min)

```bash
# Option A: Direct Python
python app_new.py

# Option B: Uvicorn (with auto-reload)
uvicorn app_new:app --reload --port 5050
```

Server runs at: `http://localhost:5050`

---

## 📝 Test API Calls

### Health Check
```bash
curl http://localhost:5050/api/health
```

Response:
```json
{
  "status": "ok",
  "gemini_ready": true,
  "openai_ready": true
}
```

### Generate with DALL-E 3
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "TechVision",
    "description": "AI-powered company",
    "style": "minimalist",
    "palette": "ocean",
    "generator": "dalle-3"
  }'
```

### Generate with Gemini
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "TechVision",
    "description": "AI-powered company",
    "style": "minimalist",
    "palette": "ocean",
    "generator": "gemini"
  }'
```

---

## 📚 Documentation Quick Links

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | Detailed system design and how everything works together |
| `MIGRATION.md` | Frontend integration & API changes |
| `REFACTORING_SUMMARY.md` | Before/after, what changed and why |
| `DIAGRAMS_AND_FLOWS.md` | Visual diagrams and flow charts |
| `DEPLOYMENT_CHECKLIST.md` | Deployment & production readiness |
| `QUICK_START.md` | This file - get running fast |

**New to the refactored code?** Start here:
1. Quick Start (this file)
2. Architecture (to understand structure)
3. Diagrams (to visualize flows)
4. MIGRATION (to integrate with frontend)

---

## 🎨 Available Styles & Palettes

### Logo Styles
```
- minimalist    : clean, simple geometric shapes
- tech          : modern, futuristic, sleek lines
- vintage       : retro, classic typography
- abstract      : creative, symbolic
- mascot        : character, friendly
- luxury        : elegant, sophisticated
```

### Color Palettes
```
- monochrome    : Black & White
- ocean         : Blue, Cyan
- sunset        : Red, Orange, Yellow
- forest        : Greens & Mint
- royal         : Purple & Gold
- neon          : Bright colors
```

### Example Request
```json
{
  "text": "MyBrand",
  "description": "Digital marketing agency",
  "style": "minimalist",
  "palette": "ocean",
  "generator": "dalle-3"
}
```

---

## 🔧 Project Structure

```
backend/
├── app_new.py              ← Main app (ready to use!)
├── routers.py              ← API routes
├── services.py             ← Business logic (Gemini + DALL-E)
├── models.py               ← Data validation
├── config.py               ← Constants & templates
├── dependencies.py         ← Client initialization
├── utils.py                ← Helpers
├── test_refactored.py      ← Tests
├── ARCHITECTURE.md         ← Detailed design
├── MIGRATION.md            ← Frontend integration
├── REFACTORING_SUMMARY.md  ← What changed
├── DIAGRAMS_AND_FLOWS.md   ← Visual guides
├── DEPLOYMENT_CHECKLIST.md ← Production ready
└── QUICK_START.md          ← This file
```

---

## 🎯 Key Differences from Old App

| Feature | Old | New |
|---------|-----|-----|
| **Code organization** | Single file | Modular (7 modules) |
| **Type safety** | None | Pydantic models |
| **Generators** | DALL-E only | DALL-E + Gemini |
| **Image generation** | Prompt refinement only | Direct generation possible |
| **API endpoint** | `/generate` | `/api/generate` |
| **Health check** | ❌ | ✅ /api/health |
| **Error messages** | Generic | Detailed & helpful |
| **Testability** | Hard | Easy (unit testable) |
| **Extensibility** | Difficult | Easy (service-based) |
| **Documentation** | Minimal | Comprehensive (4 docs) |

---

## ⚡ Common Workflows

### Development
```bash
# 1. Start server with auto-reload
uvicorn app_new:app --reload

# 2. Test in another terminal
curl http://localhost:5050/api/health

# 3. Make code changes
# → Server auto-reloads

# 4. See changes immediately
```

### Adding New Generator
1. Create new `XyzService` in `services.py`
2. Add to `LLMService` 
3. Add generator option in `config.py`
4. Add route logic in `routers.py`
5. Test with `test_refactored.py`

### Adding New Style/Palette
1. Add to `LOGO_STYLES` or `COLOR_PALETTES` in `config.py`
2. No code changes needed!
3. Automatically available via API

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
# Install missing packages
pip install -r requirements.txt
```

### "API Key not initialized"
```bash
# Check .env file
cat ../.env

# Verify keys are set
# Restart server
```

### "Port already in use"
```bash
# Use different port
uvicorn app_new:app --port 5051

# Or find and kill process on 5050
lsof -i :5050
kill -9 <PID>
```

### "Timeout on generation"
This is normal! Gemini/DALL-E take 10-30 seconds.
- Be patient
- Increase timeout in client code
- Check API status pages

---

## 📊 API Response Examples

### DALL-E 3 Response
```json
{
  "result": [
    "https://..url..to..image.."
  ],
  "brand": "TechVision",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Clean minimalist vector logo featuring...",
  "generator": "dalle-3"
}
```

### Gemini Response
```json
{
  "result": [
    "generated_logos/gemini_logo_TechVision.png"
  ],
  "brand": "TechVision",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Create a professional logo for...",
  "generator": "gemini"
}
```

---

## 🔐 Security Notes

✅ **Already handled:**
- Type validation (Pydantic)
- Input sanitization
- Error message safety
- Environment variable protection

⚠️ **You should handle:**
- API key rotation (periodically)
- CORS origin validation (restrict domains)
- Rate limiting (prevent abuse)
- HTTPS in production

---

## 📞 Need Help?

1. **See modular code?** → Read `ARCHITECTURE.md`
2. **Want to visualize flows?** → Check `DIAGRAMS_AND_FLOWS.md`
3. **Integrating with frontend?** → Follow `MIGRATION.md`
4. **Ready for production?** → Use `DEPLOYMENT_CHECKLIST.md`
5. **Curious about changes?** → Review `REFACTORING_SUMMARY.md`

---

## ✅ Success Checklist

When you see these, you're all set:

- [x] Server running: `Uvicorn running on http://0.0.0.0:5050`
- [x] Health check works: `{"status": "ok", ...}`
- [x] Can generate with DALL-E 3 (returns URL)
- [x] Can generate with Gemini (saves image locally)
- [x] No error in terminal output
- [x] Can access API docs: `http://localhost:5050/docs`

---

## 🎉 What You Have Now

```
✨ Production-ready refactored backend
✨ Dual image generator support (DALL-E + Gemini)
✨ Type-safe API with Pydantic
✨ Modular architecture (easy to extend)
✨ Comprehensive test suite
✨ Detailed documentation (4 guides)
✨ Clear deployment path
✨ Beautiful API docs (Swagger UI)
```

**Ready to go! 🚀**

---

## Next Steps

1. **Verify** everything works: `python test_refactored.py`
2. **Read** architecture guide: `cat ARCHITECTURE.md`
3. **Start** the server: `python app_new.py`
4. **Test** with curl or frontend
5. **Deploy** when ready using checklist

Happy coding! 💻
