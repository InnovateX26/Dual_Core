const GeminiService = require('../services/geminiService');
const { pool } = require('../config/database');
const axios = require('axios');

const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://localhost:8000';

class ChatController {
  static async getChat(req, res) {
    try {
      const userId = req.session.user.id;
      const [history] = await pool.query(
        'SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50',
        [userId]
      );

      // Fetch supported languages from RAG service
      let languages = [];
      try {
        const langRes = await axios.get(`${RAG_SERVICE_URL}/api/languages`, { timeout: 3000 });
        languages = langRes.data.languages || [];
      } catch {
        // Fallback languages if RAG service is not running
        languages = [
          { code: 'en', name: 'English', native: 'English', tts_code: 'en-IN' },
          { code: 'hi', name: 'Hindi', native: 'हिन्दी', tts_code: 'hi-IN' },
          { code: 'hi-en', name: 'Hinglish', native: 'Hinglish', tts_code: 'hi-IN' },
          { code: 'bn', name: 'Bengali', native: 'বাংলা', tts_code: 'bn-IN' },
          { code: 'ta', name: 'Tamil', native: 'தமிழ்', tts_code: 'ta-IN' },
          { code: 'te', name: 'Telugu', native: 'తెలుగు', tts_code: 'te-IN' },
          { code: 'mr', name: 'Marathi', native: 'मराठी', tts_code: 'mr-IN' },
          { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', tts_code: 'gu-IN' },
          { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', tts_code: 'kn-IN' },
          { code: 'ml', name: 'Malayalam', native: 'മലയാളം', tts_code: 'ml-IN' },
          { code: 'mai', name: 'Maithili', native: 'मैथिली', tts_code: 'hi-IN' },
        ];
      }

      res.render('chat', {
        title: 'Krishi Mitra — AI Farm Advisor',
        chatHistory: history.reverse(),
        languages
      });
    } catch (error) {
      console.error('Chat page error:', error);
      req.flash('error', 'Failed to load chat page');
      res.redirect('/dashboard');
    }
  }

  static async sendMessage(req, res) {
    try {
      const { message, language_hint } = req.body;
      const userId = req.session.user.id;

      if (!message || message.trim().length === 0) {
        return res.json({ success: false, error: 'Please enter a message' });
      }

      let response, detectedLanguage, suggestions, modelUsed, contextUsed;

      // Try RAG service first
      try {
        const ragRes = await axios.post(`${RAG_SERVICE_URL}/api/chat`, {
          message: message.trim(),
          language_hint: language_hint || null,
          user_id: String(userId),
        }, { timeout: 30000 });

        const data = ragRes.data;
        response = data.response;
        detectedLanguage = data.detected_language;
        suggestions = data.suggestions;
        modelUsed = data.model_used;
        contextUsed = data.context_used;

      } catch (ragError) {
        console.log('[Chat] RAG service unavailable, falling back to Gemini:', ragError.message);

        // Fallback to Gemini
        response = await GeminiService.chat(message, userId);
        detectedLanguage = { language_code: 'en', language_name: 'English', confidence: 0.5 };
        suggestions = [];
        modelUsed = 'gemini-fallback';
        contextUsed = 0;
      }

      // Save to DB
      await pool.query(
        'INSERT INTO chat_history (user_id, message, response) VALUES (?, ?, ?)',
        [userId, message, response]
      );

      res.json({
        success: true,
        response,
        detected_language: detectedLanguage,
        suggestions,
        model_used: modelUsed,
        context_used: contextUsed,
      });

    } catch (error) {
      console.error('Chat error:', error);
      res.json({ success: false, error: 'Failed to get AI response. Please try again.' });
    }
  }

  static async uploadData(req, res) {
    try {
      const { category, documents } = req.body;

      if (!documents || !Array.isArray(documents) || documents.length === 0) {
        return res.json({ success: false, error: 'No documents provided' });
      }

      const ragRes = await axios.post(`${RAG_SERVICE_URL}/api/upload-data`, {
        category: category || 'custom',
        documents,
      }, { timeout: 60000 });

      res.json(ragRes.data);

    } catch (error) {
      console.error('Upload error:', error.message);
      res.json({ 
        success: false, 
        error: 'Failed to upload data. Make sure the RAG service is running.' 
      });
    }
  }

  static async clearHistory(req, res) {
    try {
      await pool.query('DELETE FROM chat_history WHERE user_id = ?', [req.session.user.id]);
      res.json({ success: true });
    } catch (error) {
      res.json({ success: false, error: 'Failed to clear history' });
    }
  }
}

module.exports = ChatController;
