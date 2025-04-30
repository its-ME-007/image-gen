import os
import io
from datetime import datetime
import re 
from flask import Flask, render_template, jsonify, request, send_from_directory # Import 'request'
from dotenv import load_dotenv

from google import genai
from google.genai import types
from PIL import Image
from firebase_admin import credentials, initialize_app, storage
import firebase_admin

load_dotenv()
# we need to add username wise folders in firebase storage to store images separately for each user
app = Flask(__name__)
firebase_bucket = None

def initialize_firebase():
    global firebase_bucket
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("service_account_key.json")
            firebase_app = initialize_app(cred, {'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET') or 'image-gen-34b6b.firebasestorage.app'})
            firebase_bucket = storage.bucket(app=firebase_app)
            print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            # Consider exiting or raising an error if initialization is critical
    else:
        print("Firebase Admin SDK already initialized.")
        try:
             firebase_bucket = storage.bucket(app=firebase_admin.get_app())
        except Exception as e:
             print(f"Error getting existing Firebase bucket: {e}")

def gen_image(prompt: str):
    """
    Generates an image using the Gemini API based on a text prompt.
    Returns image data (bytes)
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return None, "Error: GEMINI_API_KEY not set."
    if not prompt or not prompt.strip():
         return None, "Error: Image prompt is empty."
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )

        image_data = None
        text_response = ""

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
             for part in response.candidates[0].content.parts:
                 if part.text is not None:
                     text_response += part.text
                 elif part.inline_data is not None:
                     image_data = part.inline_data.data

        if image_data is None:
             error_message = "Image generation failed or returned no image."
             # Check for safety ratings that might block content
             if hasattr(response.candidates[0], 'safety_ratings'):
                 blocked = any(r.probability > types.HarmProbability.NEGLIGIBLE for r in response.candidates[0].safety_ratings)
                 if blocked:
                      error_message += " (Reason: May have been blocked by safety filters)"

             if text_response:
                 error_message += f" Text response: {text_response}"
             return None, error_message


        print("Image generated successfully (bytes received).")
        if text_response:
             print(f"Gemini Text Response: {text_response}")

        return image_data, text_response

    except Exception as e:
        print(f"Error during image generation: {e}")
        return None, f"Error during image generation: {e}"

def store_image_in_db(bucket, image_data: bytes, filename="generated_image.png"):
    """
    Stores the generated image data in Firebase Storage.
    Returns the public URL or None on failure.
    """
    if not bucket:
        return None, "Error: Firebase bucket not initialized for storage."
    if not image_data:
        return None, "Error: No image data provided to store."

    try:
        blob = bucket.blob(filename)
        blob.upload_from_file(io.BytesIO(image_data), content_type='image/png')
        blob.make_public() # Make the blob publicly accessible
        print(f"Image uploaded to Firebase Storage: {filename}")
        print(f"Image URL: {blob.public_url}")
        return blob.public_url, None
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None, f"Error uploading image: {e}"

@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/generate_and_upload', methods=['POST'])
def generate_and_upload_route():
    """
    Endpoint to trigger image generation and upload based on user input.
    """
    request_data = request.get_json()

    if not request_data:
        return jsonify({'status': 'error', 'message': 'Invalid request: No JSON body provided.'}), 400

    # Extract prompt and filename
    prompt = request_data.get('prompt', '').strip()
    user_filename_base = request_data.get('filename', '').strip() \
    
    # Basic validation
    if not prompt:
        return jsonify({'status': 'error', 'message': 'Please provide a prompt for the image.'}), 400
    if firebase_bucket is None:
         return jsonify({'status': 'error', 'message': 'Firebase Storage is not initialized.'}), 500


    # 1. Generate the image
    image_data, gen_error = gen_image(prompt)
    if gen_error:
        return jsonify({'status': 'error', 'message': gen_error}), 500
    if not image_data:
         # This case should usually be covered by gen_error
         return jsonify({'status': 'error', 'message': 'Image generation returned no data unexpectedly.'}), 500

    # 2. Determine and sanitize filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not user_filename_base:
        # Use a default name or a snippet of the prompt if no filename is provided
        # Sanitize the prompt snippet
        snippet = prompt[:30] # Use first 30 characters of prompt
        base_filename = re.sub(r'[^\w\- ]', '', snippet).replace(' ', '_') # Keep alphanumeric, hyphens, underscores, spaces, then replace spaces
        if not base_filename: # If sanitizing resulted in empty string
             base_filename = "generated_image"
    else:
        base_filename = re.sub(r'[^\w\- ]', '', user_filename_base).replace(' ', '_')
        if not base_filename: # If sanitizing resulted in empty string
             # Fallback if user input sanitizes to empty
             base_filename = "user_provided_name" # Or handle as an error
    # Combine base name, timestamp, and extension, store in a folder
    final_filename = f"generated_images/{base_filename}_{timestamp}.png"


    # 3. Store the image in Firebase
    image_url, store_error = store_image_in_db(firebase_bucket, image_data, final_filename)
    if store_error:
         return jsonify({'status': 'error', 'message': store_error}), 500

    if image_url:
        return jsonify({
            'status': 'success',
            'message': 'Image generated and uploaded successfully!',
            'imageUrl': image_url
            }), 200
    else:
         # Fallback error case
         return jsonify({'status': 'error', 'message': 'Image upload failed without a specific error message.'}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    initialize_firebase()
    app.run(debug=True)