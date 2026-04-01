const jwt = require('jsonwebtoken');

function requireAuth(req, res, next) {
  if (!req.session.user) {
    req.flash('error', 'Please login to access this page');
    return res.redirect('/auth/login');
  }

  try {
    const decoded = jwt.verify(req.session.token, process.env.JWT_SECRET);
    req.userId = decoded.id;
    req.userRole = decoded.role;
    next();
  } catch (error) {
    req.session.destroy();
    req.flash('error', 'Session expired. Please login again');
    return res.redirect('/auth/login');
  }
}

function requireAdmin(req, res, next) {
  if (!req.session.user || req.session.user.role !== 'admin') {
    req.flash('error', 'Access denied. Admin privileges required.');
    return res.redirect('/dashboard');
  }
  next();
}

function redirectIfAuth(req, res, next) {
  if (req.session.user) {
    if (req.session.user.role === 'admin') {
      return res.redirect('/admin');
    }
    return res.redirect('/dashboard');
  }
  next();
}

module.exports = { requireAuth, requireAdmin, redirectIfAuth };
