from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key found (first 5 chars): {api_key[:5]}...")

try:
    client = genai.Client(api_key=api_key)
    print("Listing models...")
    models = list(client.models.list())
    print(f"Found {len(models)} models.")
    for m in models:
        print(f" - {m.name}")
        
    print("\nTesting Imagen 3 with models/ prefix...")
    imagen_models = [
        'models/imagen-3.0-generate-001',
        'models/imagen-3.0-fast-generate-001',
    ]
    
    for model_id in imagen_models:
        print(f"Trying model: {model_id}...")
        try:
            response = client.models.generate_image(
                model=model_id,
                prompt='A minimalist logo for a tech brand'
            )
            print(f"Successfully generated image with {model_id}!")
            break
        except Exception as e:
            print(f"Failed with {model_id}: {e}")

except Exception as e:
    print(f"General error occurred: {e}")
