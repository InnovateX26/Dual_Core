"""
AgriSense AI - Price Forecasting Service
Uses Random Forest for crop price prediction.
"""

import os
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'price_model.pkl')

CROP_ENCODING = {
    'rice': 0, 'wheat': 1, 'tomato': 2, 'potato': 3,
    'maize': 4, 'cotton': 5, 'sugarcane': 6, 'onion': 7, 'soybean': 8
}

SEASON_ENCODING = {'kharif': 0, 'rabi': 1, 'zaid': 2}

# Base MSP / market prices (₹ per kg)
BASE_PRICES = {
    'rice': 22, 'wheat': 23, 'tomato': 25, 'potato': 15,
    'maize': 20, 'cotton': 65, 'sugarcane': 3.5, 'onion': 18, 'soybean': 42
}

model = None


def create_and_train_model():
    """Train Random Forest on price data."""
    from sklearn.ensemble import RandomForestRegressor
    import joblib
    
    print("🏗️ Training Price Forecast model...")
    
    np.random.seed(42)
    n_samples = 5000
    
    crop_types = np.random.randint(0, 9, n_samples)
    current_prices = np.random.uniform(5, 120, n_samples)
    seasons = np.random.randint(0, 3, n_samples)
    demand_indices = np.random.uniform(1, 10, n_samples)
    quantities = np.random.uniform(10, 5000, n_samples)
    
    X = np.column_stack([crop_types, current_prices, seasons, demand_indices, quantities])
    
    # Price influenced by demand, season, quantity
    demand_factor = 0.7 + demand_indices * 0.06
    
    # Season factor (prices go up during off-season)
    season_factor = np.where(seasons == 0, 1.0, np.where(seasons == 1, 1.1, 0.95))
    
    # Quantity factor (bulk discounts)
    quantity_factor = np.where(quantities > 2000, 0.92, np.where(quantities < 100, 1.08, 1.0))
    
    predicted_prices = current_prices * demand_factor * season_factor * quantity_factor
    predicted_prices += np.random.normal(0, predicted_prices * 0.05)
    predicted_prices = np.maximum(predicted_prices, 1)
    
    rf_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X, predicted_prices)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(rf_model, MODEL_PATH)
    
    print(f"✅ Price model trained and saved to {MODEL_PATH}")
    return rf_model


def load_model():
    global model
    try:
        import joblib
        if os.path.exists(MODEL_PATH):
            print(f"✅ Loading price model from {MODEL_PATH}")
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
        
        crop_name = data.get('crop_type', 'rice').lower()
        crop_type = CROP_ENCODING.get(crop_name, 0)
        current_price = float(data.get('current_price', BASE_PRICES.get(crop_name, 25)))
        season = SEASON_ENCODING.get(data.get('season', 'kharif').lower(), 0)
        demand_index = float(data.get('demand_index', 5))
        quantity = float(data.get('quantity', 100))
        
        features = np.array([[crop_type, current_price, season, demand_index, quantity]])
        
        predicted_price = float(model.predict(features)[0])
        predicted_price = max(1, predicted_price)
        
        # Determine trend
        price_change = ((predicted_price - current_price) / current_price) * 100
        if price_change > 5:
            trend = "📈 Rising"
        elif price_change < -5:
            trend = "📉 Falling"
        else:
            trend = "➡️ Stable"
        
        # Best sell window
        season_names = {0: 'Kharif', 1: 'Rabi', 2: 'Zaid'}
        if demand_index > 7:
            sell_window = "Now! High demand detected."
        elif price_change > 8:
            sell_window = "Within 1-2 weeks as prices are rising."
        elif price_change < -5:
            sell_window = "Consider selling soon. Prices may drop further."
        else:
            sell_window = f"Stable market. Good to sell during peak {season_names.get(season, '')} season."
        
        result = {
            'predicted_price': round(predicted_price, 2),
            'current_price': current_price,
            'price_change_percent': round(price_change, 1),
            'price_trend': trend,
            'best_sell_window': sell_window,
            'total_value': round(predicted_price * quantity, 2),
            'crop_type': crop_name.capitalize()
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'running', 'model_loaded': model is not None})


if __name__ == '__main__':
    load_model()
    print("💰 Price Forecast Service starting on port 5004...")
    app.run(host='0.0.0.0', port=5004, debug=False)
