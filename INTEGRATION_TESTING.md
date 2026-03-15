# Integration Testing Guide

## Overview
This guide provides comprehensive testing procedures to verify the Logo Generator integration between the Streamlit frontend and FastAPI backend.

---

## Pre-Testing Checklist

Before running tests, ensure:

- [ ] Python 3.9+ installed
- [ ] `requirements.txt` packages installed
- [ ] `.env` file with valid API keys
- [ ] Backend running at `http://localhost:5050`
- [ ] Streamlit config at `frontend/.streamlit/secrets.toml`
- [ ] No port conflicts (5050 for backend, 8501 for Streamlit)

### Run Verification Script First

```bash
python verify_setup.py
```

Expected output: ✅ ALL CRITICAL CHECKS PASSED

---

## Phase 1: Backend API Testing

### Test 1.1: Health Check

**Objective:** Verify backend is running and all clients are ready.

**Command:**
```bash
curl -X GET http://localhost:5050/api/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "gemini_ready": true,
  "openai_ready": true
}
```

**Verdict:** ✅ PASS if both clients show `true`, ❌ FAIL if either is `false`

---

### Test 1.2: DALL-E 3 Generation via API

**Objective:** Test DALL-E 3 path isolation (GPT-4 Turbo → DALL-E 3).

**Command:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "TechCorp",
    "description": "A leading technology company",
    "style": "tech",
    "palette": "ocean",
    "generator": "dalle-3"
  }'
```

**Expected Response:**
```json
{
  "result": ["https://oaidalleapiprodpol..."],
  "brand": "TechCorp",
  "style": "tech",
  "palette": "ocean",
  "prompt": "Create a professional logo for TechCorp...",
  "generator": "dalle-3"
}
```

**Verification Points:**
- ✅ HTTP 200 response
- ✅ `result` contains HTTPS URL (not file path)
- ✅ `generator` field shows "dalle-3"
- ✅ `prompt` reflects GPT-4 refinement (verbose, professional)

**Verdict:** ✅ PASS if all above, ❌ FAIL if missing URL or wrong generator

---

### Test 1.3: Gemini Generation via API

**Objective:** Test Gemini path isolation (direct generation, no external refinement).

**Command:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ArtistHub",
    "description": "Creative community platform",
    "style": "minimalist",
    "palette": "monochrome",
    "generator": "gemini"
  }'
```

**Expected Response:**
```json
{
  "result": ["generated_logos/gemini_logo_ArtistHub.png"],
  "brand": "ArtistHub",
  "style": "minimalist",
  "palette": "monochrome",
  "prompt": "You are a professional logo designer...",
  "generator": "gemini"
}
```

**Verification Points:**
- ✅ HTTP 200 response
- ✅ `result` contains file path (not URL)
- ✅ `generator` field shows "gemini"
- ✅ `prompt` is direct (not overly refined)
- ✅ File exists at `backend/generated_logos/gemini_logo_ArtistHub.png`

**Verdict:** ✅ PASS if all above, ❌ FAIL if URL returned or file not created

---

### Test 1.4: Advanced Parameters (DALL-E 3)

**Objective:** Verify advanced branding fields work with DALL-E 3.

**Command:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "GreenLeaf",
    "description": "Sustainable agriculture company",
    "style": "nature",
    "palette": "forest",
    "generator": "dalle-3",
    "tagline": "Grow with Nature",
    "typography": "Clean Sans-Serif",
    "elements_to_include": "Leaf, Earth, Growth",
    "elements_to_avoid": "Animals, Chemicals",
    "brand_mission": "Promote sustainable farming practices"
  }'
```

**Expected Response:**
```json
{
  "result": ["https://..."],
  "prompt": "[Should include all 5 advanced fields in the refined prompt]",
  "generator": "dalle-3"
}
```

**Verification Points:**
- ✅ HTTP 200 response
- ✅ Prompt contains: "Leaf", "Earth", "Growth"
- ✅ Prompt avoids: "Animals", "Chemicals"
- ✅ Prompt mentions: "Grow with Nature", "Clean Sans-Serif"

**Verdict:** ✅ PASS if prompt shows rich context, ❌ FAIL if advanced fields ignored

---

### Test 1.5: Advanced Parameters (Gemini)

**Objective:** Verify advanced branding fields work with Gemini.

**Command:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "CloudSync",
    "description": "Cloud synchronization platform",
    "style": "tech",
    "palette": "neon",
    "generator": "gemini",
    "tagline": "Sync Everything",
    "typography": "Modern Geometric",
    "elements_to_include": "Cloud, Network",
    "elements_to_avoid": "Outdated tech",
    "brand_mission": "Connect the world seamlessly"
  }'
```

**Expected Response:**
```json
{
  "result": ["generated_logos/gemini_logo_CloudSync.png"],
  "prompt": "[Should include all 5 advanced fields]",
  "generator": "gemini"
}
```

**Verification Points:**
- ✅ HTTP 200 response
- ✅ Prompt contains all advanced parameters
- ✅ File created in `generated_logos/`
- ✅ File is valid PNG

**Verdict:** ✅ PASS if file created with quality output, ❌ FAIL if empty or missing file

---

## Phase 2: Frontend Integration Testing

### Test 2.1: Streamlit App Loads

**Objective:** Verify Streamlit frontend starts without errors.

**Steps:**
1. Open http://localhost:8501
2. Wait for page to load (Streamlit loading animation)
3. Check for any error messages

**Expected:**
- ✅ Page loads without red error boxes
- ✅ Header shows "🎨 LogoForge AI"
- ✅ Sidebar visible with inputs
- ✅ Three tabs visible: "🎨 Generate", "📚 Gallery", "ℹ️ Info"

**Verdict:** ✅ PASS if page loads cleanly, ❌ FAIL if errors or missing UI

---

### Test 2.2: API Health Check on Load

**Objective:** Verify frontend health check runs on page load.

**Steps:**
1. Open http://localhost:8501
2. Look in the top-right corner of Streamlit sidebar
3. Check for API connection indicator

**Expected:**
- ✅ Shows "✅ API Connected" in green
- ✅ Both "Gemini" and "OpenAI" marked as ready
- ✅ No error messages

**Alternate (Backend Down):**
- Shows "❌ API Disconnected" in red
- Error message: "Cannot connect to backend"

**Verdict:** ✅ PASS if connected, ❌ FAIL if showing error with backend running

---

### Test 2.3: Basic Form Submission (DALL-E 3)

**Objective:** Test minimal generation with DALL-E 3.

**Steps:**
1. Click the "🎨 Generate" tab
2. Enter Brand Name: `QuickLogo`
3. Leave Description blank
4. Select Style: `minimalist`
5. Select Palette: `ocean`
6. Select Generator: `dalle-3`
7. Click "🎨 Generate Logo"

**Expected:**
- ✅ Loading spinner appears
- ✅ After 15-30 seconds, image appears
- ✅ Above image shows: "Generated Logo (🎨 DALL-E 3)"
- ✅ Image is a proper logo (not an error)
- ✅ Download button appears

**Verdict:** ✅ PASS if image appears quickly, ❌ FAIL if error or no image

---

### Test 2.4: Basic Form Submission (Gemini)

**Objective:** Test minimal generation with Gemini.

**Steps:**
1. Click the "🎨 Generate" tab (clear previous)
2. Enter Brand Name: `FastGen`
3. Leave Description blank
4. Select Style: `abstract`
5. Select Palette: `sunset`
6. Select Generator: `gemini`
7. Click "🎨 Generate Logo"

**Expected:**
- ✅ Loading spinner appears
- ✅ After 10-20 seconds, image appears
- ✅ Above image shows: "Generated Logo (✨ Gemini)"
- ✅ Image is a proper logo (not an error)
- ✅ Download button appears
- ✅ File badge, not URL badge

**Verdict:** ✅ PASS if image appears and shows Gemini badge, ❌ FAIL if wrong generator or no image

---

### Test 2.5: Advanced Options Form

**Objective:** Test full form with all advanced options.

**Steps:**
1. Clear the page (refresh if needed)
2. In sidebar, click "⚙️ Show Advanced Options"
3. Fill all fields:
   - Brand Name: `EcoVision`
   - Description: `Sustainable technology startup`
   - Style: nature
   - Palette: forest
   - Generator: dalle-3
   - Tagline: Green Tomorrow
   - Typography: Organic Rounded
   - Elements to Include: Tree, Leaf, Sun
   - Elements to Avoid: Plastic, Factory
   - Brand Mission: Protect our planet
4. Click "🎨 Generate Logo"

**Expected:**
- ✅ Loading spinner appears
- ✅ After generation, "📋 Prompt Used" expander appears
- ✅ Expanding shows comprehensive prompt including all fields
- ✅ Image appears and looks relevant to branding

**Verification in Prompt:**
- Contains: "Green Tomorrow"
- Contains: "Tree, Leaf, Sun"
- Avoids mention of: "Plastic, Factory"
- References mission about planet protection

**Verdict:** ✅ PASS if all fields reflected in prompt, ❌ FAIL if fields ignored

---

### Test 2.6: Generation History

**Objective:** Verify generation history tracking works.

**Steps:**
1. Complete 3 generations (use different names/settings)
2. Click the "📚 Gallery" tab
3. Scroll through history

**Expected:**
- ✅ All 3 generations visible with thumbnails
- ✅ Each shows timestamp
- ✅ Each shows generator badge (dalle-3 or gemini)
- ✅ Can click to expand details
- ✅ Download button for each

**Verdict:** ✅ PASS if all generations tracked, ❌ FAIL if history missing or incomplete

---

### Test 2.7: Download Functionality (DALL-E 3)

**Objective:** Test download for DALL-E 3 generated image.

**Steps:**
1. Generate a logo with DALL-E 3
2. Click "📥 Download" button next to image
3. Check Downloads folder

**Expected:**
- ✅ Image downloads successfully
- ✅ File is valid PNG image
- ✅ File opens in image viewer
- ✅ File name includes brand name

**Verdict:** ✅ PASS if file downloads and opens, ❌ FAIL if download fails or corrupted file

---

### Test 2.8: Download Functionality (Gemini)

**Objective:** Test download for Gemini generated image.

**Steps:**
1. Generate a logo with Gemini
2. Click "📥 Download" button next to image
3. Check Downloads folder

**Expected:**
- ✅ Image downloads successfully
- ✅ File is valid PNG image
- ✅ File opens in image viewer
- ✅ File name includes brand name

**Verdict:** ✅ PASS if file downloads and opens, ❌ FAIL if download fails

---

### Test 2.9: Info Tab

**Objective:** Verify Info tab displays properly.

**Steps:**
1. Click "ℹ️ Info" tab
2. Review all sections
3. Check API Health Status section

**Expected:**
- ✅ "📊 API Health Status" section exists
- ✅ Shows Gemini status
- ✅ Shows OpenAI status
- ✅ "🎨 Supported Styles" section lists all styles
- ✅ "🎨 Supported Color Palettes" section lists all palettes
- ✅ No error messages

**Verdict:** ✅ PASS if all information displayed correctly, ❌ FAIL if missing sections

---

## Phase 3: Generator Isolation Testing

### Test 3.1: DALL-E Should Not Call Gemini

**Objective:** Verify DALL-E 3 path never uses Gemini API.

**Steps:**
1. Check backend logs for API calls
2. Generate DALL-E 3 logo
3. Monitor network panel or logs

**Expected:**
- ✅ Only OpenAI API calls in logs:
  - `openai.chat.completions` (GPT-4 Turbo)
  - `openai.images.generate` (DALL-E 3)
- ❌ NO Google GenAI calls

**Verification (in backend terminal output):**
```
[Expected] Creating GPT-4 Turbo completion for prompt refinement
[Expected] Calling OpenAI DALL-E 3 API
[Expected] Successfully generated DALL-E logo
[NOT Expected] Initializing Gemini client
[NOT Expected] Calling Gemini API
```

**Verdict:** ✅ PASS if no Gemini calls logged, ❌ FAIL if Gemini API used

---

### Test 3.2: Gemini Should Not Call OpenAI

**Objective:** Verify Gemini path never uses OpenAI API.

**Steps:**
1. Check backend logs for API calls
2. Generate Gemini logo
3. Monitor network panel or logs

**Expected:**
- ✅ Only Gemini API calls:
  - `genai.models.generate_content` (Gemini 2.0 Flash)
- ❌ NO OpenAI API calls (no chat, no images)

**Verification (in backend terminal output):**
```
[Expected] Calling Gemini API
[Expected] Writing image to local file
[NOT Expected] Creating OpenAI client
[NOT Expected] Calling OpenAI API
[NOT Expected] Calling DALL-E
```

**Verdict:** ✅ PASS if no OpenAI calls logged, ❌ FAIL if OpenAI API used

---

## Phase 4: Error Handling Testing

### Test 4.1: Invalid API Key

**Objective:** Verify graceful error handling for invalid API keys.

**Steps:**
1. Temporarily modify `.env` with invalid OpenAI key
2. Restart backend
3. Try to generate DALL-E 3 logo

**Expected:**
- ✅ Streamlit shows error message (not blank page)
- ✅ Error message mentions "Authentication failed" or "Invalid API key"
- ✅ User can still retry or switch generator

**Verdict:** ✅ PASS if helpful error shown, ❌ FAIL if silent failure or crash

---

### Test 4.2: Backend Disconnected

**Objective:** Verify frontend handles backend being offline.

**Steps:**
1. Stop backend (Ctrl+C)
2. Try to generate a logo
3. Check Streamlit

**Expected:**
- ✅ "❌ API Disconnected" appears in sidebar
- ✅ Form shows error: "Cannot connect to backend"
- ✅ No attempt to process (no spinner)
- ✅ User prompted to start backend

**Verdict:** ✅ PASS if clear error message, ❌ FAIL if orphaned loading spinner

---

### Test 4.3: Empty Brand Name

**Objective:** Verify validation of required fields.

**Steps:**
1. Leave Brand Name empty
2. Fill other fields
3. Click Generate

**Expected:**
- ✅ Validation error appears
- ✅ Message: "Brand name is required"
- ✅ No API call made

**Verdict:** ✅ PASS if error before API call, ❌ FAIL if API called with empty value

---

## Phase 5: Performance Testing

### Test 5.1: Generation Speed (DALL-E 3)

**Objective:** Verify DALL-E 3 completes in reasonable time.

**Steps:**
1. Note start time
2. Generate DALL-E 3 logo
3. Note end time
4. Record duration

**Expected:**
- ✅ Completes in 15-35 seconds (includes network latency)
- ⚠️  May take up to 60 seconds on slow networks

**Verdict:** ✅ PASS if < 40 seconds typical, ⚠️  WARN if 40-60 seconds, ❌ FAIL if > 60 seconds

---

### Test 5.2: Generation Speed (Gemini)

**Objective:** Verify Gemini completes quickly.

**Steps:**
1. Note start time
2. Generate Gemini logo
3. Note end time
4. Record duration

**Expected:**
- ✅ Completes in 10-25 seconds
- ⚠️  May take up to 40 seconds on slow networks

**Verdict:** ✅ PASS if < 30 seconds typical, ⚠️  WARN if 30-45 seconds, ❌ FAIL if > 45 seconds

---

### Test 5.3: Memory Usage

**Objective:** Verify app doesn't leak memory with multiple generations.

**Steps:**
1. Open system monitor
2. Start Streamlit app and note memory usage
3. Generate 10 logos (5 DALL-E, 5 Gemini)
4. Check memory usage after

**Expected:**
- ✅ Memory remains stable (< 500MB increase)
- ✅ No gradual increase after each generation

**Verdict:** ✅ PASS if memory stable, ❌ FAIL if continuous increase

---

## Summary Report Template

```
═══════════════════════════════════════════════════════════════
                    INTEGRATION TEST REPORT
═══════════════════════════════════════════════════════════════

Date: [DATE]
Tester: [NAME]
Environment: [Windows/Mac/Linux] Python [VERSION]

PHASE 1: BACKEND API TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 1.1 - Health Check:                    [✅ PASS / ❌ FAIL]
Test 1.2 - DALL-E 3 Generation:             [✅ PASS / ❌ FAIL]
Test 1.3 - Gemini Generation:               [✅ PASS / ❌ FAIL]
Test 1.4 - Advanced Parameters (DALLE):     [✅ PASS / ❌ FAIL]
Test 1.5 - Advanced Parameters (Gemini):    [✅ PASS / ❌ FAIL]

PHASE 2: FRONTEND INTEGRATION TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 2.1 - Streamlit App Loads:             [✅ PASS / ❌ FAIL]
Test 2.2 - API Health Check:                [✅ PASS / ❌ FAIL]
Test 2.3 - Basic DALL-E 3 Submission:       [✅ PASS / ❌ FAIL]
Test 2.4 - Basic Gemini Submission:         [✅ PASS / ❌ FAIL]
Test 2.5 - Advanced Options Form:           [✅ PASS / ❌ FAIL]
Test 2.6 - Generation History:              [✅ PASS / ❌ FAIL]
Test 2.7 - Download (DALL-E 3):             [✅ PASS / ❌ FAIL]
Test 2.8 - Download (Gemini):               [✅ PASS / ❌ FAIL]
Test 2.9 - Info Tab:                        [✅ PASS / ❌ FAIL]

PHASE 3: GENERATOR ISOLATION TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 3.1 - DALL-E Doesn't Call Gemini:      [✅ PASS / ❌ FAIL]
Test 3.2 - Gemini Doesn't Call OpenAI:      [✅ PASS / ❌ FAIL]

PHASE 4: ERROR HANDLING TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 4.1 - Invalid API Key:                 [✅ PASS / ❌ FAIL]
Test 4.2 - Backend Disconnected:            [✅ PASS / ❌ FAIL]
Test 4.3 - Empty Brand Name:                [✅ PASS / ❌ FAIL]

PHASE 5: PERFORMANCE TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test 5.1 - DALL-E 3 Speed:                  [Time: ___s]
Test 5.2 - Gemini Speed:                    [Time: ___s]
Test 5.3 - Memory Usage:                    [✅ STABLE / ❌ LEAK]

═══════════════════════════════════════════════════════════════
OVERALL RESULT:        [✅ ALL PASS / ⚠️  SOME WARNINGS / ❌ FAILURES]
═══════════════════════════════════════════════════════════════

NOTES:
[Additional observations, bugs, or recommendations]

SIGN-OFF:   ________________  ________________
            Tester            Date
```

---

## Automation Script (Optional)

To run basic API tests automatically:

```bash
python run_integration_tests.py
```

This script will:
1. Check backend health
2. Test both generators
3. Report results in JSON format

---

## When All Tests Pass ✅

Your Logo Generator is production-ready. You can:
- ✅ Deploy frontend to Streamlit Cloud
- ✅ Deploy backend to production server
- ✅ Configure custom domain
- ✅ Set up API rate limiting
- ✅ Monitor performance in production

Congratulations! 🎉
