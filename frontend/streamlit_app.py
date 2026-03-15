"""
LogoForge AI - Streamlit Frontend
Professional logo generation with DALL-E 3 and Gemini support
"""

import streamlit as st
import requests
from PIL import Image
from datetime import datetime
import io
import base64

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="LogoForge AI - Professional Logo Generator",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ADVANCED STYLING
# ============================================================================

st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background: #E6E6E6 !important;
        min-height: 100vh;
    }
    
    [data-testid="stMain"] {
        padding: 0 !important;
        background: #E6E6E6 !important;
    }
    
    .main {
        background: #E6E6E6 !important;
        padding: 3rem 1.5rem !important;
        max-width: 1280px !important;
        margin: 0 auto !important;
    }
    
    [data-testid="stAppViewContainer"] > section {
        max-width: 1280px !important;
        margin: 0 auto !important;
        padding: 0 1.5rem !important;
    }
    
    /* Overall text color */
    body, p, label, span {
        color: #151619 !important;
    }
    
    /* Header Styling */
    .header-container {
        text-align: center;
        margin-bottom: 3rem;
        padding: 1.5rem 1.5rem;
        height: auto;
        min-height: 72px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: linear-gradient(135deg, #FF4444 0%, #FF6666 100%);
        border-radius: 1.5rem;
        color: white;
        box-shadow: 0 12px 35px rgba(255, 68, 68, 0.35);
        max-width: 1280px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .header-container h1 {
        font-size: 2.5rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    
    .header-container p {
        font-size: 1.15rem;
        opacity: 0.95;
        font-weight: 400;
        color: #ffffff !important;
        margin: 0;
    }
    
    /* Form Sections */
    .form-section {
        background: #F5F5F5;
        padding: 2rem;
        border-radius: 1.2rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #D0D0D0;
        max-width: 100%;
    }
    
    .form-section h3 {
        color: #151619 !important;
        font-size: 1.35rem;
        margin-bottom: 1.5rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: linear-gradient(135deg, #FF4444 0%, #FF6666 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Labels and text */
    .stTextInput label,
    .stTextArea label,
    .stSelectbox label,
    .stNumberInput label {
        color: #151619 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Input Fields - Match Tailwind px-3 & py-3 (12px) */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        border: 2px solid #C0C0C0 !important;
        border-radius: 0.75rem !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        color: #151619 !important;
        background-color: #FFFFFF !important;
    }
    
    .stSelectbox > div > div > select {
        border: 2px solid #C0C0C0 !important;
        border-radius: 0.75rem !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        color: #151619 !important;
        background-color: #FFFFFF !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder,
    .stNumberInput > div > div > input::placeholder {
        color: #808080 !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #FF4444 !important;
        box-shadow: 0 0 0 4px rgba(255, 68, 68, 0.2) !important;
        color: #151619 !important;
    }
    
    /* Buttons - Match Tailwind py-4 (16px) */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #FF4444 0%, #FF6666 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border-radius: 0.75rem !important;
        padding: 1rem 2rem !important;
        min-height: 60px !important;
        border: none !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 6px 20px rgba(255, 68, 68, 0.35) !important;
        letter-spacing: 0.3px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 30px rgba(255, 68, 68, 0.45) !important;
    }
    
    .stButton > button:active {
        transform: translateY(-1px) !important;
    }
    
    /* Secondary Buttons (Style/Palette Selectors) */
    .stButton > button[kind="secondary"] {
        min-height: 48px !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Tabs - Make them visible */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        border-bottom: 3px solid #C0C0C0;
        padding: 0.5rem 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 1.5rem !important;
        border-radius: 0.75rem 0.75rem 0 0;
        font-weight: 700 !important;
        color: #666666 !important;
        font-size: 1rem !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #FF4444 !important;
        background: linear-gradient(180deg, rgba(255, 68, 68, 0.12) 0%, transparent 100%) !important;
        border-bottom: 3px solid #FF4444 !important;
    }
    
    /* Preview Container - Main preview card (rounded-3xl = 1.5rem) */
    .preview-container {
        background: #0A0B0D;
        border-radius: 1.5rem;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        border: 1px solid #1A1A1C;
        aspect-ratio: 1 / 1;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    
    .preview-container h3 {
        color: #FFFFFF !important;
        margin-bottom: 1.5rem;
        font-weight: 700;
        font-size: 1.25rem;
    }
    
    /* Section headings */
    h1, h2, h3, h4, h5, h6 {
        color: #151619 !important;
        font-weight: 700;
    }
    
    h1 { font-weight: 900; letter-spacing: -0.5px; }
    h2 { font-weight: 800; letter-spacing: -0.3px; }
    h3 { font-weight: 700; letter-spacing: -0.2px; }
    h4 { font-weight: 600; }
    
    /* Details card */
    .details-card {
        background: linear-gradient(135deg, #F5F5F5 0%, #E8E8E8 100%);
        border-left: 4px solid #FF4444;
        padding: 1.5rem;
        border-radius: 0.85rem;
        margin: 1rem 0;
    }
    
    .details-card p {
        margin: 0.75rem 0;
        font-weight: 500;
        color: #151619 !important;
    }
    
    /* Preview Canvas Inside Container */
    .preview-canvas {
        background: linear-gradient(135deg, #151619 0%, #0A0B0D 100%);
        border: 2px dashed #404040;
        border-radius: 1rem;
        padding: 2rem;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
    }
    
    .preview-canvas img {
        max-height: 90%;
        max-width: 90%;
        object-fit: contain;
        border-radius: 1rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    }
    
    /* Badges */
    .generator-badge {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        border-radius: 0.6rem;
        font-size: 0.85rem;
        font-weight: 700;
        margin: 0.5rem 0;
        text-align: center;
        width: 100%;
    }
    
    .dalle-badge {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
    }
    
    .gemini-badge {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        box-shadow: 0 6px 20px rgba(79, 172, 254, 0.4);
    }
    
    /* Mockup Cards - Business Card is 1.75:1 aspect ratio */
    .mockup-business-card {
        aspect-ratio: 1.75 / 1;
        background: white;
        border-radius: 2rem;
        padding: 2rem 3rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 2rem;
        border: 1px solid #f0f0f0;
    }
    
    .mockup-logo-container {
        width: 128px;
        height: 128px;
        flex-shrink: 0;
        background: white;
        border-radius: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        border: 1px solid #f0f0f0;
    }
    
    .mockup-logo-container img {
        max-width: 90%;
        max-height: 90%;
        object-fit: contain;
    }
    
    /* App Icon Mockup - 128px square with 40px radius */
    .mockup-app-icon {
        width: 128px;
        height: 128px;
        background: white;
        border-radius: 2.5rem;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem;
    }
    
    .mockup-app-icon img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }
    
    /* Dark Mode Mockup */
    .mockup-dark-mode {
        background: #1A1B1F;
        border-radius: 1rem;
        padding: 1.5rem;
        border: 1px solid #404040;
        text-align: center;
    }
    
    .mockup-dark-logo {
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.5rem;
    }
    
    .mockup-dark-logo img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        filter: brightness(1.1) contrast(1.1);
    }
    
    /* Containers */
    [data-testid="stContainer"] {
        padding: 0 !important;
        max-width: 100%;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #F5F5F5 !important;
        border: 2px solid #C0C0C0 !important;
        border-radius: 0.75rem !important;
        padding: 1rem !important;
        color: #151619 !important;
        font-weight: 600 !important;
    }
    
    /* Info Messages - Better padding */
    .stInfo, .stSuccess, .stError, .stAlert, .stWarning {
        padding: 1rem !important;
        border-radius: 0.75rem !important;
    }
    
    .stInfo {
        background-color: #e6f7ff !important;
        border-left: 4px solid #1890ff !important;
        color: #003a8c !important;
    }
    
    .stSuccess {
        background-color: #f6ffed !important;
        border-left: 4px solid #52c41a !important;
        color: #274406 !important;
    }
    
    .stError {
        background-color: #fff1f0 !important;
        border-left: 4px solid #ff4d4f !important;
        color: #5c1114 !important;
    }
    
    /* Gallery Items */
    .gallery-item {
        background: #F5F5F5;
        border: 1px solid #D0D0D0;
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .gallery-item:hover {
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }
    
    /* Divider */
    .divider {
        border-top: 2px solid #C0C0C0;
        margin: 3rem 0;
    }
    
    /* Text helpers */
    p, span, label, div {
        color: #151619 !important;
    }
    
    /* Markdown text */
    .markdown-text {
        color: #1a202c !important;
    }
    
    /* API Status */
    .api-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        border-radius: 0.75rem;
        font-weight: 700;
        font-size: 0.9rem;
    }
    
    .api-status.connected {
        background-color: #C8E6C9;
        color: #1B5E20;
    }
    
    .api-status.disconnected {
        background-color: #FFCDD2;
        color: #B71C1C;
    }
    
    /* Code Block */
    .stCode {
        border-radius: 0.75rem !important;
        background-color: #2d3748 !important;
    }
    
    /* Ensure all markdown is readable */
    .stMarkdown {
        color: #1a202c !important;
    }
    
    /* Style/Palette Button Selected State */
    .stButton button:focus {
        background: linear-gradient(135deg, #FF4444 0%, #FF6666 100%) !important;
        color: white !important;
        border: none !important;
    }
    
    /* Enhanced Button Styling */
    .stButton button {
        transition: all 0.3s ease !important;
    }
    
    .stButton button:active {
        transform: scale(0.98) !important;
    }
    
    /* Mockup Section Styling */
    .mockup-card {
        background: white;
        border-radius: 1rem;
        padding: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        margin: 1rem 0;
        border: 1px solid #f0f0f0;
    }
    
    .mockup-card img {
        max-width: 100%;
        height: auto;
        border-radius: 0.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Dark mode mockup */
    .dark-mockup {
        background: #1A1B1F;
        border-radius: 1rem;
        border: 1px solid #404040;
        padding: 2rem;
    }
    
    .dark-mockup img {
        filter: brightness(1.1) contrast(1.1);
    }
    
    /* Info message padding */
    .stInfo, .stSuccess, .stError {
        padding: 1rem !important;
    }
    
    /* Enhanced feature cards */
    .feature-card {
        background: linear-gradient(135deg, #F5F5F5 0%, #FFFFFF 100%);
        border: 2px solid #D0D0D0;
        border-left: 4px solid #FF4444;
        border-radius: 0.85rem;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        box-shadow: 0 4px 15px rgba(255, 68, 68, 0.1);
        transform: translateY(-4px);
    }
    
    /* Tab content padding */
    [data-testid="stTabBar"] {
        padding: 0 !important;
    }
    
    /* Professional text hierarchy */
    h1 { font-weight: 900; letter-spacing: -0.5px; }
    h2 { font-weight: 800; letter-spacing: -0.3px; }
    h3 { font-weight: 700; letter-spacing: -0.2px; }
    h4 { font-weight: 600; }
    
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:5050")
except:
    API_BASE_URL = "http://localhost:5050"


LOGO_STYLES = {
    'minimalist': '🟢 Minimalist',
    'tech': '🔮 Tech/Modern',
    'vintage': '🏛️ Vintage',
    'abstract': '🎨 Abstract',
    'mascot': '🎭 Mascot',
    'luxury': '👑 Luxury'
}

COLOR_PALETTES = {
    'monochrome': '⚫ Monochrome',
    'ocean': '🌊 Ocean',
    'sunset': '🌅 Sunset',
    'forest': '🌲 Forest',
    'royal': '👑 Royal',
    'neon': '⚡ Neon'
}

GENERATORS = {
    'dalle-3': '🎨 DALL-E 3',
    'gemini': '✨ Gemini'
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "current_logo" not in st.session_state:
    st.session_state.current_logo = None
if "generation_history" not in st.session_state:
    st.session_state.generation_history = []
if "show_advanced" not in st.session_state:
    st.session_state.show_advanced = False

# ============================================================================
# API FUNCTIONS
# ============================================================================


def check_api_health():
    """Check if backend API is available and clients are ready"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        return False, {"error": "API returned error"}
    except Exception as e:
        return False, {"error": str(e)}


def generate_logo(request_data):
    """Generate logo via backend API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/generate",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json().get("detail", "Generation failed")
    except requests.exceptions.Timeout:
        return False, "Request timed out. Try again."
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to API at {API_BASE_URL}"
    except Exception as e:
        return False, str(e)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def display_logo_result(logo_data):
    """Display generated logo with download options and comprehensive mockups"""
    
    logo_result = logo_data["result"][0]
    brand_name = logo_data['brand']
    
    # Main preview section
    st.markdown("### 🖼️ Live Preview Canvas")
    
    preview_col1, preview_col2 = st.columns([2, 1])
    
    with preview_col1:
        st.markdown('<div class="preview-container">', unsafe_allow_html=True)
        
        if logo_data["generator"] == "dalle-3":
            st.image(logo_result, use_column_width=True)
            try:
                response = requests.get(logo_result, timeout=10)
                if response.status_code == 200:
                    st.download_button(
                        label="⬇️ Download PNG",
                        data=response.content,
                        file_name=f"{brand_name.lower().replace(' ', '-')}_logo.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"dl_dalle_{id(logo_data)}"
                    )
            except:
                st.info("Logo generated but download unavailable")
        
        else:
            try:
                img = Image.open(logo_result)
                st.image(img, use_column_width=True)
                
                with open(logo_result, "rb") as f:
                    st.download_button(
                        label="⬇️ Download PNG",
                        data=f.read(),
                        file_name=f"{brand_name.lower().replace(' ', '-')}_logo.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"dl_gemini_{id(logo_data)}"
                    )
            except Exception as e:
                st.error(f"Error loading image: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with preview_col2:
        st.markdown("### 📋 Logo Details")
        
        st.markdown('<div class="details-card">', unsafe_allow_html=True)
        st.markdown(f"**Brand:** {brand_name}")
        st.markdown(f"**Style:** {logo_data['style']}")
        st.markdown(f"**Palette:** {logo_data['palette']}")
        
        # Generator badge
        if logo_data['generator'] == 'dalle-3':
            st.markdown('<div class="generator-badge dalle-badge">🎨 DALL-E 3 (HD Quality)</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<div class="generator-badge gemini-badge">✨ Gemini (Fast)</div>', 
                       unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Regenerate", use_container_width=True, key=f"regen_{id(logo_data)}"):
                st.rerun()
        
        with col_btn2:
            with st.expander("📝 Prompt"):
                st.code(logo_data["prompt"], language="text")
    
    # Visual identity preview section
    st.markdown("---")
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0A0B0D 0%, #1A1B1F 100%);
        border-radius: 1rem;
        padding: 2.5rem;
        border: 1px solid #404040;
        margin: 2rem 0;
    ">
        <h2 style="color: white; margin-bottom: 0.5rem; font-size: 1.5rem;">🎨 Visual Identity Preview</h2>
        <p style="color: #ffffff99; margin: 0; font-size: 0.95rem;">Conceptual previews of how your logo would look on physical and digital assets.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mockup previews
    st.markdown("#### 💼 Business Card Mockup")
    mock_col1, mock_col2 = st.columns([2, 1])
    
    with mock_col1:
        st.markdown(f"""
        <div style="
            background: white;
            border-radius: 2rem;
            padding: 2rem 3rem;
            aspect-ratio: 1.75 / 1;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            display: flex;
            align-items: center;
            gap: 2rem;
            border: 1px solid #f0f0f0;
        ">
            <div style="
                width: 128px;
                height: 128px;
                background: white;
                border-radius: 1rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border: 1px solid #f0f0f0;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                padding: 1rem;
            ">
                <img src="{logo_result}" alt="Logo" style="max-width: 90%; max-height: 90%; object-fit: contain;">
            </div>
            
            <div style="flex: 1;">
                <h3 style="margin: 0 0 0.5rem 0; color: #151619; font-size: 1.5rem; font-weight: 700;">{brand_name}</h3>
                <p style="margin: 0 0 1rem 0; color: #0077BE; font-weight: 600; font-size: 0.85rem; letter-spacing: 0.5px;">GLOBAL SOLUTIONS</p>
                
                <div style="font-size: 0.8rem; color: #666; line-height: 1.6; border-top: 1px solid #e0e0e0; padding-top: 0.8rem;">
                    <p style="margin: 0.3rem 0;">📧 contact@example.com</p>
                    <p style="margin: 0.3rem 0;">🌐 www.{brand_name.lower().replace(' ', '')}.com</p>
                    <p style="margin: 0.3rem 0;">📍 123 Innovation Drive, Tech City</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with mock_col2:
        st.markdown("#### Digital Assets")
        st.markdown(f"""
        **iOS App Icon**
        <div style="
            width: 128px;
            height: 128px;
            background: white;
            border-radius: 2.5rem;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0.5rem 0;
            padding: 1.5rem;
            border: 1px solid #f0f0f0;
        ">
            <img src="{logo_result}" alt="Icon" style="max-width: 85%; max-height: 85%; object-fit: contain;">
        </div>
        
        **Dark Mode**
        <div style="
            background: #1A1B1F;
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid #404040;
            text-align: center;
            margin-top: 0.5rem;
        ">
            <div style="width: 80px; height: 80px; margin: 0 auto 0.5rem; display: flex; align-items: center; justify-content: center;">
                <img src="{logo_result}" alt="Dark" style="max-width: 100%; max-height: 100%; object-fit: contain; filter: brightness(1.1) contrast(1.1);">
            </div>
            <p style="color: #ffffff99; font-size: 0.75rem; margin: 0.5rem 0 0; letter-spacing: 0.5px;">Dark UI Adaptability</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature highlights
    st.markdown("---")
    st.markdown("### ✨ Key Features")
    
    feat_col1, feat_col2, feat_col3 = st.columns(3)
    
    with feat_col1:
        st.markdown("""
        <div style="
            background: #F5F5F5;
            border: 1px solid #D0D0D0;
            border-left: 4px solid #FF4444;
            border-radius: 0.85rem;
            padding: 1.2rem;
            text-align: center;
        ">
            <p style="font-size: 1.5rem; margin: 0 0 0.5rem;">✅</p>
            <p style="font-weight: 700; color: #151619; margin: 0 0 0.3rem; font-size: 0.9rem;">Vector Ready</p>
            <p style="font-size: 0.8rem; color: #666; margin: 0; line-height: 1.4;">High-contrast designs optimized for SVG conversion.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with feat_col2:
        st.markdown("""
        <div style="
            background: #F5F5F5;
            border: 1px solid #D0D0D0;
            border-left: 4px solid #FF4444;
            border-radius: 0.85rem;
            padding: 1.2rem;
            text-align: center;
        ">
            <p style="font-size: 1.5rem; margin: 0 0 0.5rem;">💼</p>
            <p style="font-weight: 700; color: #151619; margin: 0 0 0.3rem; font-size: 0.9rem;">Commercial Use</p>
            <p style="font-size: 0.8rem; color: #666; margin: 0; line-height: 1.4;">AI-generated assets for projects & web applications.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with feat_col3:
        st.markdown("""
        <div style="
            background: #F5F5F5;
            border: 1px solid #D0D0D0;
            border-left: 4px solid #FF4444;
            border-radius: 0.85rem;
            padding: 1.2rem;
            text-align: center;
        ">
            <p style="font-size: 1.5rem; margin: 0 0 0.5rem;">⚡</p>
            <p style="font-weight: 700; color: #151619; margin: 0 0 0.3rem; font-size: 0.9rem;">Neural Design</p>
            <p style="font-size: 0.8rem; color: #666; margin: 0; line-height: 1.4;">Powered by DALL-E 3 & Gemini Image synthesis.</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# MAIN APP
# ============================================================================

# Header with gradient
st.markdown("""
<div class="header-container">
    <h1>✨ LogoForge AI</h1>
    <p>Professional AI-Powered Logo Generation Platform</p>
</div>
""", unsafe_allow_html=True)

# API Status
col1, col2, col3 = st.columns([2, 1, 1])
with col3:
    health_ok, health_info = check_api_health()
    if health_ok:
        st.markdown('<div class="api-status connected">✅ Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="api-status disconnected">❌ Disconnected</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["🎨 Generate Logo", "📚 Gallery", "ℹ️ Info & Guides"])

# ============================================================================
# TAB 1: GENERATE
# ============================================================================

with tab1:
    # Initialize session states for button selections
    if "selected_generator" not in st.session_state:
        st.session_state.selected_generator = "dalle-3"
    if "selected_style" not in st.session_state:
        st.session_state.selected_style = "minimalist"
    if "selected_palette" not in st.session_state:
        st.session_state.selected_palette = "ocean"
    
    # Create two-column layout
    form_col, preview_col = st.columns([1.15, 1.4])
    
    with form_col:
        # ---- Brand Details Section ----
        st.markdown("### 👤 Brand Identity")
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        
        brand_name = st.text_input(
            "Brand Name",
            placeholder="Enter your company or project name",
            help="The name of your brand/company. This will be integrated into the logo design."
        )
        
        brand_description = st.text_area(
            "Brand Description",
            placeholder="What does your brand do? What industry? What makes you unique?",
            height=110,
            help="Provide details about what your brand does, your industry, and unique value proposition for better logo results."
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ---- Advanced Guidelines Section (Collapsible) ----
        with st.expander("⚙️ Advanced Guidelines", expanded=False):
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                tagline = st.text_input(
                    "Tagline",
                    placeholder="e.g. Innovation at Speed",
                    key="adv_tagline",
                    help="Your brand's motto or slogan"
                )
                elements_include = st.text_input(
                    "Include Elements",
                    placeholder="e.g., Gear, Leaf, Circle",
                    key="adv_include",
                    help="Specific design elements to include"
                )
                typography = st.text_input(
                    "Typography Preference",
                    placeholder="e.g., Modern Sans-Serif, Bold Serif",
                    key="adv_typo",
                    help="Font style preferences for text elements"
                )
            
            with col2:
                elements_avoid = st.text_input(
                    "Avoid Elements",
                    placeholder="e.g., Animals, Circles",
                    key="adv_avoid",
                    help="Design elements to exclude from logo"
                )
                st.write("")  # Spacer
                st.write("")  # Spacer
                st.write("")  # Spacer
            
            brand_mission = st.text_area(
                "Brand Mission",
                placeholder="What is the core purpose of your brand?",
                height=80,
                key="adv_mission",
                help="Describe your brand's mission and values"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ---- Visual Settings Section ----
        st.markdown("### 🎨 Visual Style")
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        
        # Generator selector with better labeling
        st.markdown("**AI Generator** 🤖")
        st.markdown("<small>Choose your preferred AI model for logo generation</small>", unsafe_allow_html=True)
        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            if st.button("🎨 DALL-E 3", use_container_width=True, key="btn_dalle"):
                st.session_state.selected_generator = "dalle-3"
                st.rerun()
        with gen_col2:
            if st.button("✨ Gemini", use_container_width=True, key="btn_gemini"):
                st.session_state.selected_generator = "gemini"
                st.rerun()
        
        generator = st.session_state.selected_generator
        
        # Show generator info
        if generator == "dalle-3":
            st.info("💡 **DALL-E 3**: Premium HD outputs (20-30 seconds) • Best for professional logos")
        else:
            st.info("⚡ **Gemini**: Fast & versatile (10-20 seconds) • Great for quick iterations")
        
        st.write("")
        
        # Style selector as grid buttons
        st.markdown("**Design Style** 🎭")
        st.markdown("<small>Select your preferred visual aesthetic</small>", unsafe_allow_html=True)
        styles_list = [
            ('minimalist', '🟢 Minimalist', 'Clean, simple geometric shapes'),
            ('tech', '🔮 Tech/Modern', 'Sleek, futuristic design'),
            ('vintage', '🏛️ Vintage', 'Classic, nostalgic feel'),
            ('abstract', '🎨 Abstract', 'Unique, creative representation'),
            ('mascot', '🎭 Mascot', 'Character-based design'),
            ('luxury', '👑 Luxury', 'Elegant, high-end aesthetic'),
        ]
        
        style_cols = st.columns(3)
        for idx in range(3):
            with style_cols[idx]:
                key_name = styles_list[idx][0]
                label = styles_list[idx][1]
                button_pressed = st.button(label, use_container_width=True, key=f"style_{key_name}")
                if button_pressed:
                    st.session_state.selected_style = key_name
                    st.rerun()
        
        style_cols2 = st.columns(3)
        for idx in range(3, 6):
            with style_cols2[idx-3]:
                key_name = styles_list[idx][0]
                label = styles_list[idx][1]
                button_pressed = st.button(label, use_container_width=True, key=f"style_{key_name}")
                if button_pressed:
                    st.session_state.selected_style = key_name
                    st.rerun()
        
        style = st.session_state.selected_style
        st.write("")
        
        # Color palette selector
        st.markdown("**Color Palette** 🌈")
        st.markdown("<small>Choose color scheme matching your brand</small>", unsafe_allow_html=True)
        palettes_list = [
            ('monochrome', '⚫ Monochrome', 'Black & white'),
            ('ocean', '🌊 Ocean', 'Cool blues'),
            ('sunset', '🌅 Sunset', 'Warm oranges'),
            ('forest', '🌲 Forest', 'Natural greens'),
            ('royal', '👑 Royal', 'Purple & gold'),
            ('neon', '⚡ Neon', 'Vibrant neon'),
        ]
        
        pal_cols = st.columns(3)
        for idx in range(3):
            with pal_cols[idx]:
                key_name = palettes_list[idx][0]
                label = palettes_list[idx][1]
                button_pressed = st.button(label, use_container_width=True, key=f"pal_{key_name}")
                if button_pressed:
                    st.session_state.selected_palette = key_name
                    st.rerun()
        
        pal_cols2 = st.columns(3)
        for idx in range(3, 6):
            with pal_cols2[idx-3]:
                key_name = palettes_list[idx][0]
                label = palettes_list[idx][1]
                button_pressed = st.button(label, use_container_width=True, key=f"pal_{key_name}")
                if button_pressed:
                    st.session_state.selected_palette = key_name
                    st.rerun()
        
        palette = st.session_state.selected_palette
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ---- Generate Button (Bold Red) ----
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        if st.button("✨ Generate Logo", use_container_width=True, key="gen_main"):
            if not brand_name.strip() and not brand_description.strip():
                st.error("❌ Please enter brand name or description")
            else:
                with st.spinner("⏳ Generating your logo... (may take 10-30 seconds)"):
                    # Collect advanced options if provided
                    tagline = st.session_state.get("adv_tagline", "")
                    typography = st.session_state.get("adv_typo", "")
                    elements_include = st.session_state.get("adv_include", "")
                    elements_avoid = st.session_state.get("adv_avoid", "")
                    brand_mission = st.session_state.get("adv_mission", "")
                    
                    request_data = {
                        "text": brand_name or "Brand",
                        "description": brand_description,
                        "style": style,
                        "palette": palette,
                        "generator": generator,
                    }
                    
                    if tagline or typography or elements_include or elements_avoid or brand_mission:
                        request_data.update({
                            "tagline": tagline,
                            "typography": typography,
                            "elements_to_include": elements_include,
                            "elements_to_avoid": elements_avoid,
                            "brand_mission": brand_mission
                        })
                    
                    success, result = generate_logo(request_data)
                    
                    if success:
                        st.session_state.current_logo = result
                        st.session_state.generation_history.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "brand": brand_name,
                            "style": style,
                            "palette": palette,
                            "generator": generator,
                            "logo": result
                        })
                        st.success("✅ Logo generated successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Generation failed: {result}")
    
    with preview_col:
        st.markdown("### 📺 Live Preview Canvas")
        st.markdown('<div class="preview-container">', unsafe_allow_html=True)
        
        if st.session_state.current_logo:
            display_logo_result(st.session_state.current_logo)
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #f8f9fc 0%, #edf2f7 100%);
                border: 2px dashed #cbd5e0;
                border-radius: 1rem;
                padding: 4rem 2rem;
                text-align: center;
                min-height: 350px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div style="color: #718096;">
                    <h3 style="margin-bottom: 1rem; font-size: 1.5rem;">🎨</h3>
                    <p style="font-size: 1.05rem; margin: 0;">Fill in brand details and click Generate to see your logo here</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# TAB 2: GALLERY
# ============================================================================

with tab2:
    st.markdown("### 📚 Generation History & Gallery")
    
    if not st.session_state.generation_history:
        st.markdown("""
        <div style="
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, #F9F9FC 0%, #F0F0F7 100%);
            border-radius: 1rem;
            border: 2px dashed #D0D0D0;
        ">
            <p style="font-size: 3rem; margin: 0 0 1rem;">🚀</p>
            <h3 style="color: #151619; margin: 0 0 0.5rem;">No Logos Generated Yet</h3>
            <p style="color: #666; margin: 0;">Visit the <strong>Generate Logo</strong> tab to create your first amazing logo!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**Total Generated:** {len(st.session_state.generation_history)} logo(s)")
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.write("")
        
        st.markdown('---')
        
        # Display in reverse chronological order
        for i, item in enumerate(reversed(st.session_state.generation_history)):
            with st.container():
                st.markdown(f"""
                <div style="
                    background: #F5F5F5;
                    border: 1px solid #D0D0D0;
                    border-radius: 1rem;
                    padding: 1.5rem;
                    margin-bottom: 1rem;
                    transition: all 0.3s ease;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <h4 style="color: #151619; margin: 0 0 0.3rem; font-size: 1.2rem;">{item['brand']}</h4>
                            <p style="color: #666; font-size: 0.85rem; margin: 0 0 0.5rem;">{item['timestamp']}</p>
                            <p style="color: #666; font-size: 0.9rem; margin: 0;">
                                <strong>Style:</strong> <em>{item['style']}</em> • <strong>Palette:</strong> <em>{item['palette']}</em>
                            </p>
                        </div>
                        <div>
                            {'<div class="generator-badge dalle-badge">🎨 DALL-E 3</div>' if item['generator'] == 'dalle-3' else '<div class="generator-badge gemini-badge">✨ Gemini</div>'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                col_view, col_use, col_del = st.columns(3)
                
                with col_view:
                    if st.button("👁️ View & Download", key=f"view_{i}", use_container_width=True):
                        st.session_state.current_logo = item['logo']
                        st.switch_tab("🎨 Generate Logo")
                        st.rerun()
                
                with col_use:
                    if st.button("🔄 Use Settings", key=f"use_{i}", use_container_width=True):
                        st.session_state.current_logo = item['logo']
                        st.info("✅ Logo selected! Switch to Generate tab to use similar settings.")
                
                with col_del:
                    if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                        st.session_state.generation_history.pop(len(st.session_state.generation_history) - 1 - i)
                        st.rerun()
                
                st.write("")

# ============================================================================
# TAB 3: INFO
# ============================================================================

with tab3:
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 💡 About LogoForge AI")
    st.markdown("""
    **LogoForge AI** is a professional logo generation platform powered by cutting-edge AI models (DALL-E 3 and Google Gemini).
    
    Generate stunning, professional logos for your brand in seconds with our intuitive interface and advanced customization options.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### 🎨 Design Styles (6 Options)")
        styles_info = {
            'minimalist': 'Minimalist - Clean and simple geometric shapes',
            'tech': 'Tech/Modern - Sleek, futuristic design',
            'vintage': 'Vintage - Classic, nostalgic aesthetic',
            'abstract': 'Abstract - Unique, creative representation',
            'mascot': 'Mascot - Character-based, friendly design',
            'luxury': 'Luxury - Elegant, high-end aesthetic'
        }
        for style_key, style_desc in styles_info.items():
            st.markdown(f"✨ {style_desc}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### 🌈 Color Palettes (6 Options)")
        palettes_info = {
            'monochrome': 'Monochrome - Black & white timeless elegance',
            'ocean': 'Ocean - Cool blues inspiring trust',
            'sunset': 'Sunset - Warm oranges energetic vibes',
            'forest': 'Forest - Natural greens eco-friendly',
            'royal': 'Royal - Purple & gold premium feel',
            'neon': 'Neon - Vibrant neon bold & modern'
        }
        for pal_key, pal_desc in palettes_info.items():
            st.markdown(f"✨ {pal_desc}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 🤖 AI Generators Comparison")
    
    comp_col1, comp_col2 = st.columns(2)
    
    with comp_col1:
        st.markdown("""
        #### 🎨 DALL-E 3 (OpenAI)
        
        **Strengths:**
        - Premium HD quality outputs
        - Excellent artistic rendering
        - Detailed and refined results
        - Best for professional requirements
        
        **Performance:**
        - Generation time: 20-30 seconds
        - Quality: Highest tier
        - Ideal for: Premium branding projects
        """)
    
    with comp_col2:
        st.markdown("""
        #### ✨ Gemini (Google)
        
        **Strengths:**
        - Fast and reliable generation
        - Versatile output styles
        - Consistent quality
        - Great for quick iterations
        
        **Performance:**
        - Generation time: 10-20 seconds
        - Quality: High and consistent
        - Ideal for: Fast prototyping & testing
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 📋 Pro Tips for Best Results")
    st.markdown("""
    1. **📝 Be Descriptive**: Provide detailed brand information for better AI understanding
    2. **🎨 Match Colors**: Select palettes that align with your industry and brand values
    3. **🧪 Experiment**: Try both generators to compare outputs and find your favorite
    4. **⚙️ Fine-tune**: Use advanced options (tagline, typography, elements) for refinement
    5. ⚡ **Test Variations**: Generate multiple logos and pick the best one for your needs
    6. 💾 **Save Early**: Download logos immediately to preserve your best creations
    7. 🔄 **Iterate**: Build on successful generations by using similar settings
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### ✨ Feature Highlights")
    
    feat_col1, feat_col2, feat_col3 = st.columns(3)
    
    with feat_col1:
        st.markdown("""
        #### 🚀 Speed
        Generate professional logos in seconds, not hours.
        """)
    
    with feat_col2:
        st.markdown("""
        #### 🎯 Accuracy
        AI-powered generation tailored to your specifications.
        """)
    
    with feat_col3:
        st.markdown("""
        #### 💼 Professional
        Commercial-ready assets for business use.
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('---')
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 🔗 Resources & Information")
    st.markdown("""
    - **Backend API**: Built with FastAPI for reliability
    - **Image Generation**: Powered by DALL-E 3 and Gemini Vision
    - **Download Format**: PNG with transparent backgrounds
    - **Usage**: Commercial use for personal and business projects
    - **Status**: ✅ Online and fully operational
    """)
    st.markdown('</div>', unsafe_allow_html=True)
