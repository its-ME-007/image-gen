import os
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv 
from flask import Flask, jsonify, request 

load_dotenv()
# needs to be tested
app = Flask(__name__)

firebase_bucket = None

@app.before_first_request
def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    global firebase_bucket
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("service_account_key.json")
            bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET') or 'image-gen-34b6b.firebasestorage.app'
            firebase_app = firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
            firebase_bucket = storage.bucket(app=firebase_app)
            print(f"Firebase Admin SDK initialized successfully for bucket: {bucket_name}")
        except FileNotFoundError:
            print("Error: service_account_key.json not found.")
            print("Please ensure the service account key file is in the correct location.")
            firebase_bucket = None 
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            firebase_bucket = None 
    else:
        print("Firebase Admin SDK already initialized.")
        try:
             firebase_bucket = storage.bucket(app=firebase_admin.get_app())
        except Exception as e:
             print(f"Error getting existing Firebase bucket: {e}")
             firebase_bucket = None 

def list_files_in_folder(bucket, folder_path):
    """
    Lists files in a specified folder path within the Firebase Storage bucket.

    Args:
        bucket: The Firebase Storage bucket object.
        folder_path: The path to the folder (e.g., 'user_images/abcdef123456').
                     Include a trailing slash to list contents directly within the folder.

    Returns:
        A list of dictionaries, where each dictionary contains 'name' and 'url'
        of a file, or None if an error occurs, or an empty list if no files found.
    """
    if not bucket:
        print("Error: Firebase bucket is not initialized.")
        return None
    print(f"\nAttempting to list files in folder: {folder_path}")
    try:
        blobs = bucket.list_blobs(prefix=folder_path)
        file_list = [blob for blob in blobs if blob.name != folder_path]
        if not file_list:
            print(f"No files found in folder: {folder_path}")
            return [] 
        print(f"Found {len(file_list)} file(s).")
        image_data = []
        for blob in file_list:
            file_url = get_public_url(blob) 
            if file_url:
                image_data.append({
                    'name': os.path.basename(blob.name), 
                    'full_path': blob.name, 
                    'url': file_url
                })
            else:
                print(f"Warning: Could not get public URL for {blob.name}")
        return image_data
    except Exception as e:
        print(f"Error listing files: {e}")
        return None

def get_public_url(blob):
    """
    Gets the public URL for a given blob (file).
    Note: The file must be publicly accessible (via storage rules or make_public()).

    Args:
        blob: The Firebase Storage blob object.

    Returns:
        The public URL string, or None if the blob is not publicly accessible
        or an error occurs.
    """
    if not blob:
        return None
    try:
        if blob.public_url:
            return blob.public_url
        else:
            return None
    except Exception as e:
        print(f"Error getting public URL for '{blob.name}': {e}")
        return None

@app.route('/api/user_images/<user_uid>', methods=['GET'])
def get_user_images(user_uid):
    """
    API endpoint to fetch image URLs for a specific user.

    Args:
        user_uid: The unique ID of the user (from the URL path).

    Returns:
        A JSON response containing a list of image data (name, full_path, url)
        or an error message.
    """
    if firebase_bucket is None:
        return jsonify({'status': 'error', 'message': 'Firebase Storage is not initialized.'}), 500

    if not user_uid:
        return jsonify({'status': 'error', 'message': 'User UID is required.'}), 400

    user_folder_path = f"user_images/{user_uid}/" 
    image_list = list_files_in_folder(firebase_bucket, user_folder_path)

    if image_list is None:
        return jsonify({'status': 'error', 'message': 'An error occurred while fetching images.'}), 500
    elif not image_list:
        return jsonify({'status': 'success', 'message': f'No images found for user {user_uid}.', 'images': []}), 200
    else:
        return jsonify({'status': 'success', 'message': f'Successfully fetched images for user {user_uid}.', 'images': image_list}), 200

if __name__ == '__main__':
    app.run(debug=True) 
