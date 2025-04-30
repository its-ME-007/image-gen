from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
from firebase_admin import credentials, initialize_app, storage
import firebase_admin

def gen_image():
    """
    Generates an image using the Gemini API based on a text prompt.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("Please set the GOOGLE_API_KEY environment variable.")

    client = genai.Client(api_key=api_key)

    contents = ('HEY CAN U GENERATE A HEAVY MACHINERY STEEL CUTTER FOR A FACTORY ENVIRONMENT?')

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
        )
    )
    image_data = None 
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image_data = part.inline_data.data 
            image = Image.open(BytesIO((part.inline_data.data)))
            image.save('gemini-native-image.png')
            image.show()
    return image_data

def init_db():
    if not firebase_admin._apps:  
        cred = credentials.Certificate("service_account_key.json")
        initialize_app(cred, {'storageBucket': 'image-gen-34b6b.firebasestorage.app'})
        print("Firebase Admin SDK initialized successfully.")
    else:
        print("Firebase Admin SDK already initialized.")
    return storage.bucket() 

def store_image_in_db(bucket, image_data, filename="generated_image.png"):
    """
    Stores the generated image data in Firebase Storage.

    Args:
        bucket: The Firebase Storage bucket.
        image_data: The image data in bytes.
        filename: The name to use when saving the image in storage.  Defaults to "generated_image.png".
    """
    if not image_data:
        print("No image data to store.")
        return  # Exit if there's no image data

    try:
        blob = bucket.blob(filename)

        blob.upload_from_file(BytesIO(image_data), content_type='image/png')  # Or 'image/jpeg', depending on your image type.

        print(f"Image uploaded to Firebase Storage: {filename}")
        # Optionally, you can get the public URL of the uploaded image:
        # print(f"Image URL: {blob.public_url}")

    except Exception as e:
        print(f"Error uploading image: {e}")

if __name__ == "__main__":
    bucket = init_db()

    image_data = gen_image() 

    if bucket and image_data:
        store_image_in_db(bucket, image_data)
    elif not image_data:
        print("Image generation failed.  No image to store.")
