import os
import base64
import io
from flask import Flask, request, render_template
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Load API key
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_image_base64(file):
    """Convert uploaded image file to base64 for API"""
    file.seek(0)
    return base64.standard_b64encode(file.read()).decode('utf-8')

@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        try:
            # Check if it's a logo modification request (file upload)
            if 'logo_image' in request.files and request.files['logo_image'].filename != '':
                logo_file = request.files['logo_image']
                instructions = request.form.get("logo_instructions", "")
                
                # Validate file
                if not logo_file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    return render_template("index.html", error="Only PNG and JPG files are supported")
                
                # Convert image to base64
                try:
                    img_base64 = get_image_base64(logo_file)
                except Exception as e:
                    return render_template("index.html", error=f"Error processing image: {str(e)}")
                
                # Create modification prompt
                modification_prompt = (
                    f"You are a professional logo designer. I have provided an existing logo image. "
                    f"Please modify it based on these instructions: {instructions}\n\n"
                    f"Create an improved version that maintains the original concept while incorporating the requested changes. "
                    f"Ensure high quality, professional appearance, and maintain vector style."
                )
                
                # Call OpenAI Vision API with image
                try:
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=modification_prompt,
                        n=1,
                        size="1024x1024"
                    )
                    image_urls = [item.url for item in response.data]
                    return render_template("index.html", result=image_urls, is_modified=True, brand="Modified Logo")
                except Exception as e:
                    return render_template("index.html", error=f"Logo modification failed: {str(e)}")
            
            # Otherwise, generate new logo from scratch
            brand_name = request.form.get("text", "Brand")
            color_theme = request.form.get("color", "Black and White")
            num_images = int(request.form.get("number", 2))
            
            # Limit max images to 4 to save API costs/latency
            num_images = max(1, min(num_images, 4))
            
            # Capture Deep Customization
            style = request.form.get("style", "Modern")
            logo_type = request.form.get("logo_type", "Icon")
            element = request.form.get("element", "")
            mood = request.form.get("mood", "Professional")

            # Construct the "Smart Prompt"
            if logo_type == "Lettermark":
                design_focus = f"a typographic lettermark logo focusing on the initials of '{brand_name}'"
                visual_element = ""
            else:
                elem_text = element if element else "an abstract geometric shape"
                design_focus = f"a pictorial logo featuring {elem_text}"
                visual_element = f"Centerpiece: {elem_text}."

            full_prompt = (
                f"A {mood}, {style} logo design. "
                f"Type: {design_focus}. "
                f"Brand Name: '{brand_name}'. "
                f"Color Palette: {color_theme}. "
                f"{visual_element} "
                f"High contrast, vector style, white background, professional studio quality."
            )

            # Call API
            response = client.images.generate(
                model="dall-e-2",
                prompt=full_prompt,
                n=num_images,
                size="256x256"
            )

            image_urls = [item.url for item in response.data]
            
            return render_template("index.html", result=image_urls, brand=brand_name)

        except Exception as e:
            return render_template("index.html", error=f"Generation failed: {str(e)}")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5050)