"""
AgriSense AI - Farm Risk Scoring Service
Uses Random Forest for multi-factor risk calculation.
Trains on agricultural risk data or uses pre-trained model.
"""

import os
import json
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'risk_model.pkl')

# Crop encoding
CROP_ENCODING = {
    'rice': 0, 'wheat': 1, 'tomato': 2, 'potato': 3,
    'maize': 4, 'cotton': 5, 'sugarcane': 6, 'onion': 7, 'soybean': 8
}

model = None


def create_and_train_model():
    """Train Random Forest on synthetic agricultural risk data."""
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    
    print("🏗️ Training Risk Score model with agricultural data...")
    
    np.random.seed(42)
    n_samples = 5000
    
    # Features: temperature, humidity, rainfall, soil_ph, soil_moisture, 
    #           disease_severity, market_price, crop_type
    temperatures = np.random.uniform(15, 45, n_samples)
    humidities = np.random.uniform(20, 95, n_samples)
    rainfalls = np.random.uniform(0, 500, n_samples)
    soil_phs = np.random.uniform(4.0, 9.0, n_samples)
    soil_moistures = np.random.uniform(10, 90, n_samples)
    disease_severities = np.random.uniform(0, 10, n_samples)
    market_prices = np.random.uniform(5, 100, n_samples)
    crop_types = np.random.randint(0, 9, n_samples)
    
    X = np.column_stack([
        temperatures, humidities, rainfalls, soil_phs,
        soil_moistures, disease_severities, market_prices, crop_types
    ])
    
    # Calculate risk based on real agricultural heuristics
    risk_scores = np.zeros(n_samples)
    
    # Temperature risk (too hot or too cold)
    temp_risk = np.where(temperatures > 40, 8, np.where(temperatures < 18, 6, np.abs(temperatures - 28) / 3))
    
    # Humidity risk (too high promotes fungus, too low causes drought stress)
    humidity_risk = np.where(humidities > 85, 7, np.where(humidities < 30, 6, np.abs(humidities - 60) / 10))
    
    # Rainfall risk
    rain_risk = np.where(rainfalls > 350, 8, np.where(rainfalls < 30, 7, np.abs(rainfalls - 150) / 50))
    
    # Soil pH risk (optimal 6.0-7.0 for most crops)
    ph_risk = np.abs(soil_phs - 6.5) * 2
    
    # Soil moisture risk
    moisture_risk = np.where(soil_moistures > 80, 6, np.where(soil_moistures < 20, 7, np.abs(soil_moistures - 50) / 10))
    
    # Disease severity (direct risk factor)
    disease_risk = disease_severities
    
    # Market price (low price = high risk for farmer)
    price_risk = np.where(market_prices < 15, 7, np.where(market_prices > 60, 2, (60 - market_prices) / 10))
    
    # Combined risk score (0-100)
    risk_scores = (temp_risk * 0.15 + humidity_risk * 0.1 + rain_risk * 0.15 + 
                   ph_risk * 0.1 + moisture_risk * 0.1 + disease_risk * 0.25 + 
                   price_risk * 0.15) * 10
    risk_scores = np.clip(risk_scores, 0, 100)
    
    # Create risk categories
    risk_labels = np.digitize(risk_scores, bins=[0, 33, 66, 100]) - 1  # 0=Low, 1=Medium, 2=High
    
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X, risk_labels)
    
    # Also train a regressor for continuous risk scores
    from sklearn.ensemble import RandomForestRegressor
    rf_regressor = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        random_state=42,
        n_jobs=-1
    )
    rf_regressor.fit(X, risk_scores)
    
    # Save both models
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({'classifier': rf_model, 'regressor': rf_regressor}, MODEL_PATH)
    
    print(f"✅ Risk model trained and saved to {MODEL_PATH}")
    return {'classifier': rf_model, 'regressor': rf_regressor}


def load_model():
    """Load or train the risk model."""
    global model
    
    try:
        import joblib
        
        if os.path.exists(MODEL_PATH):
            print(f"✅ Loading risk model from {MODEL_PATH}")
            model = joblib.load(MODEL_PATH)
        else:
            print("⚠️  No pre-trained model found. Training new model...")
            model = create_and_train_model()
            
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("   Training new model...")
        model = create_and_train_model()


@app.route('/predict', methods=['POST'])
def predict():
    """Calculate farm risk score."""
    try:
        data = request.get_json()
        
        crop_type = CROP_ENCODING.get(data.get('crop_type', '').lower(), 0)
        temperature = float(data.get('temperature', 30))
        humidity = float(data.get('humidity', 60))
        rainfall = float(data.get('rainfall', 100))
        soil_ph = float(data.get('soil_ph', 6.5))
        soil_moisture = float(data.get('soil_moisture', 50))
        disease_severity = float(data.get('disease_severity', 0))
        market_price = float(data.get('market_price', 25))
        
        features = np.array([[temperature, humidity, rainfall, soil_ph,
                              soil_moisture, disease_severity, market_price, crop_type]])
        
        # Get risk score (continuous)
        risk_score = float(model['regressor'].predict(features)[0])
        risk_score = max(0, min(100, risk_score))
        
        # Get risk level
        risk_class = int(model['classifier'].predict(features)[0])
        risk_levels = ['Low', 'Medium', 'High']
        risk_level = risk_levels[min(risk_class, 2)]
        
        # Calculate individual factor contributions
        temp_factor = min(10, abs(temperature - 28) / 2)
        soil_factor = min(10, abs(soil_ph - 6.5) * 2 + abs(soil_moisture - 50) / 8)
        disease_factor = disease_severity
        market_factor = min(10, max(0, (50 - market_price) / 5)) if market_price < 50 else 0
        
        # Recommendations
        recommendations = []
        if temperature > 38:
            recommendations.append("🌡️ High temperature detected. Consider shade nets and frequent irrigation.")
        if temperature < 18:
            recommendations.append("❄️ Low temperature detected. Protect crops from frost.")
        if humidity > 80:
            recommendations.append("💧 High humidity increases fungal disease risk. Ensure proper ventilation.")
        if soil_ph < 5.5:
            recommendations.append("🧪 Acidic soil detected. Consider lime application.")
        if soil_ph > 7.5:
            recommendations.append("🧪 Alkaline soil. Consider adding sulfur or organic matter.")
        if disease_severity > 5:
            recommendations.append("🦠 High disease severity. Immediate treatment recommended.")
        if market_price < 20:
            recommendations.append("📉 Low market prices. Consider storage or value-added processing.")
        if rainfall > 300:
            recommendations.append("🌧️ Heavy rainfall expected. Ensure proper drainage.")
        if not recommendations:
            recommendations.append("✅ Farm conditions look good. Continue regular monitoring.")
        
        result = {
            'risk_score': round(risk_score, 1),
            'risk_level': risk_level,
            'factors': {
                'weather': round(temp_factor, 1),
                'soil': round(soil_factor, 1),
                'disease': round(disease_factor, 1),
                'market': round(market_factor, 1)
            },
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
    print("⚠️ Risk Scoring Service starting on port 5002...")
    app.run(host='0.0.0.0', port=5002, debug=False)
