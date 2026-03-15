"""
Logo Generator Integration Verification Script
Verifies that backend, frontend, and API keys are properly configured
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_python_version():
    """Check if Python version is 3.9+"""
    print("\n" + "="*60)
    print("🔍 CHECKING PYTHON VERSION")
    print("="*60)
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected (Required: 3.9+)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} detected (Required: 3.9+)")
        return False

def check_required_files():
    """Check if all required files exist"""
    print("\n" + "="*60)
    print("📁 CHECKING REQUIRED FILES")
    print("="*60)
    
    required_files = {
        "Backend": [
            "backend/app_new.py",
            "backend/routers.py",
            "backend/services.py",
            "backend/models.py",
            "backend/dependencies.py"
        ],
        "Frontend": [
            "frontend/streamlit_app.py",
            "frontend/.streamlit/secrets.toml"
        ],
        "Config": [
            "requirements.txt",
            ".env"
        ]
    }
    
    all_good = True
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file in files:
            path = Path(file)
            if path.exists():
                print(f"  ✅ {file}")
            else:
                print(f"  ❌ {file} (MISSING)")
                all_good = False
    
    return all_good

def check_api_keys():
    """Check if API keys are configured"""
    print("\n" + "="*60)
    print("🔐 CHECKING API KEYS")
    print("="*60)
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    all_good = True
    
    if gemini_key:
        print(f"✅ GEMINI_API_KEY: {gemini_key[:10]}...{gemini_key[-5:]}")
    else:
        print("❌ GEMINI_API_KEY: NOT SET (required)")
        all_good = False
    
    if openai_key:
        print(f"✅ OPENAI_API_KEY: {openai_key[:10]}...{openai_key[-5:]}")
    else:
        print("❌ OPENAI_API_KEY: NOT SET (required)")
        all_good = False
    
    return all_good

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n" + "="*60)
    print("📦 CHECKING PYTHON DEPENDENCIES")
    print("="*60)
    
    required_packages = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "streamlit": "Streamlit",
        "requests": "Requests",
        "openai": "OpenAI SDK",
        "google.genai": "Google GenAI",
        "PIL": "Pillow",
        "dotenv": "Python-Dotenv"
    }
    
    missing = []
    for pkg, name in required_packages.items():
        try:
            if pkg == "google.genai":
                import google.genai
            elif pkg == "PIL":
                import PIL
            elif pkg == "dotenv":
                import dotenv
            else:
                __import__(pkg)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} (NOT INSTALLED)")
            missing.append(name)
    
    return len(missing) == 0

def check_backend_health(api_url):
    """Check if backend is running and healthy"""
    print("\n" + "="*60)
    print("🏥 CHECKING BACKEND HEALTH")
    print("="*60)
    
    print(f"Attempting to connect to: {api_url}/api/health")
    
    try:
        response = requests.get(f"{api_url}/api/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Backend is running")
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Gemini: {'✅ Ready' if health.get('gemini_ready') else '❌ Not Ready'}")
            print(f"   OpenAI: {'✅ Ready' if health.get('openai_ready') else '❌ Not Ready'}")
            
            return health.get('gemini_ready') and health.get('openai_ready')
        else:
            print(f"❌ Backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {api_url}")
        print("   Make sure backend is running: python backend/app_new.py")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Backend connection timeout at {api_url}")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {str(e)}")
        return False

def check_streamlit_config():
    """Check if Streamlit is configured"""
    print("\n" + "="*60)
    print("⚙️  CHECKING STREAMLIT CONFIG")
    print("="*60)
    
    secrets_path = Path("frontend/.streamlit/secrets.toml")
    if not secrets_path.exists():
        print(f"❌ secrets.toml not found at {secrets_path}")
        return False
    
    try:
        with open(secrets_path, 'r') as f:
            content = f.read()
            if "API_BASE_URL" in content:
                print(f"✅ Streamlit secrets.toml exists")
                if "http://localhost:5050" in content:
                    print(f"✅ API_BASE_URL configured correctly")
                    return True
                else:
                    print(f"⚠️  API_BASE_URL configured but may not match backend")
                    print(f"   Content: {content}")
                    return True
            else:
                print(f"❌ API_BASE_URL not in secrets.toml")
                return False
    except Exception as e:
        print(f"❌ Error reading secrets.toml: {str(e)}")
        return False

def check_output_directory():
    """Check if output directory exists"""
    print("\n" + "="*60)
    print("📂 CHECKING OUTPUT DIRECTORY")
    print("="*60)
    
    output_dir = Path("backend/generated_logos")
    if output_dir.exists():
        print(f"✅ Output directory exists at {output_dir}")
        return True
    else:
        print(f"📌 Output directory doesn't exist yet: {output_dir}")
        print(f"   It will be created automatically on first Gemini generation")
        return True

def main():
    """Run all checks"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  LOGO GENERATOR - INTEGRATION VERIFICATION SCRIPT".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Track results
    results = {}
    
    # Run checks
    results['Python Version'] = check_python_version()
    results['Required Files'] = check_required_files()
    results['API Keys'] = check_api_keys()
    results['Dependencies'] = check_dependencies()
    results['Streamlit Config'] = check_streamlit_config()
    results['Output Directory'] = check_output_directory()
    
    # Backend health check (optional - only if other checks pass)
    if results['Dependencies'] and results['API Keys']:
        results['Backend Health'] = check_backend_health("http://localhost:5050")
    else:
        results['Backend Health'] = None
        print("\n" + "="*60)
        print("🏥 SKIPPING BACKEND HEALTH")
        print("="*60)
        print("⏭️  Skipped because dependencies or API keys are missing")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    for check, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{status}: {check}")
    
    # Overall status
    print("\n" + "="*60)
    critical_checks = [
        'Python Version',
        'Required Files', 
        'API Keys',
        'Dependencies'
    ]
    
    critical_pass = all(results.get(check) for check in critical_checks)
    
    if critical_pass:
        print("✅ ALL CRITICAL CHECKS PASSED")
        print("\nYou're ready to run the application!")
        print("\n📋 NEXT STEPS:")
        print("1. Start backend: cd backend && python app_new.py")
        print("2. In new terminal, start frontend: cd frontend && streamlit run streamlit_app.py")
        print("3. Open browser to http://localhost:8501")
        print("4. Verify API connection shows ✅")
        print("5. Generate your first logo!")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running the application.")
        print("\n💡 COMMON FIXES:")
        print("- Missing dependencies? Run: pip install -r requirements.txt")
        print("- Missing API keys? Create .env file with GEMINI_API_KEY and OPENAI_API_KEY")
        print("- Missing streamlit config? Run:")
        print("  mkdir -p frontend/.streamlit")
        print("  echo 'API_BASE_URL = \"http://localhost:5050\"' > frontend/.streamlit/secrets.toml")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
