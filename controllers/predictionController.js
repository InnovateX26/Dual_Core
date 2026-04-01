const { pool } = require('../config/database');

// Built-in prediction models — no external Python services needed
const CROP_PARAMS = {
  rice:      { baseYield: 55, optTemp: [22, 32], optHumid: [60, 85], optRain: [150, 300], optPh: [5.5, 6.5], msp: 22.03 },
  wheat:     { baseYield: 50, optTemp: [15, 25], optHumid: [40, 65], optRain: [50, 150],  optPh: [6.0, 7.5], msp: 22.75 },
  tomato:    { baseYield: 450, optTemp: [20, 30], optHumid: [50, 70], optRain: [50, 120], optPh: [6.0, 7.0], msp: 20 },
  potato:    { baseYield: 250, optTemp: [15, 25], optHumid: [55, 75], optRain: [80, 150],  optPh: [5.0, 6.5], msp: 15 },
  maize:     { baseYield: 60, optTemp: [21, 30], optHumid: [50, 70], optRain: [80, 200],  optPh: [5.5, 7.0], msp: 20.90 },
  cotton:    { baseYield: 20, optTemp: [25, 35], optHumid: [40, 60], optRain: [50, 100],  optPh: [6.0, 8.0], msp: 68.50 },
  sugarcane: { baseYield: 800, optTemp: [25, 35], optHumid: [70, 90], optRain: [150, 250], optPh: [6.0, 7.5], msp: 3.15 },
};

function rangeScore(val, [min, max]) {
  if (val >= min && val <= max) return 1.0;
  const dist = val < min ? min - val : val - max;
  const range = max - min;
  return Math.max(0, 1 - (dist / (range || 1)) * 0.5);
}

class PredictionController {
  static async getPredictions(req, res) {
    try {
      const userId = req.session.user.id;
      const [riskHistory] = await pool.query(
        'SELECT * FROM risk_assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', [userId]
      );
      const [yieldHistory] = await pool.query(
        'SELECT * FROM yield_predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', [userId]
      );
      res.render('predictions', { title: 'Predictions & Risk Analysis - AgriSense AI', riskHistory, yieldHistory });
    } catch (error) {
      console.error('Predictions page error:', error);
      req.flash('error', 'Failed to load predictions page');
      res.redirect('/dashboard');
    }
  }

  static async calculateRisk(req, res) {
    try {
      const { crop_type, temperature, humidity, rainfall, soil_ph, soil_moisture, disease_severity, market_price } = req.body;
      const params = CROP_PARAMS[crop_type] || CROP_PARAMS.rice;
      const temp = parseFloat(temperature), hum = parseFloat(humidity), rain = parseFloat(rainfall);
      const ph = parseFloat(soil_ph), moist = parseFloat(soil_moisture);
      const disease = parseFloat(disease_severity), price = parseFloat(market_price);

      // Calculate risk factors (0-10 scale, higher = more risk)
      const weatherRisk = (1 - (rangeScore(temp, params.optTemp) * 0.5 + rangeScore(hum, params.optHumid) * 0.3 + rangeScore(rain, params.optRain) * 0.2)) * 10;
      const soilRisk = (1 - (rangeScore(ph, params.optPh) * 0.5 + rangeScore(moist, [30, 60]) * 0.5)) * 10;
      const diseaseRisk = disease;
      const marketRisk = price < params.msp * 0.8 ? 8 : price < params.msp ? 5 : price < params.msp * 1.5 ? 2 : 1;

      const risk_score = Math.min(100, Math.max(0,
        (weatherRisk * 0.30 + soilRisk * 0.25 + diseaseRisk * 0.30 + marketRisk * 0.15) * 10
      ));

      const risk_level = risk_score < 35 ? 'Low' : risk_score < 65 ? 'Medium' : 'High';

      const recommendations = [];
      if (weatherRisk > 5) recommendations.push('⚠️ Weather conditions are not optimal. Consider protective measures.');
      if (soilRisk > 5) recommendations.push('🌱 Soil conditions need improvement. Test soil and add amendments.');
      if (diseaseRisk > 5) recommendations.push('🦠 High disease risk. Apply preventive fungicide/pesticide.');
      if (marketRisk > 5) recommendations.push('📉 Market price is below MSP. Consider government procurement or storage.');
      if (recommendations.length === 0) recommendations.push('✅ Farm conditions look good! Continue with current practices.');

      const riskResult = {
        risk_score: Math.round(risk_score * 10) / 10,
        risk_level,
        factors: { weather: Math.round(weatherRisk * 10) / 10, soil: Math.round(soilRisk * 10) / 10, disease: Math.round(diseaseRisk * 10) / 10, market: Math.round(marketRisk * 10) / 10 },
        recommendations
      };

      await pool.query(
        'INSERT INTO risk_assessments (user_id, crop_type, risk_score, risk_level, weather_factor, soil_factor, disease_factor, market_factor, recommendations) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [req.session.user.id, crop_type, riskResult.risk_score, riskResult.risk_level,
         riskResult.factors.weather, riskResult.factors.soil, riskResult.factors.disease, riskResult.factors.market,
         JSON.stringify(riskResult.recommendations)]
      );

      res.json({ success: true, data: riskResult });
    } catch (error) {
      console.error('Risk calculation error:', error);
      res.json({ success: false, error: 'Failed to calculate risk score: ' + error.message });
    }
  }

  static async predictYield(req, res) {
    try {
      const { crop_type, area, soil_quality, rainfall, season, temperature, humidity } = req.body;
      const params = CROP_PARAMS[crop_type] || CROP_PARAMS.rice;
      const areaVal = parseFloat(area), rain = parseFloat(rainfall), temp = parseFloat(temperature), hum = parseFloat(humidity);

      const qualityMultiplier = { poor: 0.6, average: 0.8, good: 1.0, excellent: 1.15 }[soil_quality] || 0.8;
      const seasonMultiplier = { kharif: 1.0, rabi: 0.95, zaid: 0.85 }[season] || 0.9;
      const weatherScore = rangeScore(temp, params.optTemp) * 0.4 + rangeScore(hum, params.optHumid) * 0.3 + rangeScore(rain, params.optRain) * 0.3;

      const yieldPerHectare = params.baseYield * qualityMultiplier * seasonMultiplier * weatherScore * (0.85 + Math.random() * 0.15);
      const totalYield = yieldPerHectare * areaVal;

      const recommendations = [];
      if (qualityMultiplier < 0.8) recommendations.push('🌱 Improve soil by adding FYM (10-15 tonnes/hectare) and vermicompost.');
      if (weatherScore < 0.7) recommendations.push('🌤️ Weather is not optimal. Consider irrigation and protective measures.');
      recommendations.push(`📊 Expected yield: ${yieldPerHectare.toFixed(1)} quintals/hectare for ${crop_type} in ${season} season.`);

      const yieldResult = {
        predicted_yield: Math.round(totalYield * 10) / 10,
        yield_per_hectare: Math.round(yieldPerHectare * 10) / 10,
        crop_type, area: areaVal, season,
        recommendations
      };

      await pool.query(
        'INSERT INTO yield_predictions (user_id, crop_type, area, predicted_yield, season) VALUES (?, ?, ?, ?, ?)',
        [req.session.user.id, crop_type, areaVal, yieldResult.predicted_yield, season]
      );

      res.json({ success: true, data: yieldResult });
    } catch (error) {
      console.error('Yield prediction error:', error);
      res.json({ success: false, error: 'Failed to predict yield: ' + error.message });
    }
  }

  static async forecastPrice(req, res) {
    try {
      const { crop_type, current_price, season, demand_index, quantity } = req.body;
      const params = CROP_PARAMS[crop_type] || CROP_PARAMS.rice;
      const price = parseFloat(current_price), demand = parseFloat(demand_index), qty = parseFloat(quantity);

      const seasonFactor = { kharif: -0.05, rabi: 0.08, zaid: 0.12 }[season] || 0;
      const demandFactor = (demand - 5) * 0.03;
      const supplyPressure = qty > 1000 ? -0.03 : qty > 500 ? -0.01 : 0.02;

      const priceChange = seasonFactor + demandFactor + supplyPressure + (Math.random() * 0.06 - 0.03);
      const predictedPrice = Math.max(params.msp * 0.7, price * (1 + priceChange));

      const trend = priceChange > 0.03 ? '📈 Upward' : priceChange < -0.03 ? '📉 Downward' : '➡️ Stable';
      const bestWindow = demand > 7 ? 'Sell now — demand is high!' : demand > 4 ? 'Hold for 2-3 weeks for better prices' : 'Store and wait — prices may improve in 4-6 weeks';

      const priceResult = {
        predicted_price: Math.round(predictedPrice * 10) / 10,
        price_trend: trend,
        best_sell_window: bestWindow,
        total_value: predictedPrice * qty,
        msp: params.msp,
        current_price: price
      };

      res.json({ success: true, data: priceResult });
    } catch (error) {
      console.error('Price forecast error:', error);
      res.json({ success: false, error: 'Failed to forecast price: ' + error.message });
    }
  }
}

module.exports = PredictionController;
