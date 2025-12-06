# 🎨 AI Brand Identity Generator

A modern Flask application that uses OpenAI's DALL-E models to generate professional logos and visual identity mockups.

## ✨ Features
- **Smart Style Selection:** Choose from Minimalist, Cyberpunk, Luxury, and more.
- **Instant Mockups:** Automatically visualize the logo on a Business Card and App Icon.
- **Optimized Prompts:** Backend logic translates simple inputs into professional design prompts.
- **Modern UI:** Clean, responsive design with grid layouts.

## 🛠️ Setup & Installation

### 1. Clone the Repo
```bash
git clone <your-repo-url>
cd Logo-Generator/flask-logo-app/logo-app
```

### 2. Install Dependencies

It is best to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add API Key

Create a file named `.env` in the logo-app folder:

```text
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 4. Run the Application
```bash
python app.py
```

Open http://127.0.0.1:5050 in your browser.