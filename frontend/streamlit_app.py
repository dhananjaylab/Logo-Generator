import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:5050")

# Page Configuration
st.set_page_config(
    page_title="Brand Identity Architect", 
    page_icon="🎨", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .logo-mark {
        background: #2563eb;
        color: white;
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px;
        font-weight: 700;
        font-size: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .section-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #94a3b8;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0.5rem;
    }

    /* Mockups */
    .mockup-container {
        display: flex;
        gap: 20px;
        justify-content: center;
        margin-top: 30px;
        flex-wrap: wrap;
    }

    .mockup-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }

    .business-card {
        width: 320px;
        height: 180px;
        position: relative;
        display: flex;
        align-items: center;
        padding: 0 24px;
        justify-content: space-between;
    }

    .business-card::before {
        content: '';
        position: absolute;
        right: 0;
        top: 0;
        height: 100%;
        width: 100px;
        background: #f8fafc;
        transform: skewX(-15deg) translateX(40px);
    }

    .mockup-logo {
        width: 64px;
        height: 64px;
        object-fit: cover;
        border-radius: 50%;
        z-index: 1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .card-text {
        z-index: 1;
        text-align: right;
    }

    .card-text h3 {
        margin: 0;
        font-size: 1.1rem;
        color: #1e293b;
    }

    .card-text p {
        margin: 0;
        font-size: 0.8rem;
        color: #64748b;
    }

    .app-icon {
        width: 100px;
        height: 100px;
        border-radius: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .mockup-logo-icon {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.2s;
    }

    .stButton>button:hover {
        background-color: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .download-link {
        color: #2563eb;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <div class="logo-mark">AI</div>
    <h1>Brand Identity Architect</h1>
    <p style="color: #64748b;">Powered by Advanced Generative Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for generation parameters
with st.sidebar:
    st.markdown('<div class="section-title">1. The Basics</div>', unsafe_allow_html=True)
    brand_name = st.text_input("Brand Name", placeholder="e.g. Ironclad Security")
    color_palette = st.text_input("Color Palette", placeholder="e.g. Navy Blue & Gold")
    provider = st.selectbox("AI Model Provider", ["openai", "gemini"], format_func=lambda x: "OpenAI (DALL-E)" if x == "openai" else "Gemini (Nano Banana)")
    
    st.markdown('<div class="section-title">2. Design Details</div>', unsafe_allow_html=True)
    logo_type = st.selectbox("Logo Type", ["Icon", "Lettermark"], help="Icon is graphic heavy, Lettermark is text/initials only")
    
    element = ""
    if logo_type == "Icon":
        element = st.text_input("Specific Icon Element (Optional)", placeholder="e.g. A Shield, A Lion")
    
    style = st.selectbox("Artistic Style", [
        "Minimalist flat design", 
        "Detailed hand-drawn sketch", 
        "3D glossy render", 
        "Abstract geometric"
    ])
    
    mood = st.selectbox("Brand Mood", [
        "Professional and Trustworthy", 
        "Playful and Friendly", 
        "Aggressive and Bold", 
        "Luxury and Elegant"
    ])
    
    number = st.slider("Number of Variations", 1, 4, 2)
    
    if st.button("Generate Custom Logos ➜", use_container_width=True):
        if not brand_name:
            st.error("Please enter a brand name.")
        else:
            with st.spinner("Analyzing parameters & designing..."):
                try:
                    data = {
                        "text": brand_name,
                        "color": color_palette,
                        "number": number,
                        "style": style,
                        "logo_type": logo_type,
                        "element": element,
                        "mood": mood,
                        "provider": provider
                    }
                    response = requests.post(f"{API_URL}/generate", data=data)
                    if response.status_code == 200:
                        st.session_state.result = response.json().get("result", [])
                        st.session_state.brand = brand_name
                        st.session_state.is_modified = False
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {str(e)}")

st.markdown('<div class="section-title">3. Modification Suite</div>', unsafe_allow_html=True)
with st.expander("✨ Refine & Modify Existing Concept"):
    st.info("Upload an existing image and tell the AI what to change.")
    with st.form("modify_form"):
        uploaded_file = st.file_uploader("Upload Your Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        instructions = st.text_area("Modification Instructions", placeholder="e.g. Change colors to blue, make it more minimalist...")
        submit_modify = st.form_submit_button("Apply Modifications ✨")
        
        if submit_modify:
            if not uploaded_file or not instructions:
                st.error("Please provide both an image and instructions.")
            else:
                with st.spinner("Modifying design..."):
                    try:
                        files = {"logo_image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"logo_instructions": instructions}
                        response = requests.post(f"{API_URL}/modify", files=files, data=data)
                        if response.status_code == 200:
                            st.session_state.result = response.json().get("result", [])
                            st.session_state.brand = "Modified Design"
                            st.session_state.is_modified = True
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Failed to connect to backend: {str(e)}")

# Display results
if "result" in st.session_state and st.session_state.result:
    st.markdown('<div class="section-title">Design Concepts</div>', unsafe_allow_html=True)
    
    # Grid display
    cols = st.columns(len(st.session_state.result))
    for i, url in enumerate(st.session_state.result):
        with cols[i]:
            st.image(url, use_column_width=True)
            st.markdown(f'<a href="{url}" target="_blank" class="download-link">Download High Res Concept {i+1}</a>', unsafe_allow_html=True)

    # Visual Identity Preview
    st.markdown('<div class="section-title">Visual Identity Preview</div>', unsafe_allow_html=True)
    
    first_image = st.session_state.result[0]
    brand_display = st.session_state.brand if st.session_state.brand else "Your Brand"
    
    st.markdown(f"""
    <div class="mockup-container">
        <div class="mockup-card business-card">
            <img src="{first_image}" class="mockup-logo">
            <div class="card-text">
                <h3>{brand_display}</h3>
                <p>Global Solutions</p>
                <p style="font-size: 10px; margin-top: 5px;">contact@example.com</p>
            </div>
        </div>
        <div class="mockup-card app-icon">
            <img src="{first_image}" class="mockup-logo-icon">
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Conceptual previews of how your logo would look on physical and digital assets.")
else:
    # Empty State
    st.info("Configure the parameters in the sidebar to begin your brand design journey.")
