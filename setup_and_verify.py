#!/usr/bin/env python3
"""
Logo Generator - Setup & Verification Script
Comprehensive setup verification before running the application
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def check_python_version():
    """Check Python version"""
    print_header("Python Version Check")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} - Need 3.9+")
        return False

def check_directories():
    """Check if required directories exist"""
    print_header("Directory Structure")
    
    dirs = {
        "backend": "Backend API",
        "frontend": "Frontend UI",
        "backend/.streamlit": "Frontend Config (will be created)",
    }
    
    all_ok = True
    for dir_path, name in dirs.items():
        if Path(dir_path).exists():
            print_success(f"{name}: {dir_path}")
        else:
            if ".streamlit" in dir_path:
                print_warning(f"{name}: {dir_path} (will create)")
            else:
                print_error(f"{name}: {dir_path} (MISSING)")
                all_ok = False
    
    return all_ok

def create_secrets():
    """Create Streamlit secrets file if missing"""
    print_header("Streamlit Configuration")
    
    secrets_dir = Path("frontend/.streamlit")
    secrets_file = secrets_dir / "secrets.toml"
    
    secrets_dir.mkdir(parents=True, exist_ok=True)
    
    if secrets_file.exists():
        print_success(f"Secrets file exists: {secrets_file}")
        return True
    else:
        try:
            with open(secrets_file, "w") as f:
                f.write('# API Configuration\n')
                f.write('API_BASE_URL = "http://localhost:5050"\n')
            print_success(f"Created secrets file: {secrets_file}")
            return True
        except Exception as e:
            print_error(f"Cannot create secrets: {e}")
            return False

def check_env_file():
    """Check if .env file exists"""
    print_header("Environment Configuration")
    
    env_file = Path(".env")
    
    if env_file.exists():
        with open(env_file) as f:
            content = f.read()
            if "GEMINI_API_KEY" in content and "OPENAI_API_KEY" in content:
                print_success(".env file with both API keys")
                return True
            else:
                print_warning(".env missing required keys (GEMINI_API_KEY, OPENAI_API_KEY)")
                print_info("Create .env with:")
                print("  GEMINI_API_KEY=your_key")
                print("  OPENAI_API_KEY=your_key")
                return False
    else:
        print_error(".env file not found (required)")
        print_info("Create .env in project root with:")
        print("  GEMINI_API_KEY=your_key")
        print("  OPENAI_API_KEY=your_key")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Python Dependencies")
    
    required = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "streamlit": "Streamlit",
        "requests": "Requests",
        "openai": "OpenAI SDK",
        "google.genai": "Google GenAI",
        "PIL": "Pillow",
    }
    
    missing = []
    for module, name in required.items():
        try:
            if module == "google.genai":
                import google.genai
            elif module == "PIL":
                import PIL
            else:
                __import__(module)
            print_success(name)
        except ImportError:
            print_error(name)
            missing.append(name)
    
    if missing:
        print_error(f"\nMissing {len(missing)} packages")
        print_info("Install with: pip install -r requirements.txt")
        return False
    else:
        print_success(f"\nAll {len(required)} packages installed")
        return True

def check_files():
    """Check if essential files exist"""
    print_header("Required Files")
    
    files = {
        "backend/app_new.py": "FastAPI server",
        "backend/routers.py": "API routes",
        "backend/services.py": "Generator services",
        "backend/models.py": "Data models",
        "backend/dependencies.py": "DI container",
        "backend/config.py": "Configuration",
        "backend/utils.py": "Utilities",
        "frontend/streamlit_app.py": "Streamlit frontend",
        "requirements.txt": "Dependencies",
    }
    
    missing = []
    for file_path, name in files.items():
        if Path(file_path).exists():
            print_success(f"{name}: {file_path}")
        else:
            print_error(f"{name}: {file_path} (MISSING)")
            missing.append(file_path)
    
    if missing:
        return False
    else:
        return True

def test_backend_import():
    """Test if backend can be imported"""
    print_header("Backend Import Test")
    
    try:
        sys.path.insert(0, os.path.abspath("backend"))
        import app_new
        print_success("Backend imports successfully")
        return True
    except Exception as e:
        print_error(f"Backend import failed: {e}")
        return False

def main():
    """Run all checks"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  LOGO GENERATOR - SETUP & VERIFICATION".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    results = {}
    
    # Run all checks
    results['Python Version'] = check_python_version()
    results['Directories'] = check_directories()
    results['Secrets File'] = create_secrets()
    results['Environment'] = check_env_file()
    results['Dependencies'] = check_dependencies()
    results['Required Files'] = check_files()
    results['Backend Import'] = test_backend_import()
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    # Final instructions
    if passed == total:
        print_header("Ready to Start!")
        print("""
To run the application:

1. Terminal 1 - Start Backend:
   cd backend
   python app_new.py
   
   Expected: "Uvicorn running on http://0.0.0.0:5050"

2. Terminal 2 - Start Frontend:
   cd frontend
   streamlit run streamlit_app.py
   
   Expected: Opens http://localhost:8501

3. Browser:
   Open http://localhost:8501
   Generate your first logo!

For troubleshooting, see: TROUBLESHOOTING.md
        """)
        return 0
    else:
        print_header("Issues Found")
        print(f"\n{total - passed} check(s) failed. Please fix above issues before running.\n")
        print("Common fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing .env: Create with API keys")
        print("  - Missing secrets.toml: Run this script again")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
