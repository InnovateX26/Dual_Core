const UserModel = require('../models/userModel');
const jwt = require('jsonwebtoken');

class AuthController {
  static async getLogin(req, res) {
    res.render('auth/login', { title: 'Login - AgriSense AI' });
  }

  static async postLogin(req, res) {
    try {
      const { email, password } = req.body;

      if (!email || !password) {
        req.flash('error', 'Please provide email and password');
        return res.redirect('/auth/login');
      }

      const user = await UserModel.findByEmail(email);
      if (!user) {
        req.flash('error', 'Invalid email or password');
        return res.redirect('/auth/login');
      }

      const isMatch = await UserModel.verifyPassword(password, user.password);
      if (!isMatch) {
        req.flash('error', 'Invalid email or password');
        return res.redirect('/auth/login');
      }

      const token = jwt.sign(
        { id: user.id, role: user.role },
        process.env.JWT_SECRET,
        { expiresIn: '24h' }
      );

      req.session.token = token;
      req.session.user = {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        phone: user.phone,
        location: user.location
      };

      req.flash('success', `Welcome back, ${user.name}!`);

      if (user.role === 'admin') {
        return res.redirect('/admin');
      }
      return res.redirect('/dashboard');

    } catch (error) {
      console.error('Login error:', error);
      req.flash('error', 'An error occurred during login');
      return res.redirect('/auth/login');
    }
  }

  static async getRegister(req, res) {
    res.render('auth/register', { title: 'Register - AgriSense AI' });
  }

  static async postRegister(req, res) {
    try {
      const { name, email, phone, password, confirmPassword, location } = req.body;

      // Validation
      if (!name || !email || !password) {
        req.flash('error', 'Please fill in all required fields');
        return res.redirect('/auth/register');
      }

      if (password.length < 6) {
        req.flash('error', 'Password must be at least 6 characters');
        return res.redirect('/auth/register');
      }

      if (password !== confirmPassword) {
        req.flash('error', 'Passwords do not match');
        return res.redirect('/auth/register');
      }

      const existingUser = await UserModel.findByEmail(email);
      if (existingUser) {
        req.flash('error', 'Email already registered');
        return res.redirect('/auth/register');
      }

      await UserModel.create({ name, email, phone, password, location });

      req.flash('success', 'Registration successful! Please login.');
      return res.redirect('/auth/login');

    } catch (error) {
      console.error('Register error:', error);
      req.flash('error', 'An error occurred during registration');
      return res.redirect('/auth/register');
    }
  }

  static async logout(req, res) {
    req.session.destroy((err) => {
      if (err) console.error('Logout error:', err);
      res.redirect('/');
    });
  }
}

module.exports = AuthController;
