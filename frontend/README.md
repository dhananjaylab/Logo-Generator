# Frontend Configuration

This directory contains the Streamlit frontend application for LogoForge AI.

## Structure

```
frontend/
├── streamlit_app.py          Main Streamlit application
├── .streamlit/
│   ├── secrets.toml          API configuration (git-ignored)
│   └── config.toml           Optional Streamlit theme
├── static/                   Static assets
│   └── style.css            Additional CSS (optional)
└── templates/               HTML templates (optional)
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Configure API:**
   ```bash
   # Create secrets.toml if missing
   mkdir -p .streamlit
   echo 'API_BASE_URL = "http://localhost:5050"' > .streamlit/secrets.toml
   ```

3. **Run:**
   ```bash
   streamlit run streamlit_app.py
   ```

## Configuration Files

### `.streamlit/secrets.toml`
Stores API configuration:
```toml
API_BASE_URL = "http://localhost:5050"
```

### `.streamlit/config.toml` (Optional)
Customize Streamlit theme:
```toml
[theme]
primaryColor = "#FF4444"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#151619"
```

## Features

- **Multi-tab interface** - Generate, Gallery, Info tabs
- **Advanced options** - Customizable branding fields
- **Generation history** - Track all created logos
- **Dual generator support** - DALL-E 3 or Gemini
- **Download support** - Save logos locally
- **Real-time health check** - API status indicator

## Environment Variables

None needed in this directory. All configuration via `secrets.toml`.

## Troubleshooting

- **"Secrets file not found"**: Run setup (see Quick Start)
- **"API Disconnected"**: Ensure backend is running
- **Generation fails**: Check backend logs and API keys

## File Descriptions

### `streamlit_app.py`
Main frontend application (380 lines):
- Page configuration and styling
- API integration functions
- UI components for all tabs
- Session state management
- Logo generation and download

### `.streamlit/secrets.toml`
Runtime secrets and configuration (git-ignored)

### `static/` & `templates/`
Optional for advanced customization
