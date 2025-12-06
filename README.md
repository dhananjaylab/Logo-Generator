# 🎨 Brand Identity Architect (GenAI)

An advanced Flask application that leverages OpenAI's DALL-E to generate deeply customizable logos and brand assets. Unlike simple logo generators, this tool allows users to define the **Mood**, **Iconography**, and **Artistic Style** of their brand.

## ✨ New Customization Features

1.  **Icon vs. Lettermark Control:**
    *   *Icon Mode:* Generates a symbol-heavy logo (e.g., an apple, a shield).
    *   *Lettermark Mode:* Focuses purely on typography and initials (e.g., IBM, CNN style).
2.  **Specific Elements:** Users can explicitly request objects (e.g., "A Coffee Cup", "A Fox") to be the centerpiece.
3.  **Mood Selector:** Define the emotional resonance of the brand (Professional, Playful, Aggressive, Luxury).
4.  **Live Visual Identity Mockups:** Instantly preview the logo on a business card and app icon.
5.  **Artistic Styles:** Choose from Minimalist, Vintage, 3D/Tech, or Abstract designs.
6.  **Smart Prompt Architecture:** Backend automatically constructs professional AI prompts based on your inputs.

## 🛠️ Installation & Usage

### Prerequisites
*   Python 3.8+
*   OpenAI API Key

### Steps
1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd Logo-Generator/flask-logo-app/logo-app
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Ensure `requirements.txt` contains: `Flask`, `openai>=1.3.0`, `python-dotenv`.*

3.  **Setup Environment:**
    Create a `.env` file in the root folder:
    ```
    OPENAI_API_KEY=sk-your-key-here
    ```

4.  **Run the App:**
    ```bash
    python app.py
    ```
    Visit `http://127.0.0.1:5050` in your browser.

## 🧠 How the Smart Prompt Works
The application takes user inputs and constructs a professional prompt for the AI:
> "A {Mood}, {Style} logo design. Type: {Logo_Type} featuring {Element}. Brand Name: '{Name}'. Color Palette: {Colors}..."

This ensures higher quality and more relevant results compared to standard prompts.