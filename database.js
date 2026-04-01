const mysql = require('mysql2/promise');
require('dotenv').config();

const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

async function initializeDatabase() {
  const connection = await pool.getConnection();
  try {
    // Users table
    await connection.query(`
      CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        phone VARCHAR(15),
        password VARCHAR(255) NOT NULL,
        role ENUM('farmer', 'admin') DEFAULT 'farmer',
        location VARCHAR(255),
        avatar VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
      )
    `);

    // Disease scans table
    await connection.query(`
      CREATE TABLE IF NOT EXISTS disease_scans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        image_path VARCHAR(255) NOT NULL,
        disease_name VARCHAR(100),
        confidence FLOAT,
        crop_type VARCHAR(50),
        description TEXT,
        treatment TEXT,
        prevention TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Crop marketplace listings
    await connection.query(`
      CREATE TABLE IF NOT EXISTS marketplace_listings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        crop_name VARCHAR(100) NOT NULL,
        quantity FLOAT NOT NULL,
        unit VARCHAR(20) DEFAULT 'kg',
        price FLOAT NOT NULL,
        description TEXT,
        image_path VARCHAR(255),
        location VARCHAR(255),
        status ENUM('active', 'sold', 'pending', 'rejected') DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Risk assessments
    await connection.query(`
      CREATE TABLE IF NOT EXISTS risk_assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        crop_type VARCHAR(50),
        risk_score FLOAT,
        risk_level VARCHAR(20),
        weather_factor FLOAT,
        soil_factor FLOAT,
        disease_factor FLOAT,
        market_factor FLOAT,
        recommendations TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Yield predictions
    await connection.query(`
      CREATE TABLE IF NOT EXISTS yield_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        crop_type VARCHAR(50),
        area FLOAT,
        predicted_yield FLOAT,
        unit VARCHAR(20) DEFAULT 'quintals',
        season VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Chat history
    await connection.query(`
      CREATE TABLE IF NOT EXISTS chat_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Add lat/lng to users if not exists
    try {
      await connection.query(`ALTER TABLE users ADD COLUMN lat DECIMAL(10,8) NULL`);
      await connection.query(`ALTER TABLE users ADD COLUMN lng DECIMAL(11,8) NULL`);
    } catch (e) { /* columns already exist */ }

    // Equipment listings
    await connection.query(`
      CREATE TABLE IF NOT EXISTS equipment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        owner_id INT NOT NULL,
        name VARCHAR(150) NOT NULL,
        category ENUM('tractor','rotavator','harvester','sprayer','plough','seeder','thresher','pump','trailer','other') NOT NULL,
        description TEXT,
        image_path VARCHAR(255),
        daily_rate FLOAT NOT NULL,
        deposit_amount FLOAT DEFAULT 0,
        condition_rating ENUM('new','good','fair','worn') DEFAULT 'good',
        horsepower VARCHAR(20),
        brand VARCHAR(100),
        year_of_purchase YEAR,
        lat DECIMAL(10, 8),
        lng DECIMAL(11, 8),
        location_text VARCHAR(255),
        auto_approve BOOLEAN DEFAULT FALSE,
        is_available BOOLEAN DEFAULT TRUE,
        status ENUM('active','paused','removed') DEFAULT 'active',
        total_bookings INT DEFAULT 0,
        avg_rating FLOAT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Equipment bookings
    await connection.query(`
      CREATE TABLE IF NOT EXISTS equipment_bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        equipment_id INT NOT NULL,
        renter_id INT NOT NULL,
        owner_id INT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_days INT NOT NULL,
        total_cost FLOAT NOT NULL,
        deposit_paid FLOAT DEFAULT 0,
        status ENUM('pending','approved','rejected','active','completed','cancelled','disputed') DEFAULT 'pending',
        renter_notes TEXT,
        owner_notes TEXT,
        approved_at TIMESTAMP NULL,
        pickup_at TIMESTAMP NULL,
        returned_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
        FOREIGN KEY (renter_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Equipment reviews
    await connection.query(`
      CREATE TABLE IF NOT EXISTS equipment_reviews (
        id INT AUTO_INCREMENT PRIMARY KEY,
        booking_id INT NOT NULL,
        equipment_id INT NOT NULL,
        reviewer_id INT NOT NULL,
        reviewed_user_id INT NOT NULL,
        rating INT NOT NULL,
        review_text TEXT,
        review_type ENUM('renter_to_owner','owner_to_renter') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES equipment_bookings(id) ON DELETE CASCADE,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Equipment blocked dates (availability calendar)
    await connection.query(`
      CREATE TABLE IF NOT EXISTS equipment_blocked_dates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        equipment_id INT NOT NULL,
        blocked_date DATE NOT NULL,
        reason ENUM('booking','maintenance','unavailable') DEFAULT 'booking',
        booking_id INT NULL,
        UNIQUE KEY uq_equip_date (equipment_id, blocked_date),
        FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
      )
    `);

    // Farmer trust scores
    await connection.query(`
      CREATE TABLE IF NOT EXISTS farmer_trust_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        trust_score FLOAT DEFAULT 50,
        total_rentals INT DEFAULT 0,
        completed_rentals INT DEFAULT 0,
        cancelled_rentals INT DEFAULT 0,
        avg_rating_given FLOAT DEFAULT 0,
        avg_rating_received FLOAT DEFAULT 0,
        deposit_required BOOLEAN DEFAULT FALSE,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    console.log('✅ Database tables initialized successfully (including equipment sharing)');
  } catch (error) {
    console.error('❌ Database initialization error:', error.message);
    throw error;
  } finally {
    connection.release();
  }
}

module.exports = { pool, initializeDatabase };
