// Common Utilities for AC Telemetry
console.log("🏁 AC Telemetry Common JS loaded");

// Theme Management
let theme = localStorage.getItem('theme') || 'dark';

document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
});

function initializeTheme() {
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon();
}

function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.querySelector('.theme-icon');
    if (!icon) return;
    icon.innerHTML = theme === 'dark' ? '☀️' : '🌙';
}

// Format time (ms -> MM:SS.ms)
function formatTime(ms) {
    if (!ms || ms === Infinity) return '--:--.---';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    const milliseconds = Math.floor((totalSeconds % 1) * 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
}

// Session Type Translation
function translateSessionType(type) {
    if (!type) return 'Desconocido';
    const map = {
        'PRACTICE': 'Práctica',
        'QUALIFY': 'Clasificación',
        'RACE': 'Carrera',
        'HOTLAP': 'Hotlap',
        'TIME_ATTACK': 'Time Attack',
        'DRIFT': 'Drift'
    };
    return map[type.toUpperCase()] || type;
}
