import io
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client(api_key="AIzaSyCkj-1YSHckNUugVfxWSu0X5ZXLCsXzKhs")

prompt = ("Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme")
response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt],
)

# Access the first candidate, then its content, then the parts
for part in response.candidates[0].content.parts:
    if part.text:
        print(part.text)
    elif part.inline_data:
        # 1. Access the raw bytes via .data
        # 2. Use io.BytesIO to make the bytes "readable" like a file
        # 3. Open it with Image.open
        image = Image.open(io.BytesIO(part.inline_data.data))
        image.save("generated_image5.png")
        print("Image saved as generated_image.png")

# from google import genai
# from google.genai import types
# from PIL import Image

# client = genai.Client(api_key="AIzaSyCkj-1YSHckNUugVfxWSu0X5ZXLCsXzKhs")

# prompt = (
#     "Create a picture of my cat eating a nano-banana in a "
#     "fancy restaurant under the Gemini constellation",
# )

# image = Image.open("generated_image.png")

# response = client.models.generate_content(
#     model="gemini-3.1-flash-image-preview",
#     contents=[prompt, image],
# )

# for part in response.parts:
#     if part.text is not None:
#         print(part.text)
#     elif part.inline_data is not None:
#         image = part.as_image()
#         image.save("generated_image1.png")

# from google import genai
# from google.genai import types

# client = genai.Client()

# chat = client.chats.create(
#     model="gemini-3.1-flash-image-preview",
#     config=types.GenerateContentConfig(
#         response_modalities=['TEXT', 'IMAGE'],
#         tools=[{"google_search": {}}]
#     )
# )

# message = "Create a vibrant infographic that explains photosynthesis as if it were a recipe for a plant's favorite food. Show the \"ingredients\" (sunlight, water, CO2) and the \"finished dish\" (sugar/energy). The style should be like a page from a colorful kids' cookbook, suitable for a 4th grader."

# response = chat.send_message(message)

# for part in response.parts:
#     if part.text is not None:
#         print(part.text)
#     elif image:= part.as_image():
#         image.save("photosynthesis.png")