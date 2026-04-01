// AgriConnect — Main JavaScript
// Weather, Animations, Voice Support, Utilities

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flash messages
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 300);
    }, 4000);
  });

  // Load weather via geolocation
  loadWeather();

  // Animate feed cards on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.feed-card, .stat-card, .card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'all 0.5s ease';
    observer.observe(el);
  });
});

// Sidebar toggle
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.querySelector('.hamburger');
  if (sidebar && sidebar.classList.contains('open') &&
    !sidebar.contains(e.target) && hamburger && !hamburger.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// === Weather ===
async function loadWeather() {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        const res = await fetch(`/api/weather?lat=${latitude}&lon=${longitude}`);
        const json = await res.json();
        if (json.success) updateWeatherUI(json.data);
      },
      async () => {
        // Fallback to Delhi
        const res = await fetch('/api/weather?city=New Delhi');
        const json = await res.json();
        if (json.success) updateWeatherUI(json.data);
      },
      { timeout: 5000 }
    );
  }
}

function updateWeatherUI(w) {
  // Navbar mini
  const navMini = document.getElementById('weatherMini');
  const navTemp = document.getElementById('navTemp');
  if (navMini && navTemp) {
    navTemp.textContent = w.temp + '°C';
    navMini.style.display = 'flex';
  }
  // Full widget
  const el = (id) => document.getElementById(id);
  if (el('weatherIcon')) el('weatherIcon').textContent = w.iconEmoji || '🌤️';
  if (el('weatherTemp')) el('weatherTemp').textContent = w.temp + '°C';
  if (el('weatherDesc')) el('weatherDesc').textContent = w.description;
  if (el('weatherCity')) el('weatherCity').textContent = w.city + ', ' + w.country;
  if (el('weatherHum')) el('weatherHum').textContent = w.humidity + '%';
  if (el('weatherWind')) el('weatherWind').textContent = w.wind + ' km/h';
}

// === Markdown to HTML converter ===
function mdToHtml(text) {
  if (!text) return '';
  let html = text
    // Code blocks
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Unordered lists
    .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Line breaks
    .replace(/\n/g, '<br>');
  // Wrap consecutive <li> in <ul>
  html = html.replace(/((<li>.*?<\/li>)(<br>)?)+/g, (match) => {
    return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
  });
  return html;
}

// Form data helper
function getFormData(formId) {
  const form = document.getElementById(formId);
  if (!form) return {};
  return Object.fromEntries(new FormData(form));
}
