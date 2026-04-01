"""
AgriSense AI - Yield Prediction Service
Uses Random Forest for crop yield estimation.
"""

import os
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'yield_model.pkl')

CROP_ENCODING = {
    'rice': 0, 'wheat': 1, 'tomato': 2, 'potato': 3,
    'maize': 4, 'cotton': 5, 'sugarcane': 6, 'onion': 7, 'soybean': 8
}

SOIL_ENCODING = {'poor': 0, 'average': 1, 'good': 2, 'excellent': 3}
SEASON_ENCODING = {'kharif': 0, 'rabi': 1, 'zaid': 2}

# Average yield per hectare (quintals) for reference
AVG_YIELD = {
    'rice': 25, 'wheat': 30, 'tomato': 200, 'potato': 180,
    'maize': 28, 'cotton': 15, 'sugarcane': 700, 'onion': 170, 'soybean': 12
}

model = None


def create_and_train_model():
    """Train Random Forest on agricultural yield data."""
    from sklearn.ensemble import RandomForestRegressor
    import joblib
    
    print("🏗️ Training Yield Prediction model...")
    
    np.random.seed(42)
    n_samples = 5000
    
    # Features: crop_type, area, soil_quality, rainfall, season, temperature, humidity
    crop_types = np.random.randint(0, 9, n_samples)
    areas = np.random.uniform(0.2, 20, n_samples)
    soil_qualities = np.random.randint(0, 4, n_samples)
    rainfalls = np.random.uniform(50, 400, n_samples)
    seasons = np.random.randint(0, 3, n_samples)
    temperatures = np.random.uniform(15, 42, n_samples)
    humidities = np.random.uniform(30, 90, n_samples)
    
    X = np.column_stack([crop_types, areas, soil_qualities, rainfalls, 
                         seasons, temperatures, humidities])
    
    # Calculate yields based on crop type and conditions
    base_yields = np.array([list(AVG_YIELD.values())[ct] for ct in crop_types])
    
    # Soil quality multiplier
    soil_mult = 0.6 + soil_qualities * 0.15
    
    # Temperature optimality (each crop has optimal range around 25-30°C)
    temp_factor = 1 - np.abs(temperatures - 27) / 40
    temp_factor = np.clip(temp_factor, 0.4, 1.2)
    
    # Rainfall factor
    rain_factor = np.where(rainfalls < 100, 0.7, np.where(rainfalls > 300, 0.85, 1.0))
    
    # Humidity factor
    humidity_factor = np.where(humidities < 40, 0.8, np.where(humidities > 80, 0.9, 1.0))
    
    # Calculate yield per hectare then multiply by area
    yield_per_hectare = base_yields * soil_mult * temp_factor * rain_factor * humidity_factor
    yield_per_hectare += np.random.normal(0, yield_per_hectare * 0.1)  # Add noise
    yield_per_hectare = np.maximum(yield_per_hectare, 0)
    
    total_yields = yield_per_hectare * areas
    
    rf_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X, total_yields)
    
    # Also train yield per hectare model
    rf_per_hectare = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    )
    rf_per_hectare.fit(X, yield_per_hectare)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    import joblib
    joblib.dump({'total': rf_model, 'per_hectare': rf_per_hectare}, MODEL_PATH)
    
    print(f"✅ Yield model trained and saved to {MODEL_PATH}")
    return {'total': rf_model, 'per_hectare': rf_per_hectare}


def load_model():
    global model
    try:
        import joblib
        if os.path.exists(MODEL_PATH):
            print(f"✅ Loading yield model from {MODEL_PATH}")
            model = joblib.load(MODEL_PATH)
        else:
            model = create_and_train_model()
    except Exception as e:
        print(f"❌ Error: {e}")
        model = create_and_train_model()


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        crop_type = CROP_ENCODING.get(data.get('crop_type', '').lower(), 0)
        area = float(data.get('area', 1))
        soil_quality = SOIL_ENCODING.get(data.get('soil_quality', 'good').lower(), 2)
        rainfall = float(data.get('rainfall', 150))
        season = SEASON_ENCODING.get(data.get('season', 'kharif').lower(), 0)
        temperature = float(data.get('temperature', 28))
        humidity = float(data.get('humidity', 65))
        
        features = np.array([[crop_type, area, soil_quality, rainfall, 
                              season, temperature, humidity]])
        
        total_yield = float(model['total'].predict(features)[0])
        yield_per_hectare = float(model['per_hectare'].predict(features)[0])
        
        total_yield = max(0, total_yield)
        yield_per_hectare = max(0, yield_per_hectare)
        
        # Recommendations
        crop_name = data.get('crop_type', 'crop').capitalize()
        recommendations = []
        if soil_quality <= 1:
            recommendations.append(f"Improve soil quality with organic compost for better {crop_name} yield.")
        if rainfall < 100:
            recommendations.append("Low rainfall expected. Plan for supplemental irrigation.")
        if temperature > 38:
            recommendations.append("High temperatures may stress crops. Consider mulching.")
        if not recommendations:
            recommendations.append(f"Conditions look favorable for {crop_name} cultivation!")
        
        result = {
            'predicted_yield': round(total_yield, 2),
            'yield_per_hectare': round(yield_per_hectare, 2),
            'unit': 'quintals',
            'area': area,
            'crop_type': crop_name,
            'recommendations': recommendations
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running', 'model_loaded': model is not None})


if __name__ == '__main__':
    load_model()
    print("🌾 Yield Prediction Service starting on port 5003...")
    app.run(host='0.0.0.0', port=5003, debug=False)
