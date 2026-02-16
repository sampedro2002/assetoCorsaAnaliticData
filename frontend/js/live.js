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

function updateDashboard(data) {
    if (!data) return;

    // 1. Numeric Displays
    updateText('speedValue', Math.round(data.physics.speedKmh));
    updateText('gearDisplay', data.physics.gear === 0 ? 'R' : (data.physics.gear === 1 ? 'N' : data.physics.gear - 1));
    updateText('currentLapTime', data.graphics.currentTime);
    updateText('lastLapTime', data.graphics.lastTime);
    updateText('bestLapTime', data.graphics.bestTime);

    // Session Info
    updateText('sessionMode', translateSessionType(data.graphics.session));
    // Additional session info
    // NOTE: The backend might need to send track/car names in the realtime packet 
    // or we fetch them separately. For now, we assume they might be in static data or ignored.

    // 2. Gauges
    if (speedGaugeChart) {
        const speed = Math.round(data.physics.speedKmh);
        speedGaugeChart.data.datasets[0].data = [speed, 300 - speed];
        speedGaugeChart.update();
    }

    // 3. Inputs (Bars)
    updateBar('throttleBar', data.physics.gas, 'throttleValue', '%');
    updateBar('brakeBar', data.physics.brake, 'brakeValue', '%');
    updateBar('clutchBar', data.physics.clutch, null, null);

    // Steering
    const steeringAngle = data.physics.steerAngle;
    updateSteering(steeringAngle);

    // 4. G-Force
    updateText('gforceLat', data.physics.gG[0].toFixed(2));
    updateText('gforceLong', data.physics.gG[2].toFixed(2));

    // 5. Tires (Temp & Pressure)
    updateTire(tireElements.fl, data.physics.tyreCoreTemp[0], data.physics.wheelsPressure[0]);
    updateTire(tireElements.fr, data.physics.tyreCoreTemp[1], data.physics.wheelsPressure[1]);
    updateTire(tireElements.rl, data.physics.tyreCoreTemp[2], data.physics.wheelsPressure[2]);
    updateTire(tireElements.rr, data.physics.tyreCoreTemp[3], data.physics.wheelsPressure[3]);
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
