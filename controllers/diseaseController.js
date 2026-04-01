const axios = require('axios');
const fs = require('fs');
const DiseaseModel = require('../models/diseaseModel');
const GeminiService = require('../services/geminiService');

class DiseaseController {
  static async getDetection(req, res) {
    try {
      const userId = req.session.user.id;
      const history = await DiseaseModel.getScansByUser(userId, 10);
      res.render('disease-detection', {
        title: 'Disease Detection - AgriSense AI',
        history
      });
    } catch (error) {
      console.error('Disease page error:', error);
      req.flash('error', 'Failed to load disease detection page');
      res.redirect('/dashboard');
    }
  }

  static async detectDisease(req, res) {
    try {
      if (!req.file) {
        req.flash('error', 'Please upload an image');
        return res.redirect('/disease');
      }

      const imagePath = `/uploads/disease/${req.file.filename}`;
      const fullPath = req.file.path;

      let finalResult = null; // { disease_name, confidence, crop_type, description }

      // STRATEGY: Use Gemini Vision AI as PRIMARY detector (much more accurate
      // on real-world photos), fall back to ML model only if Gemini fails.

      // Step 1: Try Gemini Vision AI first (primary)
      console.log('[AI] Analyzing image with Gemini Vision AI...');
      try {
        const geminiVisionResult = await GeminiService.analyzeImageForDisease(fullPath);
        if (geminiVisionResult && geminiVisionResult.disease_name) {
          finalResult = {
            disease_name: geminiVisionResult.disease_name,
            confidence: geminiVisionResult.confidence || 0.85,
            crop_type: geminiVisionResult.crop_type || 'Unknown',
            description: geminiVisionResult.description || `${geminiVisionResult.disease_name} detected on ${geminiVisionResult.crop_type}.`
          };
          console.log(`[AI] Gemini Vision result: ${finalResult.disease_name} (${finalResult.crop_type}) - ${(finalResult.confidence * 100).toFixed(1)}%`);
        }
      } catch (visionError) {
        console.error('[AI] Gemini Vision error:', visionError.message);
      }

      // Step 2: If Gemini failed, fall back to Python ML model
      if (!finalResult) {
        console.log('[ML] Gemini unavailable, falling back to ML model...');
        try {
          const FormData = require('form-data');
          const form = new FormData();
          form.append('image', fs.createReadStream(fullPath));

          const mlResponse = await axios.post(
            `${process.env.ML_DISEASE_URL || 'http://localhost:5001'}/predict`,
            form,
            { headers: form.getHeaders(), timeout: 30000 }
          );
          const mlResult = mlResponse.data;
          finalResult = {
            disease_name: mlResult.disease_name,
            confidence: mlResult.confidence,
            crop_type: mlResult.crop_type || 'Unknown',
            description: mlResult.description
          };
          console.log(`[ML] Fallback result: ${finalResult.disease_name} (${finalResult.crop_type}) - ${(finalResult.confidence * 100).toFixed(1)}%`);
        } catch (mlError) {
          console.error('[ML] Service error:', mlError.message);
        }
      }

      // Step 3: If both failed, show error
      if (!finalResult) {
        req.flash('error', 'Disease detection is currently unavailable. Please try again later.');
        return res.redirect('/disease');
      }

      // Step 5: Get detailed AI explanation from Gemini
      let aiExplanation = {};
      try {
        aiExplanation = await GeminiService.getDiseaseExplanation(
          finalResult.disease_name,
          finalResult.confidence,
          finalResult.crop_type
        );
      } catch (geminiError) {
        console.error('[AI] Explanation error:', geminiError.message);
        aiExplanation = {
          description: finalResult.description || 'AI explanation unavailable.',
          treatment: 'Please consult a local agricultural expert.',
          prevention: 'Maintain good crop hygiene and regular monitoring.'
        };
      }

      // Step 6: Save scan to database
      const scanData = {
        user_id: req.session.user.id,
        image_path: imagePath,
        disease_name: finalResult.disease_name,
        confidence: finalResult.confidence,
        crop_type: finalResult.crop_type,
        description: aiExplanation.description,
        treatment: aiExplanation.treatment,
        prevention: aiExplanation.prevention
      };

      const scanId = await DiseaseModel.saveScan(scanData);
      const scan = await DiseaseModel.getScanById(scanId);

      res.render('disease-result', {
        title: 'Detection Result - AgriSense AI',
        scan,
        aiExplanation
      });

    } catch (error) {
      console.error('Disease detection error:', error);
      req.flash('error', 'An error occurred during disease detection');
      res.redirect('/disease');
    }
  }

  static async getScanDetail(req, res) {
    try {
      const scan = await DiseaseModel.getScanById(req.params.id);
      if (!scan) {
        req.flash('error', 'Scan not found');
        return res.redirect('/disease');
      }
      res.render('disease-result', {
        title: 'Scan Detail - AgriSense AI',
        scan,
        aiExplanation: {
          description: scan.description,
          treatment: scan.treatment,
          prevention: scan.prevention
        }
      });
    } catch (error) {
      console.error('Scan detail error:', error);
      req.flash('error', 'Failed to load scan details');
      res.redirect('/disease');
    }
  }
}

module.exports = DiseaseController;
