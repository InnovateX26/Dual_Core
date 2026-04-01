const EquipmentModel = require('../models/equipmentModel');

const CATEGORIES = [
  { value: 'tractor', label: 'Tractor / ट्रैक्टर', icon: 'fa-tractor' },
  { value: 'rotavator', label: 'Rotavator / रोटावेटर', icon: 'fa-cog' },
  { value: 'harvester', label: 'Harvester / हार्वेस्टर', icon: 'fa-cut' },
  { value: 'sprayer', label: 'Sprayer / स्प्रेयर', icon: 'fa-spray-can' },
  { value: 'plough', label: 'Plough / हल', icon: 'fa-plow' },
  { value: 'seeder', label: 'Seeder / बीज ड्रिल', icon: 'fa-seedling' },
  { value: 'thresher', label: 'Thresher / थ्रेशर', icon: 'fa-fan' },
  { value: 'pump', label: 'Water Pump / पंप', icon: 'fa-faucet' },
  { value: 'trailer', label: 'Trailer / ट्रॉली', icon: 'fa-truck' },
  { value: 'other', label: 'Other / अन्य', icon: 'fa-tools' },
];

class EquipmentController {

  // ─── PAGE: Browse Equipment ───
  static async browsePage(req, res) {
    try {
      const { category, search, max_distance, page } = req.query;
      const userLat = req.session.user?.lat;
      const userLng = req.session.user?.lng;

      const equipment = await EquipmentModel.browse({
        category, search, maxDistance: max_distance || 50,
        lat: userLat, lng: userLng,
        page: parseInt(page) || 1, limit: 20
      });
      const total = await EquipmentModel.getCount({ category, search });

      res.render('equipment-browse', {
        title: 'Equipment Rental — AgriConnect',
        equipment, categories: CATEGORIES,
        filters: { category: category || 'all', search: search || '', max_distance: max_distance || 50 },
        total, currentPage: parseInt(page) || 1,
        totalPages: Math.ceil(total / 20)
      });
    } catch (error) {
      console.error('Equipment browse error:', error);
      req.flash('error', 'Failed to load equipment');
      res.redirect('/dashboard');
    }
  }

  // ─── PAGE: Equipment Detail ───
  static async detailPage(req, res) {
    try {
      const equip = await EquipmentModel.getById(req.params.id);
      if (!equip) { req.flash('error', 'Equipment not found'); return res.redirect('/equipment'); }

      const blockedDates = await EquipmentModel.getBlockedDates(equip.id);
      const reviews = await EquipmentModel.getReviewsByEquipment(equip.id);
      const trust = await EquipmentModel.getTrustScore(req.session.user.id);

      res.render('equipment-detail', {
        title: `${equip.name} — Equipment Rental`,
        equip, blockedDates, reviews, trust, categories: CATEGORIES
      });
    } catch (error) {
      console.error('Equipment detail error:', error);
      req.flash('error', 'Failed to load equipment details');
      res.redirect('/equipment');
    }
  }

  // ─── PAGE: My Equipment & Bookings ───
  static async myPage(req, res) {
    try {
      const userId = req.session.user.id;
      const myEquipment = await EquipmentModel.getByOwner(userId);
      const myBookings = await EquipmentModel.getBookingsByRenter(userId);
      const incomingBookings = await EquipmentModel.getBookingsByOwner(userId);
      const trust = await EquipmentModel.getTrustScore(userId);

      res.render('equipment-my', {
        title: 'My Equipment — AgriConnect',
        myEquipment, myBookings, incomingBookings, trust, categories: CATEGORIES
      });
    } catch (error) {
      console.error('My equipment error:', error);
      req.flash('error', 'Failed to load your equipment');
      res.redirect('/equipment');
    }
  }

  // ─── API: Add Equipment ───
  static async addEquipment(req, res) {
    try {
      const data = {
        owner_id: req.session.user.id,
        name: req.body.name,
        category: req.body.category,
        description: req.body.description,
        image_path: req.file ? `/uploads/equipment/${req.file.filename}` : null,
        daily_rate: parseFloat(req.body.daily_rate),
        deposit_amount: parseFloat(req.body.deposit_amount) || 0,
        condition_rating: req.body.condition_rating || 'good',
        horsepower: req.body.horsepower,
        brand: req.body.brand,
        year_of_purchase: req.body.year_of_purchase || null,
        lat: req.body.lat || null,
        lng: req.body.lng || null,
        location_text: req.body.location_text,
        auto_approve: req.body.auto_approve === 'on' || req.body.auto_approve === 'true'
      };

      const id = await EquipmentModel.create(data);
      req.flash('success', 'Equipment listed successfully! 🚜');
      res.redirect('/equipment/my-equipment');
    } catch (error) {
      console.error('Add equipment error:', error);
      req.flash('error', 'Failed to add equipment');
      res.redirect('/equipment/my-equipment');
    }
  }

  // ─── API: Update Equipment ───
  static async updateEquipment(req, res) {
    try {
      const data = { ...req.body };
      if (req.file) data.image_path = `/uploads/equipment/${req.file.filename}`;
      delete data._method;
      await EquipmentModel.update(req.params.id, req.session.user.id, data);
      req.flash('success', 'Equipment updated');
      res.redirect('/equipment/my-equipment');
    } catch (error) {
      console.error('Update equipment error:', error);
      req.flash('error', 'Failed to update');
      res.redirect('/equipment/my-equipment');
    }
  }

  // ─── API: Delete Equipment ───
  static async deleteEquipment(req, res) {
    try {
      await EquipmentModel.remove(req.params.id, req.session.user.id);
      req.flash('success', 'Equipment removed');
      res.redirect('/equipment/my-equipment');
    } catch (error) {
      console.error('Delete equipment error:', error);
      res.redirect('/equipment/my-equipment');
    }
  }

  // ─── API: Book Equipment ───
  static async bookEquipment(req, res) {
    try {
      const equip = await EquipmentModel.getById(req.params.id);
      if (!equip) return res.json({ success: false, error: 'Equipment not found' });
      if (equip.owner_id === req.session.user.id) return res.json({ success: false, error: 'You cannot book your own equipment' });

      const trust = await EquipmentModel.getTrustScore(req.session.user.id);
      if (trust.trust_score < 20) return res.json({ success: false, error: 'Your trust score is too low. Please build trust by lending equipment first.' });

      const startDate = new Date(req.body.start_date);
      const endDate = new Date(req.body.end_date);
      if (endDate < startDate) return res.json({ success: false, error: 'End date must be after start date' });

      const totalDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
      const totalCost = totalDays * equip.daily_rate;
      const depositPaid = trust.deposit_required ? equip.deposit_amount : 0;

      const result = await EquipmentModel.createBooking({
        equipment_id: equip.id,
        renter_id: req.session.user.id,
        owner_id: equip.owner_id,
        start_date: req.body.start_date,
        end_date: req.body.end_date,
        total_days: totalDays,
        total_cost: totalCost,
        deposit_paid: depositPaid,
        renter_notes: req.body.renter_notes,
        auto_approve: equip.auto_approve
      });

      if (result.error) return res.json({ success: false, error: result.error });

      res.json({
        success: true,
        booking: {
          id: result.bookingId,
          status: result.status,
          total_days: totalDays,
          total_cost: totalCost,
          deposit_required: depositPaid,
          message: result.status === 'approved' ? 'Booking confirmed! ✅' : 'Booking request sent. Waiting for owner approval. ⏳'
        }
      });
    } catch (error) {
      console.error('Book equipment error:', error);
      res.json({ success: false, error: 'Failed to create booking' });
    }
  }

  // ─── API: Approve/Reject/Complete Booking ───
  static async approveBooking(req, res) {
    try {
      await EquipmentModel.updateBookingStatus(req.params.id, req.session.user.id, 'approved', req.body.notes);
      req.flash('success', 'Booking approved ✅');
      res.redirect('/equipment/my-equipment');
    } catch (error) { console.error(error); res.redirect('/equipment/my-equipment'); }
  }

  static async rejectBooking(req, res) {
    try {
      await EquipmentModel.updateBookingStatus(req.params.id, req.session.user.id, 'rejected', req.body.notes);
      req.flash('success', 'Booking rejected');
      res.redirect('/equipment/my-equipment');
    } catch (error) { console.error(error); res.redirect('/equipment/my-equipment'); }
  }

  static async completeBooking(req, res) {
    try {
      await EquipmentModel.updateBookingStatus(req.params.id, req.session.user.id, 'completed', req.body.notes);
      // Recalculate trust scores for both parties
      const booking = await EquipmentModel.getBookingById(req.params.id);
      if (booking) {
        await EquipmentModel.recalcTrustScore(booking.renter_id);
        await EquipmentModel.recalcTrustScore(booking.owner_id);
      }
      req.flash('success', 'Equipment returned. Booking completed! 🎉');
      res.redirect('/equipment/my-equipment');
    } catch (error) { console.error(error); res.redirect('/equipment/my-equipment'); }
  }

  // ─── API: Submit Review ───
  static async submitReview(req, res) {
    try {
      const booking = await EquipmentModel.getBookingById(req.params.id);
      if (!booking || booking.status !== 'completed') return res.json({ success: false, error: 'Can only review completed bookings' });

      const isRenter = booking.renter_id === req.session.user.id;
      await EquipmentModel.createReview({
        booking_id: booking.id,
        equipment_id: booking.equipment_id,
        reviewer_id: req.session.user.id,
        reviewed_user_id: isRenter ? booking.owner_id : booking.renter_id,
        rating: parseInt(req.body.rating),
        review_text: req.body.review_text,
        review_type: isRenter ? 'renter_to_owner' : 'owner_to_renter'
      });

      // Recalculate trust scores
      await EquipmentModel.recalcTrustScore(booking.renter_id);
      await EquipmentModel.recalcTrustScore(booking.owner_id);

      res.json({ success: true, message: 'Review submitted! ⭐' });
    } catch (error) {
      console.error('Review error:', error);
      res.json({ success: false, error: 'Failed to submit review' });
    }
  }

  // ─── API: Toggle Availability ───
  static async toggleAvailability(req, res) {
    try {
      const equip = await EquipmentModel.getById(req.params.id);
      if (!equip || equip.owner_id !== req.session.user.id) return res.redirect('/equipment/my-equipment');
      await EquipmentModel.update(req.params.id, req.session.user.id, { is_available: !equip.is_available });
      req.flash('success', equip.is_available ? 'Equipment paused' : 'Equipment is now available');
      res.redirect('/equipment/my-equipment');
    } catch (error) { console.error(error); res.redirect('/equipment/my-equipment'); }
  }
}

module.exports = EquipmentController;
