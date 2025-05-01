import os
import io
from datetime import datetime
import re
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv

from google import genai
from google.ai import generativelanguage_v1beta as gen_language
from google.genai import types
import base64

from PIL import Image
from firebase_admin import credentials, initialize_app, storage
import firebase_admin

# Load environment variables
load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')

# Initialize Flask app
app = Flask(__name__)
firebase_bucket = None  # Global variable for Firebase bucket

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK and gets the storage bucket.
    """
    global firebase_bucket
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("service_account_key.json")
            firebase_app = initialize_app(
                cred,
                {'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET') or 'image-gen-34b6b.firebasestorage.app'},
            )
            firebase_bucket = storage.bucket(app=firebase_app)
            print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            # It's often better to raise an exception here, so the app doesn't try to run with a broken Firebase setup.
            # raise e
            return  # IMPORTANT: Exit the function on error
    else:
        print("Firebase Admin SDK already initialized.")
        try:
            firebase_bucket = storage.bucket(app=firebase_admin.get_app())
        except Exception as e:
            print(f"Error getting existing Firebase bucket: {e}")
            # raise e
            return  # IMPORTANT: Exit the function on error


def gen_image(prompt: str):
    """
    Generates an image using the Gemini API based on a text prompt.
    Returns image data (bytes) and text response.
    """
    if not api_key:
        return None, "Error: GEMINI_API_KEY not set."
    if not prompt or not prompt.strip():
        return None, "Error: Image prompt is empty."
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE']),
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
            # Check for safety ratings.  This check was improved.
            if response.candidates and hasattr(response.candidates[0], 'safety_ratings'):
                safety_ratings = response.candidates[0].safety_ratings
                blocked = any(r.blocked for r in safety_ratings)  # Simpler check
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


@app.route('/', methods=['GET'])
def index():
    """Renders the main HTML page."""
    return render_template('index.html')  # You'll need an index.html in a 'templates' folder

@app.route('/generate_and_upload', methods=['POST'])
def generate_and_upload():
    """
    Endpoint to generate an image and upload it to Firebase storage.
    Returns JSON response with the image URL.
    """
    if request.method != 'POST':
        return jsonify({'status': 'error', 'message': 'Invalid request method. Use POST.'}), 405

    # Check if the request has the correct Content-Type
    if request.headers.get('Content-Type') != 'application/json':
        return jsonify({
            'status': 'error', 
            'message': 'Invalid Content-Type. Use application/json.'
        }), 400

    try:
        request_data = request.get_json()
        if request_data is None:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid request: No JSON body provided or invalid JSON format.'
            }), 400

        prompt = request_data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'status': 'error', 'message': 'Please provide a prompt for the image.'}), 400

        # Get filename from request or generate one
        base_filename = request_data.get('filename', '').strip()
        if not base_filename:
            # Generate a filename based on prompt (first 20 chars) if none provided
            base_filename = re.sub(r'[^\w\s-]', '', prompt[:20]).strip().replace(' ', '_').lower()
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{base_filename}_{timestamp}.png"

        # Generate the image
        image_data, text_response = gen_image(prompt)
        if not image_data:
            return jsonify({'status': 'error', 'message': text_response}), 500

        # If Firebase is initialized, upload the image
        if firebase_bucket:
            try:
                # Create a file-like object from the image data
                image_file = io.BytesIO(image_data)
                
                # Upload to Firebase Storage
                blob = firebase_bucket.blob(filename)
                blob.upload_from_file(image_file, content_type='image/png')
                
                # Make the blob publicly accessible
                blob.make_public()
                
                # Get the public URL
                image_url = blob.public_url
                
                return jsonify({
                    'status': 'success',
                    'message': 'Image generated and uploaded successfully!',
                    'imageUrl': image_url,
                    'text_response': text_response
                }), 200
            except Exception as e:
                print(f"Error uploading to Firebase: {e}")
                # If upload fails, fallback to returning base64 data
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                return jsonify({
                    'status': 'partial_success',
                    'message': f'Image generated but upload failed: {e}',
                    'image_data': image_base64,
                    'text_response': text_response
                }), 200
        else:
            # Firebase not initialized, return base64 data
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            return jsonify({
                'status': 'success',
                'message': 'Image generated successfully! (Firebase storage not available)',
                'image_data': image_base64,
                'text_response': text_response
            }), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'status': 'error', 'message': f'Error processing request: {e}'}), 500


@app.route('/generate_image', methods=['POST'])
def generate_image_route():
    """
    Legacy endpoint to trigger image generation. Returns JSON response with image data.
    """
    if request.method != 'POST':
        return jsonify({'status': 'error', 'message': 'Invalid request method. Use POST.'}), 405

    # Check if the request has the correct Content-Type
    if request.headers.get('Content-Type') != 'application/json':
        return jsonify({
            'status': 'error', 
            'message': 'Invalid Content-Type. Use application/json.'
        }), 400

    try:
        request_data = request.get_json()
        if request_data is None:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid request: No JSON body provided or invalid JSON format.'
            }), 400

        prompt = request_data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'status': 'error', 'message': 'Please provide a prompt for the image.'}), 400

        image_data, text_response = gen_image(prompt)  # Get image data and text
        if not image_data:
            return jsonify({'status': 'error', 'message': text_response}), 500  # Return the error from gen_image

        # Convert image data to base64 for sending in JSON.  This is suitable for smaller images.
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        return jsonify({
            'status': 'success',
            'message': 'Image generated successfully!',
            'image_data': image_base64,  # Send base64 encoded image data
            'text_response': text_response
        }), 200
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'status': 'error', 'message': f'Error processing request: {e}'}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files (like CSS, JS)."""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    initialize_firebase()  # Initialize Firebase (if you want to use it for storage)
    app.run(debug=True) #, host='0.0.0.0'