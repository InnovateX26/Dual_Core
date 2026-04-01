const { GoogleGenerativeAI } = require('@google/generative-ai');
const fs = require('fs');
const path = require('path');

class GeminiService {
  static chatSessions = new Map();

  static getModel() {
    const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
    return genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
  }

  static getVisionModel() {
    const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);
    return genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
  }

  /**
   * Analyze a crop image using Gemini Vision AI for disease detection.
   * Used as fallback when the ML model confidence is too low.
   */
  static async analyzeImageForDisease(imagePath) {
    const model = this.getVisionModel();

    // Read image and convert to base64
    const imageBuffer = fs.readFileSync(imagePath);
    const base64Image = imageBuffer.toString('base64');

    // Determine MIME type
    const ext = path.extname(imagePath).toLowerCase();
    const mimeMap = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };
    const mimeType = mimeMap[ext] || 'image/jpeg';

    const prompt = `You are an expert agricultural scientist and plant pathologist. Analyze this image of a crop/plant carefully.

Identify:
1. What crop/plant is shown in the image
2. Whether it is healthy or has any disease
3. If diseased, what specific disease it has
4. Your confidence level (0.0 to 1.0)

IMPORTANT RULES:
- If the plant looks healthy with no visible disease symptoms, set disease_name to "Healthy"
- Be specific about the crop type (e.g., "Corn", "Tomato", "Wheat", "Rice", etc.)
- If you can identify a specific disease, name it precisely
- Be honest about confidence - don't inflate it

Respond with ONLY a JSON object (no markdown, no code blocks):
{
  "crop_type": "the crop name",
  "disease_name": "specific disease name or Healthy",
  "confidence": 0.85,
  "description": "Brief description of what you observe in the image and your diagnosis"
}`;

    const imagePart = {
      inlineData: {
        data: base64Image,
        mimeType: mimeType,
      },
    };

    const result = await model.generateContent([prompt, imagePart]);
    const text = result.response.text().replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();

    try {
      const parsed = JSON.parse(text);
      console.log(`[Gemini Vision] Detected: ${parsed.crop_type} - ${parsed.disease_name} (${(parsed.confidence * 100).toFixed(1)}%)`);
      return parsed;
    } catch (e) {
      console.error('[Gemini Vision] Failed to parse response:', text);
      return null;
    }
  }

  static async chat(message, userId) {
    const model = this.getModel();

    if (!this.chatSessions.has(userId)) {
      const chat = model.startChat({
        history: [],
        generationConfig: { maxOutputTokens: 1000, temperature: 0.7 }
      });
      this.chatSessions.set(userId, chat);
    }

    const chat = this.chatSessions.get(userId);

    const systemContext = `You are AgriSense AI, an expert agricultural advisor. You help Indian farmers with:
- Crop disease identification and treatment
- Best farming practices
- Government schemes and subsidies (PM-KISAN, PMFBY, etc.)
- Weather advisory and seasonal recommendations
- Organic and chemical treatment options
- Market prices and selling strategies
- Soil management and irrigation

Always respond in a helpful, practical manner. If the farmer speaks in Hindi or Hinglish, respond accordingly.
Keep answers concise but informative. Use bullet points when listing steps or options.

Farmer's question: ${message}`;

    const result = await chat.sendMessage(systemContext);
    const response = result.response.text();
    return response;
  }

  static async getDiseaseExplanation(diseaseName, confidence, cropType) {
    const model = this.getModel();

    const prompt = `You are an agricultural disease expert. A plant disease has been detected with the following details:
- Disease: ${diseaseName}
- Confidence: ${(confidence * 100).toFixed(1)}%
- Crop: ${cropType}

Provide a JSON response with exactly these fields (no markdown, no code blocks, just raw JSON):
{
  "description": "Brief description of this disease, its causes, and how it affects the crop (2-3 sentences)",
  "treatment": "Recommended treatment methods including both organic and chemical options (3-4 bullet points as a single string separated by newlines)",
  "prevention": "Preventive measures to avoid this disease in future (3-4 bullet points as a single string separated by newlines)"
}`;

    const result = await model.generateContent(prompt);
    const text = result.response.text().replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();

    try {
      return JSON.parse(text);
    } catch {
      return {
        description: `${diseaseName} detected on ${cropType} with ${(confidence * 100).toFixed(1)}% confidence.`,
        treatment: 'Please consult a local agricultural expert for specific treatment recommendations.',
        prevention: 'Maintain crop hygiene, ensure proper spacing, and monitor regularly.'
      };
    }
  }

  static async getSuggestedPrice(cropName, quantity, location) {
    const model = this.getModel();
    const prompt = `As an Indian agricultural market expert, suggest a fair price for:
- Crop: ${cropName}
- Quantity: ${quantity} kg
- Location: ${location || 'India'}

Consider current market rates in India. Return ONLY a JSON object:
{"suggested_price_per_kg": number, "total_price": number, "market_insight": "brief insight"}`;

    const result = await model.generateContent(prompt);
    const text = result.response.text().replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();

    try {
      return JSON.parse(text);
    } catch {
      return { suggested_price_per_kg: 0, total_price: 0, market_insight: 'Unable to fetch price suggestion.' };
    }
  }

  static clearSession(userId) {
    this.chatSessions.delete(userId);
  }
}

module.exports = GeminiService;
