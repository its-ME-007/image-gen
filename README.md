# Gemini Image Generator Web App

A simple Flask-based web application that allows users to generate images using the **Google Gemini API** and upload them to **Firebase Storage**.

## ✨ Features

- Generate images from a text prompt using the **Gemini API**
- Upload the generated image to **Firebase Storage**
- Specify a custom filename for uploads
- Basic web interface for user interaction


## 🔧 Prerequisites

Ensure the following are set up before running the application:

- **Python 3.7+**
- **pip** (Python package installer)
- **Google Cloud / Firebase Project**
- **Firebase Service Account Key** (`service_account_key.json`)
- **Google Gemini API Key**
- **Firebase Storage Bucket Name** (e.g., `your-project-id.appspot.com`)


## 🚀 Setup

1. **Clone or Download** the project to your local machine.

2. **Install Dependencies**  
   Open terminal in the project directory and run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Place Firebase Credentials**  
   Download your Firebase **Service Account Key** and place it in the root directory as:
   ```
   service_account_key.json
   ```

4. **Create `.env` File**  
   In the root directory, add your credentials:
   ```env
   GEMINI_API_KEY=YOUR_GENAI_API_KEY
   FIREBASE_STORAGE_BUCKET=your-bucket-name.appspot.com
   ```

## ▶️ Running the App

In the terminal, navigate to the project directory and run:

```bash
python app.py
```

The app will start on [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## 💡 Usage

1. Open the web interface in your browser.
2. Enter an **image prompt** (description).
3. Optionally enter a **base filename**.
4. Click **"Generate & Upload Image"**.
5. Wait for generation and upload. Status and image will appear below.

---

## 🔒 Firebase Storage Rules

To make uploaded images publicly readable, use the following **Firebase Storage Rules** (for development only):

```js
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read: if true;              // WARNING: Public read access
      allow write: if request.auth != null; // Allow authenticated writes
    }
  }
}
```

## 📁 File Structure

```
.
├── app.py
├── service_account_key.json
├── .env
├── templates/
│   └── index.html
├── static/
│   └── style.css
└── requirements.txt
```

### To contribute, reach out to the owner of the repository [here](anirudh007kulkarni@gmail.com) and initiate a PR.