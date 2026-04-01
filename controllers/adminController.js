const UserModel = require('../models/userModel');
const DiseaseModel = require('../models/diseaseModel');
const CropModel = require('../models/cropModel');
const { pool } = require('../config/database');

class AdminController {
  static async getDashboard(req, res) {
    try {
      const totalUsers = await UserModel.getCount();
      const totalFarmers = await UserModel.getFarmerCount();
      const totalScans = await DiseaseModel.getTotalScans();
      const totalListings = await CropModel.getTotalCount();
      const activeListings = await CropModel.getActiveCount();
      const recentScans = await DiseaseModel.getRecentScans(5);
      const recentListings = await CropModel.getAllListings({ limit: 5 });

      // Monthly user signups for chart
      const [monthlyUsers] = await pool.query(`
        SELECT DATE_FORMAT(created_at, '%Y-%m') as month, COUNT(*) as count 
        FROM users 
        GROUP BY DATE_FORMAT(created_at, '%Y-%m') 
        ORDER BY month DESC LIMIT 6
      `);

      res.render('admin/dashboard', {
        title: 'Admin Dashboard - AgriSense AI',
        stats: { totalUsers, totalFarmers, totalScans, totalListings, activeListings },
        recentScans,
        recentListings,
        monthlyUsers: monthlyUsers.reverse()
      });
    } catch (error) {
      console.error('Admin dashboard error:', error);
      req.flash('error', 'Failed to load admin dashboard');
      res.redirect('/');
    }
  }

  static async getUsers(req, res) {
    try {
      const users = await UserModel.getAll();
      res.render('admin/users', {
        title: 'User Management - AgriSense AI',
        users
      });
    } catch (error) {
      console.error('Admin users error:', error);
      req.flash('error', 'Failed to load users');
      res.redirect('/admin');
    }
  }

  static async deleteUser(req, res) {
    try {
      await UserModel.deleteUser(req.params.id);
      req.flash('success', 'User deleted successfully');
      res.redirect('/admin/users');
    } catch (error) {
      console.error('Delete user error:', error);
      req.flash('error', 'Failed to delete user');
      res.redirect('/admin/users');
    }
  }

  static async updateUserRole(req, res) {
    try {
      const { role } = req.body;
      await UserModel.updateProfile(req.params.id, { role });
      req.flash('success', 'User role updated');
      res.redirect('/admin/users');
    } catch (error) {
      console.error('Update role error:', error);
      req.flash('error', 'Failed to update user role');
      res.redirect('/admin/users');
    }
  }

  static async getListings(req, res) {
    try {
      const [listings] = await pool.query(`
        SELECT ml.*, u.name as farmer_name 
        FROM marketplace_listings ml 
        JOIN users u ON ml.user_id = u.id 
        ORDER BY ml.created_at DESC
      `);
      res.render('admin/listings', {
        title: 'Manage Listings - AgriSense AI',
        listings
      });
    } catch (error) {
      console.error('Admin listings error:', error);
      req.flash('error', 'Failed to load listings');
      res.redirect('/admin');
    }
  }

  static async updateListingStatus(req, res) {
    try {
      const { status } = req.body;
      await CropModel.updateStatus(req.params.id, status);
      req.flash('success', 'Listing status updated');
      res.redirect('/admin/listings');
    } catch (error) {
      console.error('Update listing status error:', error);
      req.flash('error', 'Failed to update listing');
      res.redirect('/admin/listings');
    }
  }
}

module.exports = AdminController;
