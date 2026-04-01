const CropModel = require('../models/cropModel');
const GeminiService = require('../services/geminiService');

class MarketplaceController {
  static async getMarketplace(req, res) {
    try {
      const filters = {
        crop_name: req.query.crop,
        location: req.query.location,
        min_price: req.query.min_price,
        max_price: req.query.max_price
      };

      const listings = await CropModel.getAllListings(filters);

      res.render('marketplace', {
        title: 'Marketplace - AgriSense AI',
        listings,
        filters: req.query
      });
    } catch (error) {
      console.error('Marketplace error:', error);
      req.flash('error', 'Failed to load marketplace');
      res.redirect('/dashboard');
    }
  }

  static async createListing(req, res) {
    try {
      const { crop_name, quantity, unit, price, description, location } = req.body;
      const image_path = req.file ? `/uploads/crops/${req.file.filename}` : null;

      await CropModel.createListing({
        user_id: req.session.user.id,
        crop_name,
        quantity: parseFloat(quantity),
        unit,
        price: parseFloat(price),
        description,
        image_path,
        location: location || req.session.user.location
      });

      req.flash('success', 'Listing created successfully!');
      res.redirect('/marketplace');
    } catch (error) {
      console.error('Create listing error:', error);
      req.flash('error', 'Failed to create listing');
      res.redirect('/marketplace');
    }
  }

  static async getMyListings(req, res) {
    try {
      const listings = await CropModel.getByUser(req.session.user.id);
      res.render('my-listings', {
        title: 'My Listings - AgriSense AI',
        listings
      });
    } catch (error) {
      console.error('My listings error:', error);
      req.flash('error', 'Failed to load your listings');
      res.redirect('/marketplace');
    }
  }

  static async getListingDetail(req, res) {
    try {
      const listing = await CropModel.getById(req.params.id);
      if (!listing) {
        req.flash('error', 'Listing not found');
        return res.redirect('/marketplace');
      }
      res.render('listing-detail', {
        title: `${listing.crop_name} - AgriSense AI`,
        listing
      });
    } catch (error) {
      console.error('Listing detail error:', error);
      req.flash('error', 'Failed to load listing');
      res.redirect('/marketplace');
    }
  }

  static async updateListing(req, res) {
    try {
      const { crop_name, quantity, unit, price, description, location, status } = req.body;
      await CropModel.updateListing(req.params.id, {
        crop_name, quantity: parseFloat(quantity), unit, price: parseFloat(price),
        description, location, status
      });
      req.flash('success', 'Listing updated successfully');
      res.redirect('/marketplace/my-listings');
    } catch (error) {
      console.error('Update listing error:', error);
      req.flash('error', 'Failed to update listing');
      res.redirect('/marketplace/my-listings');
    }
  }

  static async deleteListing(req, res) {
    try {
      await CropModel.deleteListing(req.params.id);
      req.flash('success', 'Listing deleted');
      res.redirect('/marketplace/my-listings');
    } catch (error) {
      console.error('Delete listing error:', error);
      req.flash('error', 'Failed to delete listing');
      res.redirect('/marketplace/my-listings');
    }
  }

  static async getSuggestedPrice(req, res) {
    try {
      const { crop_name, quantity, location } = req.query;
      const suggestion = await GeminiService.getSuggestedPrice(crop_name, quantity, location);
      res.json({ success: true, suggestion });
    } catch (error) {
      res.json({ success: false, error: 'Failed to get price suggestion' });
    }
  }
}

module.exports = MarketplaceController;
