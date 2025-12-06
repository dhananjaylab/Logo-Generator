import os
from flask import Flask, request, render_template
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI Client (v1.0+)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        try:
            brand_name = request.form["text"]
            color_theme = request.form["color"]
            style = request.form["style"]
            
            # Smart Prompt Engineering
            # We hide the complexity from the user but send detailed instructions to the AI
            full_prompt = (
                f"A high-quality, vector-style logo for a company named '{brand_name}'. "
                f"Style: {style}. "
                f"Primary Color: {color_theme}. "
                f"White background, centered, symmetrical, flat design, high resolution."
            )

            # Call OpenAI DALL-E 2 (Cost-effective & Fast)
            response = client.images.generate(
                model="dall-e-2",
                prompt=full_prompt,
                n=2, # Generate 2 variations
                size="256x256"
            )

            image_urls = [item.url for item in response.data]
            
            return render_template("index.html", result=image_urls, brand=brand_name)

        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5050)