const DiseaseModel = require('../models/diseaseModel');
const CropModel = require('../models/cropModel');
const { pool } = require('../config/database');

class DashboardController {
  static async getDashboard(req, res) {
    try {
      const userId = req.session.user.id;

      const [recentScans] = await pool.query(
        'SELECT * FROM disease_scans WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', [userId]
      );
      const [riskHistory] = await pool.query(
        'SELECT * FROM risk_assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', [userId]
      );
      const [yieldPredictions] = await pool.query(
        'SELECT * FROM yield_predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', [userId]
      );
      const [userListings] = await pool.query(
        'SELECT * FROM marketplace_listings WHERE user_id = ? AND status = "active" ORDER BY created_at DESC LIMIT 5', [userId]
      );

      // Build unified feed
      const feed = [];
      recentScans.forEach(s => feed.push({ type: 'disease', data: s, date: s.created_at }));
      riskHistory.forEach(r => feed.push({ type: 'risk', data: r, date: r.created_at }));
      yieldPredictions.forEach(y => feed.push({ type: 'yield', data: y, date: y.created_at }));
      feed.sort((a, b) => new Date(b.date) - new Date(a.date));

      const scanCount = recentScans.length;
      const latestRisk = riskHistory[0] || null;

      res.render('dashboard', {
        title: 'Feed — AgriConnect',
        feed,
        scanCount,
        latestRisk,
        recentScans,
        riskHistory,
        yieldPredictions,
        userListings
      });
    } catch (error) {
      console.error('Dashboard error:', error);
      req.flash('error', 'Failed to load dashboard');
      res.redirect('/');
    }
  }
}

module.exports = DashboardController;
