// Live Dashboard Logic
console.log("🏎️ Live Dashboard JS loaded");

// WebSocket connection
let ws = null;
let reconnectInterval = null;

// Gauge & Chart instances
let speedGaugeChart = null;
const tireElements = {
    fl: document.getElementById('tireFL'),
    fr: document.getElementById('tireFR'),
    rl: document.getElementById('tireRL'),
    rr: document.getElementById('tireRR')
};

// Volante (steering wheel) tracking
let previousSteeringAngle = 0;
let previousAngularVelocity = 0;
let previousTimestamp = 0;
const frequencyBuffer = [];
const FREQUENCY_BUFFER_SIZE = 10;

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    connectWebSocket();
});

// --- Initialization ---

function initCharts() {
    // Speed Gauge (Chart.js Doughnut)
    const ctxSpeed = document.getElementById('speedGauge').getContext('2d');
    speedGaugeChart = new Chart(ctxSpeed, {
        type: 'doughnut',
        data: {
            labels: ['Speed', 'Remaining'],
            datasets: [{
                data: [0, 300],
                backgroundColor: ['#38bdf8', 'rgba(255, 255, 255, 0.1)'],
                borderWidth: 0,
                cutout: '80%',
                circumference: 240,
                rotation: 240
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { tooltip: { enabled: false }, legend: { display: false } },
            animation: { duration: 0 }
        }
    });
}

// --- WebSocket ---

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    ws = new WebSocket(wsUrl);

    ws.onsrc = function () {
        console.log("✅ WebSocket Connected");
        hideDisconnectOverlay();
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };

    ws.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'telemetry_update') {
                updateDashboard(data.data);
            } else if (data.type === 'session_status') {
                // Handle session status (e.g. race finished)
                if (data.status === 'finished') {
                    // Show notification or link to analysis
                }
            }
        } catch (e) {
            console.error("Error parsing WS data", e);
        }
    };

    ws.onclose = function () {
        console.warn("⚠️ WebSocket Disconnected");
        showDisconnectOverlay();
        if (!reconnectInterval) {
            reconnectInterval = setInterval(connectWebSocket, 3000);
        }
    };

    ws.onerror = function (err) {
        console.error("WebSocket Error", err);
        ws.close();
    };
}

// --- Dashboard Updates ---

let currentTrackName = null;

function updateDashboard(data) {
    if (!data) return;

    // Check for track change and trigger comparison chart update
    if (data.track_name && data.track_name !== currentTrackName) {
        currentTrackName = data.track_name;
        console.log(`Track changed to: ${currentTrackName}`);

        // Trigger chart update if function exists (charts.js loaded)
        if (typeof window.loadBestRaceComparison === 'function') {
            window.loadBestRaceComparison(currentTrackName);
        }
    }

    // 1. Numeric Displays
    // Data is now flat structure from reader.py
    updateText('speedValue', Math.round(data.speed));
    updateText('gearDisplay', data.gear === 0 ? 'R' : (data.gear === 1 ? 'N' : data.gear - 1));
    updateText('currentLapTime', formatTime(data.current_lap_time)); // reader sends ms
    updateText('lastLapTime', formatTime(data.last_lap_time));
    updateText('bestLapTime', formatTime(data.best_lap_time));

    // Session Info
    updateText('sessionMode', translateSessionType(data.session_type));

    // Update Track Name display if element exists
    updateText('trackName', data.track_name);

    // 2. Gauges
    if (speedGaugeChart) {
        const speed = Math.round(data.speed);
        speedGaugeChart.data.datasets[0].data = [speed, 300 - speed]; // Assume 300 max
        speedGaugeChart.update();
    }

    // 3. Inputs (Bars)
    // AC sends 0-1 for inputs
    updateBar('throttleBar', data.throttle, 'throttleValue', '%');
    updateBar('brakeBar', data.brake, 'brakeValue', '%');
    updateBar('clutchBar', data.clutch, null, null);

    // Steering
    updateSteering(data.steering);

    // 4. G-Force
    if (data.g_force_lat !== undefined) updateText('gforceLat', data.g_force_lat.toFixed(2));
    if (data.g_force_long !== undefined) updateText('gforceLong', data.g_force_long.toFixed(2));

    // 5. Tires (Temp & Pressure)
    // Reader sends individual fields
    updateTire(tireElements.fl, data.tire_temp_fl, data.tire_pressure_fl);
    updateTire(tireElements.fr, data.tire_temp_fr, data.tire_pressure_fr);
    updateTire(tireElements.rl, data.tire_temp_rl, data.tire_pressure_rl);
    updateTire(tireElements.rr, data.tire_temp_rr, data.tire_pressure_rr);

    // 6. Electronics (New)
    // Update electronics values if elements exist
    updateText('tcLevel', data.tc !== undefined ? data.tc : '--');
    updateText('absLevel', data.abs !== undefined ? data.abs : '--');
    // Map engine brake to 0-12 or similar if needed, reader sends int
    updateText('engineBrakeLevel', data.engine_brake !== undefined ? data.engine_brake : '--');

    // ERS/KERS
    updateText('ersRecovery', data.ers_recovery_level !== undefined ? data.ers_recovery_level : '--');
    updateText('ersMode', data.ers_power_level !== undefined ? data.ers_power_level : '--');

    // Sample Rate
    if (data.sample_frequency) {
        updateText('sampleFreq', Math.round(data.sample_frequency) + ' Hz');
    }
}

// --- Helpers ---

function updateText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function updateBar(id, value, textId, unit) {
    // Value is 0.0 to 1.0 usually
    const el = document.getElementById(id);
    if (el) el.style.width = `${value * 100}%`;

    if (textId) {
        const textEl = document.getElementById(textId);
        if (textEl) textEl.textContent = `${Math.round(value * 100)}${unit}`;
    }
}

function updateSteering(angle) {
    // Normalize steering for display (visual rotation)
    // Assume max rotation is around 450 degrees or 900 total
    const rotation = angle * 50; // Simple scaling
    const el = document.getElementById('steeringBar');
    const valEl = document.getElementById('steeringValue');

    if (el) {
        // Center the bar. 50% is 0 degrees.
        // If generic logic:
        // This depends on the specific CSS implementation of the steering bar (left/right split or simple bar)
        // For now, let's assume it's a simple bar that fills based on absolute value, 
        // or we rotate a wheel icon. 
        // Given the HTML 'input-bar', it's likely a progress bar. 
        // Let's just update the text and a simple indicator.

        // Visual fix: If it's a bar, we usually show magnitude.
        el.style.width = `${Math.abs(angle) * 100}%`; // Fallback
    }
    if (valEl) valEl.textContent = `${Math.round(angle * 57.29)}°`; // Rad to Deg
}

function updateTire(el, temp, press) {
    if (!el) return;
    const tempEl = el.querySelector('.tire-temp');
    const presEl = el.querySelector('.tire-pres');

    if (tempEl) tempEl.textContent = `${Math.round(temp)}°C`;
    if (presEl) presEl.textContent = `${Math.round(press)} psi`;

    // Colorize based on temp
    // Simple logic: Cold < 60, Optimal 60-100, Hot > 100
    el.classList.remove('cold', 'optimal', 'hot');
    if (temp < 60) el.classList.add('cold');
    else if (temp < 100) el.classList.add('optimal');
    else el.classList.add('hot');
}

function showDisconnectOverlay() {
    const overlay = document.getElementById('disconnectOverlay');
    if (overlay) overlay.classList.remove('hidden');
}

function hideDisconnectOverlay() {
    const overlay = document.getElementById('disconnectOverlay');
    if (overlay) overlay.classList.add('hidden');
}
