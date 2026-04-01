"""
AgriSense AI - Disease Detection Service
Uses MobileNetV2 for plant disease classification.
Fixed pipeline: proper preprocessing + top-N predictions + confidence thresholds.
"""

import os
import sys
import json
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps
import io

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'disease_model.h5')
CLASS_NAMES_PATH = os.path.join(os.path.dirname(__file__), 'models', 'disease_classes.json')
IMG_SIZE = 224

# Disease info mapping — all 38 PlantVillage classes
DISEASE_INFO = {
    'Apple___Apple_scab': {'crop': 'Apple', 'disease': 'Apple Scab'},
    'Apple___Black_rot': {'crop': 'Apple', 'disease': 'Black Rot'},
    'Apple___Cedar_apple_rust': {'crop': 'Apple', 'disease': 'Cedar Apple Rust'},
    'Apple___healthy': {'crop': 'Apple', 'disease': 'Healthy'},
    'Blueberry___healthy': {'crop': 'Blueberry', 'disease': 'Healthy'},
    'Cherry_(including_sour)___Powdery_mildew': {'crop': 'Cherry', 'disease': 'Powdery Mildew'},
    'Cherry_(including_sour)___healthy': {'crop': 'Cherry', 'disease': 'Healthy'},
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': {'crop': 'Corn', 'disease': 'Cercospora Leaf Spot'},
    'Corn_(maize)___Common_rust_': {'crop': 'Corn', 'disease': 'Common Rust'},
    'Corn_(maize)___Northern_Leaf_Blight': {'crop': 'Corn', 'disease': 'Northern Leaf Blight'},
    'Corn_(maize)___healthy': {'crop': 'Corn', 'disease': 'Healthy'},
    'Grape___Black_rot': {'crop': 'Grape', 'disease': 'Black Rot'},
    'Grape___Esca_(Black_Measles)': {'crop': 'Grape', 'disease': 'Esca (Black Measles)'},
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': {'crop': 'Grape', 'disease': 'Leaf Blight'},
    'Grape___healthy': {'crop': 'Grape', 'disease': 'Healthy'},
    'Orange___Haunglongbing_(Citrus_greening)': {'crop': 'Orange', 'disease': 'Huanglongbing (Citrus Greening)'},
    'Peach___Bacterial_spot': {'crop': 'Peach', 'disease': 'Bacterial Spot'},
    'Peach___healthy': {'crop': 'Peach', 'disease': 'Healthy'},
    'Pepper,_bell___Bacterial_spot': {'crop': 'Bell Pepper', 'disease': 'Bacterial Spot'},
    'Pepper,_bell___healthy': {'crop': 'Bell Pepper', 'disease': 'Healthy'},
    'Potato___Early_blight': {'crop': 'Potato', 'disease': 'Early Blight'},
    'Potato___Late_blight': {'crop': 'Potato', 'disease': 'Late Blight'},
    'Potato___healthy': {'crop': 'Potato', 'disease': 'Healthy'},
    'Raspberry___healthy': {'crop': 'Raspberry', 'disease': 'Healthy'},
    'Soybean___healthy': {'crop': 'Soybean', 'disease': 'Healthy'},
    'Squash___Powdery_mildew': {'crop': 'Squash', 'disease': 'Powdery Mildew'},
    'Strawberry___Leaf_scorch': {'crop': 'Strawberry', 'disease': 'Leaf Scorch'},
    'Strawberry___healthy': {'crop': 'Strawberry', 'disease': 'Healthy'},
    'Tomato___Bacterial_spot': {'crop': 'Tomato', 'disease': 'Bacterial Spot'},
    'Tomato___Early_blight': {'crop': 'Tomato', 'disease': 'Early Blight'},
    'Tomato___Late_blight': {'crop': 'Tomato', 'disease': 'Late Blight'},
    'Tomato___Leaf_Mold': {'crop': 'Tomato', 'disease': 'Leaf Mold'},
    'Tomato___Septoria_leaf_spot': {'crop': 'Tomato', 'disease': 'Septoria Leaf Spot'},
    'Tomato___Spider_mites Two-spotted_spider_mite': {'crop': 'Tomato', 'disease': 'Spider Mites'},
    'Tomato___Target_Spot': {'crop': 'Tomato', 'disease': 'Target Spot'},
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': {'crop': 'Tomato', 'disease': 'Yellow Leaf Curl Virus'},
    'Tomato___Tomato_mosaic_virus': {'crop': 'Tomato', 'disease': 'Mosaic Virus'},
    'Tomato___healthy': {'crop': 'Tomato', 'disease': 'Healthy'},
}

model = None
class_names = None


def load_model():
    """Load the trained MobileNetV2 model."""
    global model, class_names

    try:
        import tensorflow as tf

        if os.path.exists(MODEL_PATH):
            print(f"[OK] Loading trained model from {MODEL_PATH}")
            model = tf.keras.models.load_model(MODEL_PATH)

            if os.path.exists(CLASS_NAMES_PATH):
                with open(CLASS_NAMES_PATH, 'r') as f:
                    class_names = json.load(f)
            else:
                class_names = list(DISEASE_INFO.keys())

            print(f"[OK] Model loaded with {len(class_names)} classes")
        else:
            print("[WARN] No trained model found.")
            print("   Run: python train_disease_model.py")
            model = None

    except Exception as e:
        print(f"[ERROR] Error loading model: {e}")
        model = None


def preprocess_image(image_bytes):
    """
    Preprocess image to match training pipeline exactly.
    Training used ImageDataGenerator with rescale=1./255 and resize to 224x224.
    Key fix: center-crop to square before resizing to avoid distortion.
    """
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert('RGB')

    # EXIF orientation fix
    img = ImageOps.exif_transpose(img)

    # Center-crop to square (matches how PlantVillage images are square)
    w, h = img.size
    short_side = min(w, h)
    left = (w - short_side) // 2
    top = (h - short_side) // 2
    img = img.crop((left, top, left + short_side, top + short_side))

    # Resize to model input size using high-quality resampling
    img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

    # Convert to array and normalize exactly like training (rescale=1./255)
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


def predict_with_tta(img_bytes):
    """
    Test-Time Augmentation: predict on original + horizontally flipped image,
    then average the predictions for more robust results.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img = ImageOps.exif_transpose(img)

    # Center-crop to square
    w, h = img.size
    short_side = min(w, h)
    left = (w - short_side) // 2
    top = (h - short_side) // 2
    img = img.crop((left, top, left + short_side, top + short_side))
    img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

    # Original
    arr1 = np.array(img, dtype=np.float32) / 255.0

    # Horizontally flipped
    arr2 = np.array(img.transpose(Image.FLIP_LEFT_RIGHT), dtype=np.float32) / 255.0

    batch = np.stack([arr1, arr2], axis=0)
    preds = model.predict(batch, verbose=0)

    # Average predictions
    avg_preds = np.mean(preds, axis=0)
    return avg_preds


@app.route('/', methods=['GET'])
def index():
    """Root page — service status and test UI."""
    status = "✅ Model Loaded" if model is not None else "❌ Model Not Loaded"
    num_classes = len(class_names) if class_names else 0
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>AgriSense Disease Detection API</title>
    <style>
      body {{ font-family: 'Segoe UI', sans-serif; max-width: 700px; margin: 40px auto; padding: 20px;
             background: #f0fdf4; color: #1a1a2e; }}
      h1 {{ color: #16a34a; }} h2 {{ color: #333; }}
      .status {{ padding: 12px 20px; border-radius: 8px; background: #dcfce7; border: 1px solid #86efac;
                margin: 16px 0; font-weight: 600; }}
      .status.error {{ background: #fef2f2; border-color: #fca5a5; }}
      form {{ background: white; padding: 24px; border-radius: 12px; border: 1px solid #e5e7eb;
             box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
      input[type=file] {{ margin: 12px 0; }}
      button {{ background: #16a34a; color: white; border: none; padding: 10px 24px; border-radius: 8px;
               cursor: pointer; font-size: 15px; font-weight: 600; }}
      button:hover {{ background: #15803d; }}
      pre {{ background: #f8fafc; padding: 16px; border-radius: 8px; overflow-x: auto;
            border: 1px solid #e2e8f0; font-size: 13px; }}
      .endpoints {{ background: white; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb; }}
      code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 14px; }}
    </style></head>
    <body>
      <h1>🔬 AgriSense Disease Detection API</h1>
      <div class="status {'error' if model is None else ''}">{status} — {num_classes} classes</div>

      <h2>📡 API Endpoints</h2>
      <div class="endpoints">
        <p><code>GET /</code> — This page</p>
        <p><code>GET /health</code> — JSON health check</p>
        <p><code>POST /predict</code> — Upload image → disease prediction (with TTA)</p>
      </div>

      <h2>🧪 Quick Test</h2>
      <form action="/predict" method="POST" enctype="multipart/form-data">
        <label><strong>Upload a plant leaf image:</strong></label><br>
        <input type="file" name="image" accept="image/*" required><br><br>
        <button type="submit">🔬 Predict Disease</button>
      </form>

      <h2>📋 Loaded Classes ({num_classes})</h2>
      <pre>{chr(10).join(class_names) if class_names else 'No classes loaded'}</pre>
    </body></html>
    """


@app.route('/predict', methods=['POST'])
def predict():
    """Predict disease from uploaded image with TTA and top-3 results."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        image_bytes = file.read()

        if model is None:
            return jsonify({'error': 'Model not loaded. Train first.'}), 503

        # Use Test-Time Augmentation for more robust predictions
        predictions = predict_with_tta(image_bytes)

        # Get top 3 predictions
        top3_idx = np.argsort(predictions)[-3:][::-1]

        top3 = []
        for idx in top3_idx:
            cls_name = class_names[idx]
            info = DISEASE_INFO.get(cls_name, {
                'crop': cls_name.split('___')[0].replace('_', ' '),
                'disease': cls_name.split('___')[1].replace('_', ' ') if '___' in cls_name else 'Unknown'
            })
            top3.append({
                'class_name': cls_name,
                'crop_type': info['crop'],
                'disease_name': info['disease'],
                'confidence': float(predictions[idx])
            })

        # Primary prediction
        best = top3[0]
        confidence = best['confidence']

        # Log for debugging
        print(f"[PREDICT] {best['disease_name']} ({best['crop_type']}) - {confidence*100:.1f}%")
        for r in top3:
            print(f"   -> {r['crop_type']:15s} | {r['disease_name']:30s} | {r['confidence']*100:.1f}%")

        result = {
            'disease_name': best['disease_name'],
            'crop_type': best['crop_type'],
            'confidence': confidence,
            'class_name': best['class_name'],
            'description': f"{best['disease_name']} detected on {best['crop_type']} with {confidence*100:.1f}% confidence.",
            'top_predictions': top3
        }

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'running',
        'model_loaded': model is not None,
        'classes': len(class_names) if class_names else 0
    })


if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'models'), exist_ok=True)
    load_model()
    print("[INFO] Disease Detection Service starting on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)
