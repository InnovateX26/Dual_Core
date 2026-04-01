"""Quick diagnostic: check what the model actually outputs."""
import os, json, sys, numpy as np
from PIL import Image

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'disease_model.h5')
CLASS_PATH = os.path.join(os.path.dirname(__file__), 'models', 'disease_classes.json')

model = tf.keras.models.load_model(MODEL_PATH)
with open(CLASS_PATH) as f:
    classes = json.load(f)

out = open(os.path.join(os.path.dirname(__file__), 'debug_output.txt'), 'w')

subset_dir = os.path.join(os.path.dirname(__file__), 'dataset', 'PlantVillage_subset')
test_classes = ['Apple___Apple_scab', 'Tomato___Late_blight', 'Potato___Early_blight',
                'Corn_(maize)___Common_rust_', 'Grape___Black_rot',
                'Strawberry___Leaf_scorch', 'Tomato___healthy']

for cls in test_classes:
    cls_dir = os.path.join(subset_dir, cls)
    if not os.path.exists(cls_dir):
        out.write(f"SKIP: {cls}\n")
        continue
    imgs = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
    if not imgs:
        continue
    img = Image.open(os.path.join(cls_dir, imgs[0])).convert('RGB').resize((224,224))
    arr = np.expand_dims(np.array(img)/255.0, axis=0)
    preds = model.predict(arr, verbose=0)[0]
    top5 = np.argsort(preds)[-5:][::-1]
    
    out.write(f"\nTRUE: {cls}\n")
    for i in top5:
        out.write(f"  {classes[i]:55s} {preds[i]*100:.2f}%\n")
    out.write(f"  PREDICTED: {classes[np.argmax(preds)]}\n")

out.close()
print("Done. Check python/debug_output.txt")
