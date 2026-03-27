"""
LogoForge AI – Streamlit shell with embedded HTML/JS UI.

Architecture note
─────────────────
To avoid f-string escaping bugs ({{ vs { in CSS/JS), the HTML, CSS and JS
are built as regular strings and joined — NOT as one giant f-string.
Only the tiny pieces that need the Python API_BASE_URL variable use
an f-string or .format(). This guarantees JS template literals, CSS
selectors and onclick handlers are never accidentally mangled.
"""

import streamlit as st
import requests

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="LogoForge AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── API URL ────────────────────────────────────────────────────
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:5050")
except Exception:
    API_BASE_URL = "http://localhost:5050"


def check_api_health():
    try:
        r = requests.get(f"{API_BASE_URL}/api/health", timeout=4)
        if r.status_code == 200:
            return True, r.json()
        return False, {}
    except Exception:
        return False, {}


# ── Hide Streamlit chrome; keep iframe fully interactive ────────
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
    [data-testid="stVerticalBlock"]    { gap: 0 !important; }
    section[data-testid="stMain"]      { padding: 0 !important; }
    .block-container                   { padding: 0 !important; max-width: 100% !important; }
    iframe { pointer-events: auto !important; border: none; }
    [data-testid="stCustomComponentV1"] { pointer-events: auto !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Backend Status")
    health_ok, health_data = check_api_health()
    if health_ok:
        st.success("✅ API Connected")
        st.markdown(f"{'✅' if health_data.get('gemini_ready') else '❌'} Gemini ready")
        st.markdown(f"{'✅' if health_data.get('openai_ready') else '❌'} OpenAI ready")
    else:
        st.error("❌ API Disconnected")
        st.caption(f"Expected at {API_BASE_URL}")
    st.markdown("---")
    st.markdown("### 📡 Backend URL")
    st.code(API_BASE_URL, language="text")
    st.markdown("---")
    st.markdown("**Start backend:**\n```bash\ncd backend\npython app_new.py\n```")


# ══════════════════════════════════════════════════════════════════════════════
#  HTML COMPONENT  — built as plain string concatenation, never one f-string
# ══════════════════════════════════════════════════════════════════════════════

# ---------- CSS (plain string — no Python variable interpolation needed) ------
CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{
  --bg:#E6E6E6; --surface:#FFFFFF; --surface2:#F5F5F5;
  --border:rgba(21,22,25,.08); --text:#151619; --muted:rgba(21,22,25,.45);
  --red:#FF4444; --red-glow:rgba(255,68,68,.25);
  --dark:#0A0B0D; --dark2:#1A1B1F;
  --font:'Space Grotesk',sans-serif; --mono:'JetBrains Mono',monospace;
}
html,body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}

/* Header */
.hdr{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.72);
  backdrop-filter:blur(14px);border-bottom:1px solid var(--border);
  padding:.85rem 1.5rem;display:flex;align-items:center;justify-content:space-between;}
.hdr-brand{display:flex;align-items:center;gap:.6rem;}
.hdr-icon{width:38px;height:38px;background:var(--text);border-radius:10px;
  display:flex;align-items:center;justify-content:center;}
.hdr-icon svg{color:#fff;width:20px;height:20px;}
.hdr h1{font-size:1.05rem;font-weight:800;letter-spacing:-.02em;text-transform:uppercase;}
.hdr-pill{font-family:var(--mono);font-size:.65rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);}

/* Main grid */
.main{max-width:1320px;margin:0 auto;padding:2.5rem 1.5rem;
  display:grid;grid-template-columns:1fr 1.35fr;gap:2rem;}
@media(max-width:900px){.main{grid-template-columns:1fr;}}

/* Panel */
.panel{background:var(--surface);border-radius:1.25rem;padding:2rem;
  border:1px solid var(--border);display:flex;flex-direction:column;gap:1.5rem;overflow:visible;}

.label{display:flex;align-items:center;gap:.4rem;font-family:var(--mono);
  font-size:.65rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);margin-bottom:.6rem;}
.label svg{width:13px;height:13px;}

/* Inputs */
input[type=text],textarea{
  width:100%;max-width:100%;background:var(--surface2);border:none;border-radius:.75rem;
  padding:.8rem 1rem;font-family:var(--font);font-size:.95rem;color:var(--text);
  outline:none;resize:none;transition:box-shadow .2s;overflow:hidden;text-overflow:ellipsis;}
input[type=text]:focus,textarea:focus{box-shadow:0 0 0 2px var(--text);overflow:auto;text-overflow:clip;}
input::placeholder,textarea::placeholder{color:var(--muted);}

/* Advanced toggle */
.adv-toggle{display:flex;align-items:center;justify-content:space-between;
  background:none;border:none;width:100%;cursor:pointer;font-family:var(--mono);
  font-size:.65rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);
  padding:.25rem 0;transition:color .2s;}
.adv-toggle:hover{color:var(--text);}
.adv-toggle .chevron{width:14px;height:14px;transition:transform .3s;}
.adv-toggle.open .chevron{transform:rotate(180deg);}
.adv-body{max-height:0;overflow:hidden;transition:max-height .35s ease,opacity .3s ease;opacity:0;}
.adv-body.open{max-height:800px;opacity:1;}
.adv-inner{display:flex;flex-direction:column;gap:.85rem;padding-top:.75rem;
  padding-left:2px;padding-right:2px;}
.row2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:.75rem;}
.field-label{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.12em;color:var(--muted);display:flex;align-items:center;gap:.3rem;margin-bottom:.35rem;}
.field-label svg{width:10px;height:10px;}

/* Chip buttons */
.btn-grid{display:grid;gap:.5rem;}
.btn-grid.cols2{grid-template-columns:1fr 1fr;}
.btn-grid.cols3{grid-template-columns:1fr 1fr 1fr;}
.chip{background:var(--surface2);border:2px solid transparent;border-radius:.7rem;
  padding:.5rem .75rem;font-size:.8rem;font-weight:600;cursor:pointer;
  transition:all .15s;text-align:center;font-family:var(--font);}
.chip:hover{background:#eee;}
.chip.active{background:var(--text);color:#fff;border-color:var(--text);}

/* Palette chips */
.pal-chip{background:var(--surface2);border:2px solid transparent;border-radius:.7rem;
  padding:.5rem .6rem;display:flex;flex-direction:column;align-items:center;gap:.35rem;
  cursor:pointer;transition:all .15s;}
.pal-chip:hover{background:#eee;}
.pal-chip.active{border-color:var(--text);background:var(--surface);}
.pal-dots{display:flex;gap:3px;}
.pal-dot{width:14px;height:14px;border-radius:50%;border:1px solid rgba(0,0,0,.1);}
.pal-name{font-size:.62rem;font-weight:600;color:var(--muted);}
.pal-chip.active .pal-name{color:var(--text);}

/* Generator hint */
.gen-hint{font-size:.78rem;color:var(--muted);margin-top:.45rem;
  padding:.5rem .7rem;background:var(--surface2);border-radius:.5rem;line-height:1.5;}

/* Generate row */
.gen-row{display:flex;gap:.6rem;align-items:stretch;}

/* Generate button */
.gen-btn{flex:1;background:var(--red);color:#fff;border:none;border-radius:.9rem;
  padding:1.05rem;font-family:var(--font);font-size:1.05rem;font-weight:700;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:.5rem;
  box-shadow:0 8px 24px var(--red-glow);transition:all .2s;}
.gen-btn:hover{background:#e63e3e;transform:translateY(-2px);box-shadow:0 12px 28px var(--red-glow);}
.gen-btn:active{transform:scale(.98);}
.gen-btn:disabled{background:rgba(255,68,68,.45);cursor:not-allowed;transform:none;box-shadow:none;}

/* Cancel button */
.cancel-btn{flex-shrink:0;background:#fff;color:var(--red);
  border:2px solid var(--red);border-radius:.9rem;padding:0 1.1rem;
  font-family:var(--font);font-weight:700;font-size:.88rem;cursor:pointer;
  transition:all .2s;white-space:nowrap;display:none;}
.cancel-btn:hover{background:rgba(255,68,68,.06);}

/* Progress bar */
.progress-wrap{display:none;flex-direction:column;gap:.4rem;}
.progress-wrap.show{display:flex;}
.progress-track{height:4px;background:rgba(255,68,68,.15);border-radius:2px;overflow:hidden;}
.progress-fill{height:100%;background:var(--red);border-radius:2px;width:0%;transition:width .4s ease;}
.progress-label{font-family:var(--mono);font-size:.62rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);}

/* Error box */
.err{background:rgba(255,68,68,.1);border:1px solid rgba(255,68,68,.25);
  border-radius:.75rem;padding:.8rem 1rem;font-size:.82rem;font-weight:500;
  color:var(--red);text-align:center;}

/* Preview panel */
.preview-wrap{display:flex;flex-direction:column;gap:1.25rem;}
.canvas-card{background:var(--surface);border-radius:1.5rem;border:1px solid var(--border);
  aspect-ratio:1/1;display:flex;flex-direction:column;overflow:hidden;position:relative;}
.canvas-top{display:flex;align-items:center;gap:.5rem;padding:.9rem 1.1rem;border-bottom:1px solid var(--border);}
.pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--red);animation:pulseDot 2s ease-in-out infinite;}
@keyframes pulseDot{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.4;transform:scale(.7);}}
.canvas-label{font-family:var(--mono);font-size:.62rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);}
.canvas-body{flex:1;display:flex;align-items:center;justify-content:center;
  background:var(--surface2);position:relative;overflow:hidden;padding:2rem;}
.placeholder{display:flex;flex-direction:column;align-items:center;gap:.85rem;color:rgba(21,22,25,.15);text-align:center;}
.placeholder svg{width:64px;height:64px;stroke-width:1;}
.placeholder p{font-family:var(--mono);font-size:.65rem;text-transform:uppercase;letter-spacing:.14em;}
.logo-img{max-width:85%;max-height:85%;object-fit:contain;border-radius:.75rem;
  filter:drop-shadow(0 12px 24px rgba(0,0,0,.12));animation:fadeIn .4s ease;}
@keyframes fadeIn{from{opacity:0;transform:scale(.95);}to{opacity:1;transform:scale(1);}}
.loading-state{display:flex;flex-direction:column;align-items:center;gap:1rem;text-align:center;}
.loader-ring{width:56px;height:56px;border:3px solid rgba(255,68,68,.2);
  border-top:3px solid var(--red);border-radius:50%;animation:spin 1s linear infinite;}
.loading-state p{font-family:var(--mono);font-size:.65rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);}
.loading-state small{font-size:.58rem;color:rgba(21,22,25,.3);margin-top:-.4rem;}
@keyframes spin{to{transform:rotate(360deg);}}
.var-badge{position:absolute;top:.8rem;right:.8rem;background:rgba(21,22,25,.06);
  border:1px solid rgba(21,22,25,.1);border-radius:2rem;padding:.25rem .65rem;
  font-family:var(--mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);}
.canvas-actions{position:absolute;bottom:1.25rem;left:50%;transform:translateX(-50%);display:flex;gap:.75rem;}
.act-btn{padding:.65rem 1.2rem;border-radius:2rem;font-weight:700;font-size:.82rem;
  cursor:pointer;display:flex;align-items:center;gap:.4rem;
  transition:all .2s;white-space:nowrap;border:none;font-family:var(--font);}
.act-btn svg{width:15px;height:15px;}
.act-primary{background:var(--text);color:#fff;box-shadow:0 4px 12px rgba(21,22,25,.25);}
.act-primary:hover{background:#2a2b30;transform:translateY(-1px);}
.act-secondary{background:var(--surface);color:var(--text);border:1px solid var(--border);box-shadow:0 2px 8px rgba(21,22,25,.08);}
.act-secondary:hover{background:var(--surface2);transform:translateY(-1px);}
.act-btn:disabled{opacity:.45;cursor:not-allowed;transform:none !important;}

/* Feature chips */
.feat-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem;}
@media(max-width:600px){.feat-row{grid-template-columns:1fr;}}
.feat-chip{background:rgba(255,255,255,.5);border:1px solid var(--border);
  border-radius:1rem;padding:.9rem 1rem;display:flex;flex-direction:column;gap:.4rem;}
.feat-chip svg{width:15px;height:15px;color:var(--muted);}
.feat-chip-title{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);}
.feat-chip-desc{font-size:.72rem;color:var(--muted);line-height:1.4;}

/* Identity section */
.identity{background:var(--dark);padding:3.5rem 1.5rem;border-top:1px solid rgba(255,255,255,.05);}
.identity-inner{max-width:1320px;margin:0 auto;}
.identity-hdr{border-bottom:1px solid rgba(255,255,255,.08);padding-bottom:1.25rem;margin-bottom:2.5rem;}
.identity-hdr h2{font-family:var(--mono);font-size:.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.3em;color:#fff;margin-bottom:.3rem;}
.identity-hdr p{font-size:.82rem;color:rgba(255,255,255,.35);}
.identity-grid{display:grid;grid-template-columns:7fr 5fr;gap:2rem;align-items:start;}
@media(max-width:900px){.identity-grid{grid-template-columns:1fr;}}
.biz-card{aspect-ratio:1.75/1;background:#fff;border-radius:1.75rem;padding:2rem 2.5rem;
  box-shadow:0 24px 64px rgba(0,0,0,.35);display:flex;align-items:center;gap:2rem;
  overflow:hidden;position:relative;transition:transform .5s ease;}
.biz-card:hover{transform:scale(1.02);}
.biz-logo-wrap{width:96px;height:96px;background:#fff;border-radius:50%;
  box-shadow:0 4px 16px rgba(0,0,0,.1);border:1px solid rgba(0,0,0,.05);
  flex-shrink:0;display:flex;align-items:center;justify-content:center;padding:.9rem;}
.biz-logo-wrap img{max-width:100%;max-height:100%;object-fit:contain;}
.biz-info{flex:1;min-width:0;}
.biz-name{font-size:1.4rem;font-weight:800;color:var(--text);margin-bottom:.2rem;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.biz-tagline{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:rgba(0,119,190,.7);margin-bottom:1rem;}
.biz-contacts{border-top:1px solid rgba(0,0,0,.06);padding-top:.75rem;}
.biz-contact{display:flex;align-items:center;gap:.4rem;font-size:.72rem;color:rgba(0,0,0,.4);margin:.25rem 0;}
.biz-contact svg{width:11px;height:11px;flex-shrink:0;}
.biz-label{margin-top:.85rem;font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.14em;color:rgba(255,255,255,.2);display:flex;align-items:center;gap:.35rem;}
.biz-label svg{width:12px;height:12px;}
.dig-col{display:flex;flex-direction:column;gap:1.5rem;}
.app-icon-wrap{display:flex;align-items:center;gap:1.5rem;}
.app-icon{width:96px;height:96px;background:#fff;border-radius:1.75rem;
  box-shadow:0 12px 32px rgba(0,0,0,.35);flex-shrink:0;
  display:flex;align-items:center;justify-content:center;padding:1.1rem;transition:transform .4s ease;}
.app-icon:hover{transform:rotate(6deg) scale(1.08);}
.app-icon img{max-width:100%;max-height:100%;object-fit:contain;}
.web-fav{flex:1;background:rgba(255,255,255,.05);border-radius:1rem;
  padding:1rem 1.1rem;border:1px solid rgba(255,255,255,.06);}
.fav-row{display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem;}
.fav-icon{width:28px;height:28px;background:#fff;border-radius:.4rem;
  display:flex;align-items:center;justify-content:center;padding:.3rem;flex-shrink:0;}
.fav-icon img{max-width:100%;max-height:100%;object-fit:contain;}
.fav-bar{height:8px;background:rgba(255,255,255,.08);border-radius:4px;flex:1;}
.fav-lines{display:flex;flex-direction:column;gap:.35rem;}
.fav-line{height:6px;background:rgba(255,255,255,.05);border-radius:3px;}
.fav-line.w-full{width:100%;}
.fav-line.w-2-3{width:66%;}
.fav-label{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.14em;color:rgba(255,255,255,.2);display:flex;align-items:center;gap:.35rem;margin-top:.6rem;}
.fav-label svg{width:11px;height:11px;}
.dark-mock{background:var(--dark2);border-radius:1rem;padding:1.5rem 1.75rem;
  border:1px solid rgba(255,255,255,.06);display:flex;align-items:center;justify-content:center;gap:1.5rem;}
.dark-logo-box{width:68px;height:68px;display:flex;align-items:center;justify-content:center;}
.dark-logo-box img{max-width:100%;max-height:100%;object-fit:contain;filter:brightness(1.1) contrast(1.1);}
.dark-lines{flex:1;display:flex;flex-direction:column;gap:.5rem;}
.dark-line{height:8px;background:rgba(255,255,255,.07);border-radius:4px;}
.dark-tag{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.14em;color:rgba(255,255,255,.2);display:flex;align-items:center;gap:.35rem;
  text-align:center;margin-top:.5rem;}
.dark-tag svg{width:11px;height:11px;}
.dig-label{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
  letter-spacing:.14em;color:rgba(255,255,255,.2);display:flex;align-items:center;gap:.35rem;margin-top:.5rem;}
.dig-label svg{width:12px;height:12px;}
footer{max-width:1320px;margin:0 auto;padding:2rem 1.5rem;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;
  opacity:.4;border-top:1px solid var(--border);}
.footer-brand{display:flex;align-items:center;gap:.4rem;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;}
.footer-brand svg{width:15px;height:15px;}
.footer-links{display:flex;gap:1.5rem;}
.footer-links span{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.12em;}

/* Gallery Section */
.gallery{max-width:1320px;margin:3rem auto;padding:0 1.5rem;}
.gallery-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;border-bottom:1px solid var(--border);padding-bottom:.75rem;}
.gallery-hdr h2{font-family:var(--mono);font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.25em;color:var(--text);}
.gallery-grid{display:grid;grid-template-columns:repeat(auto-fill, minmax(180px, 1fr));gap:1.5rem;}
.gallery-item{background:var(--surface);border:1px solid var(--border);border-radius:1rem;overflow:hidden;transition:all .2s;cursor:pointer;display:flex;flex-direction:column;}
.gallery-item:hover{transform:translateY(-4px);box-shadow:0 12px 24px rgba(0,0,0,.08);border-color:var(--text);}
.gallery-img-wrap{aspect-ratio:1/1;background:var(--surface2);display:flex;align-items:center;justify-content:center;padding:1rem;}
.gallery-img-wrap img{max-width:100%;max-height:100%;object-fit:contain;filter:drop-shadow(0 4px 8px rgba(0,0,0,.08));}
.gallery-info{padding:.75rem;border-top:1px solid var(--border);}
.gallery-name{font-size:.75rem;font-weight:700;color:var(--text);margin-bottom:.15rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.gallery-meta{font-family:var(--mono);font-size:.55rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);display:flex;justify-content:space-between;}
"""

# ---------- HTML body (plain string) -----------------------------------------
HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"/>
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>

<header class="hdr">
  <div class="hdr-brand">
    <div class="hdr-icon"><i data-lucide="sparkles"></i></div>
    <h1>LogoForge AI</h1>
  </div>
  <span class="hdr-pill">v2.1 // Production</span>
</header>

<main class="main">
  <!-- LEFT panel -->
  <div class="panel" id="panel">

    <!-- Brand identity -->
    <div>
      <div class="label"><i data-lucide="type"></i> Brand Identity</div>
      <input type="text" id="brandName" placeholder="Enter Brand Name" autocomplete="off"/>
      <textarea id="brandDesc" rows="3" style="margin-top:.6rem" placeholder="Describe your brand, industry, or vision..."></textarea>
    </div>

    <!-- Advanced guidelines -->
    <div>
      <button class="adv-toggle" id="advToggle" onclick="toggleAdv()">
        <span style="display:flex;align-items:center;gap:.4rem">
          <i data-lucide="target" style="width:13px;height:13px"></i>
          Advanced Guidelines
        </span>
        <i data-lucide="chevron-down" class="chevron"></i>
      </button>
      <div class="adv-body" id="advBody">
        <div class="adv-inner">
          <div>
            <div class="field-label"><i data-lucide="quote"></i> Tagline</div>
            <input type="text" id="tagline" placeholder="e.g. Innovation at Speed"/>
          </div>
          <div>
            <div class="field-label"><i data-lucide="type"></i> Typography Preference</div>
            <input type="text" id="typography" placeholder="e.g. Modern Sans-Serif, Bold Serif"/>
          </div>
          <div class="row2">
            <div>
              <div class="field-label"><i data-lucide="check-circle-2"></i> Include</div>
              <input type="text" id="elemInclude" placeholder="e.g. Gear, Leaf"/>
            </div>
            <div>
              <div class="field-label"><i data-lucide="ban"></i> Avoid</div>
              <input type="text" id="elemAvoid" placeholder="e.g. Animals, Circles"/>
            </div>
          </div>
          <div>
            <div class="field-label"><i data-lucide="briefcase"></i> Brand Mission</div>
            <textarea id="mission" rows="2" placeholder="What is the core purpose of your brand?"></textarea>
          </div>
        </div>
      </div>
    </div>

    <!-- Generator -->
    <div>
      <div class="label"><i data-lucide="cpu"></i> AI Generator</div>
      <div class="btn-grid cols2" id="genGrid">
        <button class="chip active" id="btn-gen-dalle" onclick="selectGenerator('dalle-3',this)">&#127912; DALL-E 3</button>
        <button class="chip"        id="btn-gen-gemini" onclick="selectGenerator('gemini',this)">&#10024; Gemini</button>
      </div>
      <div id="genHint" class="gen-hint">
        &#128161; <strong>DALL-E 3:</strong> Premium HD quality &middot; ~15 s &middot; best for professional logos
      </div>
    </div>

    <!-- Visual Style -->
    <div>
      <div class="label"><i data-lucide="layers"></i> Visual Style</div>
      <div class="btn-grid cols2" id="styleGrid">
        <button class="chip active" onclick="selectStyle('minimalist',this)">Minimalist</button>
        <button class="chip"        onclick="selectStyle('tech',this)">Tech / Modern</button>
        <button class="chip"        onclick="selectStyle('vintage',this)">Vintage</button>
        <button class="chip"        onclick="selectStyle('abstract',this)">Abstract</button>
        <button class="chip"        onclick="selectStyle('mascot',this)">Mascot</button>
        <button class="chip"        onclick="selectStyle('luxury',this)">Luxury</button>
      </div>
    </div>

    <!-- Color Palette -->
    <div>
      <div class="label"><i data-lucide="palette"></i> Color Palette</div>
      <div class="btn-grid cols3" id="palGrid">
        <button class="pal-chip active" onclick="selectPalette('monochrome',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#000"></div>
            <div class="pal-dot" style="background:#FFF;border:1px solid #ccc"></div>
          </div>
          <span class="pal-name">Mono</span>
        </button>
        <button class="pal-chip" onclick="selectPalette('ocean',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#0077BE"></div>
            <div class="pal-dot" style="background:#00A3E0"></div>
            <div class="pal-dot" style="background:#E0F2F7"></div>
          </div>
          <span class="pal-name">Ocean</span>
        </button>
        <button class="pal-chip" onclick="selectPalette('sunset',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#FF4E50"></div>
            <div class="pal-dot" style="background:#FC913A"></div>
            <div class="pal-dot" style="background:#F9D423"></div>
          </div>
          <span class="pal-name">Sunset</span>
        </button>
        <button class="pal-chip" onclick="selectPalette('forest',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#1B4332"></div>
            <div class="pal-dot" style="background:#2D6A4F"></div>
            <div class="pal-dot" style="background:#74C69D"></div>
          </div>
          <span class="pal-name">Forest</span>
        </button>
        <button class="pal-chip" onclick="selectPalette('royal',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#4B0082"></div>
            <div class="pal-dot" style="background:#FFD700"></div>
            <div class="pal-dot" style="background:#FFF;border:1px solid #ccc"></div>
          </div>
          <span class="pal-name">Royal</span>
        </button>
        <button class="pal-chip" onclick="selectPalette('neon',this)">
          <div class="pal-dots">
            <div class="pal-dot" style="background:#39FF14"></div>
            <div class="pal-dot" style="background:#FF00FF"></div>
            <div class="pal-dot" style="background:#00FFFF"></div>
          </div>
          <span class="pal-name">Neon</span>
        </button>
      </div>
    </div>

    <!-- Generate row -->
    <div style="display:flex;flex-direction:column;gap:.75rem">
      <div class="gen-row">
        <button class="gen-btn" id="genBtn" onclick="generateLogo(false)">
          <i data-lucide="sparkles" style="width:20px;height:20px"></i>
          Generate Logo
        </button>
        <button class="cancel-btn" id="cancelBtn" onclick="cancelGeneration()">&#10005; Cancel</button>
      </div>
      <div class="progress-wrap" id="progressWrap">
        <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
        <div class="progress-label" id="progressLabel">Initialising...</div>
      </div>
    </div>

    <div id="errBox" class="err" style="display:none"></div>

  </div><!-- /panel -->

  <!-- RIGHT: preview -->
  <div class="preview-wrap">
    <div class="canvas-card">
      <div class="canvas-top">
        <div class="pulse-dot"></div>
        <span class="canvas-label">Live Preview Canvas</span>
      </div>
      <div class="canvas-body" id="canvasBody">
        <div id="placeholder" class="placeholder">
          <i data-lucide="image" style="width:64px;height:64px;stroke-width:1"></i>
          <p>Awaiting Generation Parameters</p>
        </div>
      </div>
      <div class="var-badge" id="varBadge" style="display:none"></div>
      <div class="canvas-actions" id="canvasActions" style="display:none">
        <button class="act-btn act-primary" id="dlBtn" onclick="downloadLogo()">
          <i data-lucide="download"></i> Download PNG
        </button>
        <button class="act-btn act-secondary" id="regenBtn" onclick="generateLogo(true)">
          <i data-lucide="refresh-cw"></i> Regenerate
        </button>
      </div>
    </div>

    <div class="feat-row">
      <div class="feat-chip">
        <i data-lucide="check-circle-2"></i>
        <div class="feat-chip-title">Vector Ready</div>
        <div class="feat-chip-desc">High-contrast designs optimised for SVG conversion.</div>
      </div>
      <div class="feat-chip">
        <i data-lucide="briefcase"></i>
        <div class="feat-chip-title">Commercial Use</div>
        <div class="feat-chip-desc">AI-generated assets for your projects and applications.</div>
      </div>
      <div class="feat-chip">
        <i data-lucide="sparkles"></i>
        <div class="feat-chip-title">Neural Design</div>
        <div class="feat-chip-desc">Powered by DALL-E 3 and Gemini image synthesis.</div>
      </div>
    </div>
  </div>

</main>

<!-- Identity preview -->
<section class="identity" id="identitySection" style="display:none">
  <div class="identity-inner">
    <div class="identity-hdr">
      <h2>Visual Identity Preview</h2>
      <p>Conceptual previews of how your logo would appear on physical and digital assets.</p>
    </div>
    <div class="identity-grid">
      <div>
        <div class="biz-card">
          <div class="biz-logo-wrap"><img id="bizLogoImg" src="" alt="Logo"/></div>
          <div class="biz-info">
            <div class="biz-name" id="bizName">Brand Name</div>
            <div class="biz-tagline" id="bizTagline">Global Solutions</div>
            <div class="biz-contacts">
              <div class="biz-contact"><i data-lucide="mail"></i> contact@example.com</div>
              <div class="biz-contact"><i data-lucide="globe"></i><span id="bizUrl">www.example.com</span></div>
              <div class="biz-contact"><i data-lucide="map-pin"></i> 123 Innovation Drive, Tech City</div>
            </div>
          </div>
        </div>
        <div class="biz-label"><i data-lucide="credit-card"></i> Physical Asset // Business Card Mockup</div>
      </div>
      <div class="dig-col">
        <div class="app-icon-wrap">
          <div>
            <div class="app-icon"><img id="appIconImg" src="" alt="App icon"/></div>
            <div class="dig-label" style="justify-content:center"><i data-lucide="smartphone"></i> iOS Icon</div>
          </div>
          <div class="web-fav">
            <div class="fav-row">
              <div class="fav-icon"><img id="favIconImg" src="" alt="favicon"/></div>
              <div class="fav-bar"></div>
            </div>
            <div class="fav-lines">
              <div class="fav-line w-full"></div>
              <div class="fav-line w-2-3"></div>
            </div>
            <div class="fav-label"><i data-lucide="globe"></i> Web Favicon &amp; Header</div>
          </div>
        </div>
        <div class="dark-mock">
          <div class="dark-logo-box"><img id="darkLogoImg" src="" alt="dark logo"/></div>
          <div class="dark-lines">
            <div class="dark-line" style="width:100%"></div>
            <div class="dark-line" style="width:75%"></div>
            <div class="dark-line" style="width:50%"></div>
          </div>
        </div>
        <div class="dark-tag"><i data-lucide="monitor"></i> Dark UI Adaptability</div>
      </div>
    </div>
  </div>
</section>

<!-- Gallery Section -->
<section class="gallery" id="gallerySection">
  <div class="gallery-hdr">
    <h2>Recent Generations</h2>
    <div style="display:flex;gap:.5rem">
        <button class="adv-toggle" onclick="fetchHistory()" style="font-size:.55rem"><i data-lucide="refresh-cw" style="width:12px;height:12px"></i> Refresh</button>
    </div>
  </div>
  <div class="gallery-grid" id="galleryGrid">
    <!-- Populated by JS -->
    <div style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--muted);font-family:var(--mono);font-size:.65rem;text-transform:uppercase;letter-spacing:.15em;">
        Loading History...
    </div>
  </div>
</section>

<footer>
  <div class="footer-brand"><i data-lucide="sparkles"></i> LogoForge AI System</div>
  <div class="footer-links">
    <span>Privacy Protocol</span>
    <span>Usage Terms</span>
    <span id="apiStatusFooter">API: Checking...</span>
  </div>
</footer>
"""

# ---------- JS (plain string — no Python interpolation except API_BASE_URL) ---
# We use a regular string and only .replace() the one Python variable needed.
JS_TEMPLATE = r"""
const API = "__API_URL__";

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  generator:      "dalle-3",
  style:          "minimalist",
  palette:        "monochrome",
  logoSrc:        null,
  generating:     false,
  variationIndex: 0,
  abortCtrl:      null,
};

// Variation directions rotated on each Regenerate click
const VARIATION_HINTS = [
  "",
  "Try a completely different icon concept and layout. Reimagine the composition from scratch.",
  "Bold typographic approach — make the brand name the centrepiece with a minimal icon accent.",
  "Strong geometric shapes, sharp angles and clean negative space.",
  "Organic, flowing curves and softer rounded elements for a friendly feel.",
  "Abstract, highly symbolic representation — less literal, more evocative.",
  "Maximise negative space; ultra-minimalist, almost invisible simplicity.",
  "Dynamic, energetic diagonal composition with strong directional movement.",
];

// ── Boot ──────────────────────────────────────────────────────────────────────
lucide.createIcons();

(async () => {
  try {
    const r = await fetch(API + "/api/health", { signal: AbortSignal.timeout(4000) });
    const d = await r.json();
    document.getElementById("apiStatusFooter").textContent =
      "API: " + (d.status === "ok" ? "Online \u2705" : "Degraded \u26a0\ufe0f");
  } catch {
    document.getElementById("apiStatusFooter").textContent = "API: Offline \u274c";
  }
  fetchHistory();
})();

// ── History / Gallery ──────────────────────────────────────────────────────────
async function fetchHistory() {
  try {
    const r = await fetch(API + "/api/history?limit=12");
    if (r.ok) {
      const data = await r.json();
      renderHistory(data);
    }
  } catch (e) {
    console.error("Failed to fetch history:", e);
  }
}

function renderHistory(items) {
  const grid = document.getElementById("galleryGrid");
  if (!items || items.length === 0) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--muted);font-family:var(--mono);font-size:.65rem;">No history found yet</div>';
    return;
  }

  grid.innerHTML = items.map(item => {
    const src = item.image_url.startsWith("http") ? item.image_url : API + "/static/" + item.image_url.split("\\").join("/");
    return `
      <div class="gallery-item" onclick="loadFromHistory('${item.brand_name}', '${src}')">
        <div class="gallery-img-wrap">
          <img src="${src}" alt="${item.brand_name}"/>
        </div>
        <div class="gallery-info">
          <div class="gallery-name">${item.brand_name}</div>
          <div class="gallery-meta">
            <span>${item.generator}</span>
            <span>${new Date(item.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
  lucide.createIcons();
}

function loadFromHistory(brand, src) {
  document.getElementById("brandName").value = brand;
  state.logoSrc = src;
  setCanvasLogo(src, 0);
  showIdentity(brand, "", src);
}

// ── Selection helpers ──────────────────────────────────────────────────────────
function clearActive(gridId) {
  document.querySelectorAll("#" + gridId + " button").forEach(b => b.classList.remove("active"));
}

function selectGenerator(val, btn) {
  state.generator = val;
  clearActive("genGrid");
  btn.classList.add("active");
  const hints = {
    "dalle-3": "\ud83d\udca1 <strong>DALL-E 3:</strong> Premium HD quality &middot; ~15 s &middot; best for professional logos",
    "gemini":  "\u26a1 <strong>Gemini:</strong> Fast generation &middot; ~12 s &middot; great for rapid iterations",
  };
  document.getElementById("genHint").innerHTML = hints[val] || "";
}

function selectStyle(val, btn) {
  state.style = val;
  clearActive("styleGrid");
  btn.classList.add("active");
}

function selectPalette(val, btn) {
  state.palette = val;
  clearActive("palGrid");
  btn.classList.add("active");
}

// ── Advanced toggle ────────────────────────────────────────────────────────────
function toggleAdv() {
  const body = document.getElementById("advBody");
  const btn  = document.getElementById("advToggle");
  const willOpen = !body.classList.contains("open");
  if (willOpen) {
    body.style.overflow = "hidden";
    body.classList.add("open");
    btn.classList.add("open");
    body.addEventListener("transitionend", () => {
      if (body.classList.contains("open")) body.style.overflow = "visible";
    }, { once: true });
  } else {
    body.style.overflow = "hidden";
    body.classList.remove("open");
    btn.classList.remove("open");
  }
}

// ── Progress bar ───────────────────────────────────────────────────────────────
let _progressTimer = null;

function startProgress(generator) {
  const fill  = document.getElementById("progressFill");
  const label = document.getElementById("progressLabel");
  const wrap  = document.getElementById("progressWrap");
  wrap.classList.add("show");
  fill.style.background = "";
  fill.style.width = "0%";

  const steps = generator === "dalle-3"
    ? [[0,5,"Connecting to DALL-E 3..."],[2000,30,"Generating image..."],[8000,65,"Processing..."],[14000,85,"Saving locally..."]]
    : [[0,5,"Connecting to Gemini..."],[1500,30,"Generating image..."],[6000,70,"Processing output..."],[10000,88,"Saving file..."]];

  let i = 0;
  function tick() {
    if (i >= steps.length) return;
    fill.style.width = steps[i][1] + "%";
    label.textContent = steps[i][2];
    i++;
    if (i < steps.length) _progressTimer = setTimeout(tick, steps[i][0] - steps[i-1][0]);
  }
  tick();
}

function finishProgress(success) {
  clearTimeout(_progressTimer);
  const fill  = document.getElementById("progressFill");
  const label = document.getElementById("progressLabel");
  const wrap  = document.getElementById("progressWrap");
  fill.style.width = "100%";
  if (success) {
    label.textContent = "Done \u2713";
  } else {
    fill.style.background = "#ff4d4f";
    label.textContent = "Failed";
  }
  setTimeout(() => {
    wrap.classList.remove("show");
    fill.style.background = "";
    fill.style.width = "0%";
  }, 1400);
}

// ── Canvas helpers ─────────────────────────────────────────────────────────────
function setCanvasLoading() {
  document.getElementById("canvasBody").innerHTML =
    '<div class="loading-state">' +
    '<div class="loader-ring"></div>' +
    '<p>Synthesising visual assets...</p>' +
    '<small>This may take 10-20 seconds</small>' +
    '</div>';
  document.getElementById("canvasActions").style.display = "none";
  document.getElementById("varBadge").style.display = "none";
}

function setCanvasLogo(src, variationIndex) {
  document.getElementById("canvasBody").innerHTML =
    '<img class="logo-img" src="' + src + '" alt="Generated logo"/>';
  document.getElementById("canvasActions").style.display = "flex";
  const badge = document.getElementById("varBadge");
  if (variationIndex > 0) {
    badge.textContent = "Variation " + variationIndex;
    badge.style.display = "block";
  } else {
    badge.style.display = "none";
  }
}

function setCanvasError() {
  document.getElementById("canvasBody").innerHTML =
    '<div class="placeholder">' +
    '<i data-lucide="alert-circle" style="width:48px;height:48px;stroke-width:1;color:rgba(255,68,68,.4)"></i>' +
    '<p>Generation failed &mdash; see error below</p>' +
    '</div>';
  lucide.createIcons();
  document.getElementById("canvasActions").style.display = "none";
}

// ── Cancel ─────────────────────────────────────────────────────────────────────
function cancelGeneration() {
  if (state.abortCtrl) {
    state.abortCtrl.abort();
    state.abortCtrl = null;
  }
}

// ── Main generate ──────────────────────────────────────────────────────────────
async function generateLogo(isRegen) {
  if (state.generating) return;

  const brand = document.getElementById("brandName").value.trim();
  const desc  = document.getElementById("brandDesc").value.trim();
  if (!brand && !desc) { showErr("Please enter a brand name or description."); return; }
  clearErr();

  // Update variation index
  if (isRegen) {
    state.variationIndex = (state.variationIndex + 1) % VARIATION_HINTS.length;
  } else {
    state.variationIndex = 0;
  }

  const variationHint = VARIATION_HINTS[state.variationIndex];

  state.generating = true;
  setCanvasLoading();
  startProgress(state.generator);

  // Show cancel, disable other buttons
  document.getElementById("cancelBtn").style.display = "block";
  const dlBtn    = document.getElementById("dlBtn");
  const regenBtn = document.getElementById("regenBtn");
  if (dlBtn)    dlBtn.disabled = true;
  if (regenBtn) regenBtn.disabled = true;

  const genBtn = document.getElementById("genBtn");
  genBtn.disabled = true;
  genBtn.innerHTML =
    '<svg class="spin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    '<path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> ' +
    (isRegen ? "Generating variation..." : "Forging Logo...");

  // AbortController + 75 s hard backstop
  const ctrl = new AbortController();
  state.abortCtrl = ctrl;
  const hardTimeout = setTimeout(() => ctrl.abort(), 75000);

  // Build payload — always reads live UI state
  const payload = {
    text:                brand || "Brand",
    description:         desc,
    style:               state.style,
    palette:             state.palette,
    generator:           state.generator,
    tagline:             document.getElementById("tagline").value.trim(),
    typography:          document.getElementById("typography").value.trim(),
    elements_to_include: document.getElementById("elemInclude").value.trim(),
    elements_to_avoid:   document.getElementById("elemAvoid").value.trim(),
    brand_mission:       document.getElementById("mission").value.trim(),
    variation_hint:      variationHint,
    variation_index:     state.variationIndex,
  };

  try {
    const r = await fetch(API + "/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
      signal:  ctrl.signal,
    });

    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      throw new Error(d.detail || "HTTP " + r.status);
    }

    const { job_id } = await r.json();
    console.log("[JS] Enqueued job:", job_id);

    // --- Polling loop ---
    let jobData = null;
    let attempts = 0;
    while (attempts < 60) { // Max 60 attempts (~60-120 seconds)
      if (ctrl.signal.aborted) throw new Error("AbortError");
      
      const res = await fetch(API + "/api/jobs/" + job_id, { signal: ctrl.signal });
      if (!res.ok) throw new Error("Failed to check job status");
      
      const statusData = await res.json();
      console.log("[JS] Job status:", statusData.status);
      
      if (statusData.status === "completed") {
        jobData = statusData.result;
        break;
      } else if (statusData.status === "failed") {
        throw new Error(statusData.error || "Generation task failed");
      }
      
      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1500)); // Poll every 1.5s
    }

    if (!jobData) throw new Error("Generation timed out");

    clearTimeout(hardTimeout);

    const raw    = jobData.result[0];
    // Both generators return a relative path like generated_logos/dalle/... or generated_logos/gemini/...
    // Full https:// URLs (fallback) are used as-is.
    const imgSrc = raw.startsWith("http") ? raw : API + "/static/" + raw.split("\\").join("/");

    state.logoSrc = imgSrc;
    finishProgress(true);
    setCanvasLogo(imgSrc, state.variationIndex);
    showIdentity(brand, payload.tagline, imgSrc);
    fetchHistory(); // Refresh history after new generation

  } catch (e) {
    clearTimeout(hardTimeout);
    finishProgress(false);
    if (e.name === "AbortError" || e.message === "AbortError") {
      showErr("Generation cancelled.");
    } else {
      showErr(e.message || "Unexpected error");
    }
    setCanvasError();
  } finally {
    state.generating = false;
    state.abortCtrl  = null;
    document.getElementById("cancelBtn").style.display = "none";
    genBtn.disabled = false;
    genBtn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>' +
      '</svg> Generate Logo';
    if (dlBtn)    dlBtn.disabled = false;
    if (regenBtn) regenBtn.disabled = false;
  }
}

// ── Download ───────────────────────────────────────────────────────────────────
async function downloadLogo() {
  if (!state.logoSrc) return;
  try {
    const r    = await fetch(state.logoSrc);
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = (document.getElementById("brandName").value.trim() || "logo")
                   .toLowerCase().replace(/\s+/g, "-") + "-logo.png";
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    window.open(state.logoSrc, "_blank");
  }
}

// ── Identity preview ───────────────────────────────────────────────────────────
function showIdentity(brand, tagline, imgSrc) {
  document.getElementById("identitySection").style.display = "block";
  document.getElementById("bizName").textContent    = brand || "Brand Name";
  document.getElementById("bizTagline").textContent = tagline || "Global Solutions";
  document.getElementById("bizUrl").textContent     =
    "www." + (brand || "example").toLowerCase().replace(/\s+/g, "") + ".com";
  ["bizLogoImg","appIconImg","favIconImg","darkLogoImg"].forEach(id => {
    document.getElementById(id).src = imgSrc;
  });
  document.getElementById("identitySection").scrollIntoView({ behavior:"smooth", block:"start" });
  lucide.createIcons();
}

// ── Error helpers ──────────────────────────────────────────────────────────────
function showErr(msg) {
  const el = document.getElementById("errBox");
  el.textContent = msg;
  el.style.display = "block";
}
function clearErr() {
  document.getElementById("errBox").style.display = "none";
}
"""

# ── Assemble final HTML — only the API URL needs Python interpolation ──────────
JS = JS_TEMPLATE.replace("__API_URL__", API_BASE_URL)

COMPONENT_HTML = (
    "<!DOCTYPE html><html lang='en'><head>"
    "<meta charset='UTF-8'/>"
    "<meta name='viewport' content='width=device-width,initial-scale=1.0'/>"
    "<style>" + CSS + "</style>"
    "</head><body>"
    + HTML +
    "<script>" + JS + "</script>"
    "</body></html>"
)

# ── Render ─────────────────────────────────────────────────────────────────────
st.components.v1.html(COMPONENT_HTML, height=1400, scrolling=True)