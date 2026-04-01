const axios = require('axios');

class WeatherService {
  static async getWeatherByCoords(lat, lon) {
    const apiKey = process.env.WEATHER_API_KEY || '4d8fb5b93d4af21d66a2948710284366';
    const url = `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&units=metric&appid=${apiKey}`;
    
    try {
      const response = await axios.get(url, { timeout: 5000 });
      const d = response.data;
      return {
        temp: Math.round(d.main.temp),
        feels_like: Math.round(d.main.feels_like),
        humidity: d.main.humidity,
        description: d.weather[0].description,
        icon: d.weather[0].icon,
        wind: Math.round(d.wind.speed * 3.6),
        city: d.name,
        country: d.sys.country
      };
    } catch (error) {
      console.error('[Weather] API error:', error.message);
      return null;
    }
  }

  static async getWeatherByCity(city) {
    const apiKey = process.env.WEATHER_API_KEY || '4d8fb5b93d4af21d66a2948710284366';
    const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(city)}&units=metric&appid=${apiKey}`;
    
    try {
      const response = await axios.get(url, { timeout: 5000 });
      const d = response.data;
      return {
        temp: Math.round(d.main.temp),
        feels_like: Math.round(d.main.feels_like),
        humidity: d.main.humidity,
        description: d.weather[0].description,
        icon: d.weather[0].icon,
        wind: Math.round(d.wind.speed * 3.6),
        city: d.name,
        country: d.sys.country
      };
    } catch (error) {
      console.error('[Weather] API error:', error.message);
      return null;
    }
  }

  static getIconEmoji(iconCode) {
    const map = {
      '01d': '☀️', '01n': '🌙', '02d': '⛅', '02n': '☁️',
      '03d': '☁️', '03n': '☁️', '04d': '☁️', '04n': '☁️',
      '09d': '🌧️', '09n': '🌧️', '10d': '🌦️', '10n': '🌧️',
      '11d': '⛈️', '11n': '⛈️', '13d': '❄️', '13n': '❄️',
      '50d': '🌫️', '50n': '🌫️'
    };
    return map[iconCode] || '🌤️';
  }
}

module.exports = WeatherService;
