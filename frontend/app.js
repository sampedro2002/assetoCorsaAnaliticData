// Dashboard Application Logic
console.log("🏁 Assetto Corsa Dashboard v3.29 (Normalized Steering Fix) loaded");

// WebSocket connection
let ws = null;
let reconnectInterval = null;

// Current state
let currentView = 'live';
window.currentSessionId = null;
let theme = localStorage.getItem('theme') || 'dark';
let currentLapNumber = 1;
// Track map renderer (not used for live tracking anymore)
let trackMapRenderer = null;

// Volante (steering wheel) tracking for live view
let previousSteeringAngle = 0;
let previousAngularVelocity = 0;
let previousTimestamp = 0;
let frequencyBuffer = [];
const FREQUENCY_BUFFER_SIZE = 10;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeEventListeners();
    // Render empty analysis containers immediately
    displaySectionAnalysis([]);
    connectWebSocket();
});

// Theme Management
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

    if (theme === 'dark') {
        // Sun icon for switching to light mode
        icon.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2" fill="currentColor" opacity="0.8"/>
                <path d="M12 2V4M12 20V22M22 12H20M4 12H2M19.07 4.93L17.66 6.34M6.34 17.66L4.93 19.07M19.07 19.07L17.66 17.66M6.34 6.34L4.93 4.93" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
            </svg>
        `;
    } else {
        // Moon icon for switching to dark mode
        icon.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" opacity="0.8"/>
            </svg>
        `;
    }
}

// Event Listeners
function initializeEventListeners() {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('backButton').addEventListener('click', () => switchView('live'));
    document.getElementById('analysisButton').addEventListener('click', () => switchView('analysis'));

    // History View Listeners
    const historyBtn = document.getElementById('historyButton');
    if (historyBtn) historyBtn.addEventListener('click', () => switchView('history'));

    const historyBtnAnalysis = document.getElementById('historyButtonAnalysis');
    if (historyBtnAnalysis) historyBtnAnalysis.addEventListener('click', () => {
        const trackElement = document.getElementById('summaryTrack');
        const trackName = trackElement ? trackElement.textContent : null;
        switchView('history', trackName && trackName !== '--' ? trackName : null);
    });

    const historyBtnAnalysisBottom = document.getElementById('historyButtonAnalysisBottom');
    if (historyBtnAnalysisBottom) historyBtnAnalysisBottom.addEventListener('click', () => {
        const trackElement = document.getElementById('summaryTrack');
        const trackName = trackElement ? trackElement.textContent : null;
        switchView('history', trackName && trackName !== '--' ? trackName : null);
    });

    const backHistoryBtn = document.getElementById('backFromHistoryButton');
    if (backHistoryBtn) backHistoryBtn.addEventListener('click', () => switchView('live'));

    const changeTrackBtn = document.getElementById('changeTrackButton');
    if (changeTrackBtn) changeTrackBtn.addEventListener('click', () => {
        document.getElementById('trackSelectionContainer').classList.remove('hidden');
        document.getElementById('trackHistoryDashboard').classList.add('hidden');
    });

    const showTrackListBtn = document.getElementById('showTrackListButton');
    if (showTrackListBtn) showTrackListBtn.addEventListener('click', showTrackList);
}

// View Management
function switchView(view, trackName = null) {
    currentView = view;

    // Hide all views first
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));

    // Update active button state
    document.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(view + 'Button');
    if (activeBtn) activeBtn.classList.add('active');

    if (view === 'live') {
        document.getElementById('liveView').classList.add('active');
    } else if (view === 'analysis') {
        document.getElementById('analysisView').classList.add('active');
        hideDisconnectOverlay();
    } else if (view === 'history') {
        document.getElementById('historyView').classList.add('active');
        hideDisconnectOverlay();

        // If trackName is provided, select it automatically
        if (trackName) {
            selectTrack(trackName);
        } else {
            // If no track provided, auto-load history
            loadHistoryTracks();
        }
    }
}

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    updateConnectionStatus('Conectando...', false);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('✓ WebSocket connected');
        updateConnectionStatus('Esperando Juego...', false);
        clearInterval(reconnectInterval);
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleMessage(message);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('Error', false);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus('Desconectado', false);

        // Attempt reconnection
        reconnectInterval = setInterval(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
        }, 3000);
    };
}

function updateConnectionStatus(text, connected) {
    const statusText = document.querySelector('.status-text');
    const statusDot = document.querySelector('.status-dot');

    statusText.textContent = text;

    if (connected) {
        statusDot.classList.add('connected');
    } else {
        statusDot.classList.remove('connected');
    }
}

// Message Handling
function handleMessage(message) {
    switch (message.type) {
        case 'ac_connected':
            hideDisconnectOverlay();
            updateConnectionStatus('Juego Conectado', true);
            break;
        case 'ac_disconnected':
            showDisconnectOverlay();
            updateConnectionStatus('Juego Desconectado', false);
            break;
        case 'race_start':
            updateConnectionStatus('En Carrera', true);
            window.currentSessionId = message.data.id || message.data.session_id;
            handleRaceStart(message.data);
            break;
        case 'telemetry':
            // Ensure status is green if we are receiving telemetry
            const statusText = document.querySelector('.status-text').textContent;
            if (statusText === 'Esperando Juego...' || statusText === 'Juego Desconectado') {
                updateConnectionStatus('Juego Conectado', true);
            }
            updateTelemetry(message.data);
            break;
        case 'lap_complete':
            console.log('✓ Lap completed:', message.data);

            // Use lap number from backend (backend sends 0-indexed, we display as 1-indexed)
            currentLapNumber = message.data.lap_number + 1;
            updateLapDisplay();
            break;
        case 'race_end':
            updateConnectionStatus('Sesión Finalizada', true);
            handleRaceEnd(message.data);
            break;

    }
}

function showDisconnectOverlay() {
    document.getElementById('disconnectOverlay').classList.remove('hidden');
    console.log('⚠️ AC disconnected - showing overlay');
}

function hideDisconnectOverlay() {
    document.getElementById('disconnectOverlay').classList.add('hidden');
    console.log('✓ AC connected - hiding overlay');
}

function handleRaceStart(data) {
    console.log('🏁 Race started:', data);
    window.currentSessionId = data.session_id;
    currentLapNumber = 0; // Show completed laps: starts at 0
    updateLapDisplay();

    // Hide analysis/other views, show live dashboard
    switchView('live');

    // Update session info
    document.getElementById('trackName').textContent = data.track;
    document.getElementById('carName').textContent = data.car;
}

function updateLapDisplay() {
    const lapEl = document.getElementById('currentLapNumber');
    if (lapEl) {
        lapEl.textContent = currentLapNumber;
    }
}

function updateTelemetry(data) {
    // Update session mode if available
    if (data.session_type) {
        const sessionMode = document.getElementById('sessionMode');
        sessionMode.textContent = data.session_type;
        sessionMode.className = 'session-mode ' + data.session_type.toLowerCase();
    }

    // Speed
    document.getElementById('speedValue').textContent = Math.round(data.speed);

    // RPM
    document.getElementById('rpmValue').textContent = data.rpm;

    // Gear
    const gearDisplay = document.getElementById('gearDisplay');
    if (data.gear === 0) {
        gearDisplay.textContent = 'R';
    } else if (data.gear === 1) {
        gearDisplay.textContent = 'N';
    } else {
        gearDisplay.textContent = data.gear - 1;
    }

    // G-Forces
    document.getElementById('gforceLat').textContent = data.g_force_lat.toFixed(2);
    document.getElementById('gforceLong').textContent = data.g_force_long.toFixed(2);

    // Lap Times
    document.getElementById('currentLapTime').textContent = formatTime(data.current_lap_time);
    document.getElementById('lastLapTime').textContent = formatTime(data.last_lap_time);
    document.getElementById('bestLapTime').textContent = formatTime(data.best_lap_time);

    // Delta (simplified - would need more complex calculation)
    const delta = data.current_lap_time - data.best_lap_time;
    const deltaElement = document.getElementById('deltaTime');
    if (delta > 0) {
        deltaElement.textContent = `+${(delta / 1000).toFixed(3)}`;
        deltaElement.classList.add('positive');
        deltaElement.classList.remove('negative');
    } else {
        deltaElement.textContent = (delta / 1000).toFixed(3);
        deltaElement.classList.add('negative');
        deltaElement.classList.remove('positive');
    }

    // Inputs
    updateInputBar('throttle', data.throttle * 100);
    updateInputBar('brake', data.brake * 100);
    updateSteeringBar(data.steering);

    // Fuel
    const maxFuel = data.max_fuel || 100;
    const fuelPercent = (data.fuel / maxFuel) * 100;
    document.getElementById('fuelBar').style.width = `${fuelPercent}%`;
    document.getElementById('fuelValue').textContent = `${data.fuel.toFixed(1)} L`;

    // Tires
    updateTireTemp('FL', data.tire_temp_fl);
    updateTireTemp('FR', data.tire_temp_fr);
    updateTireTemp('RL', data.tire_temp_rl);
    updateTireTemp('RR', data.tire_temp_rr);

    // Tire Pressures
    document.getElementById('pressureFL').textContent = data.tire_pressure_fl.toFixed(1);
    document.getElementById('pressureFR').textContent = data.tire_pressure_fr.toFixed(1);
    document.getElementById('pressureRL').textContent = data.tire_pressure_rl.toFixed(1);
    document.getElementById('pressureRR').textContent = data.tire_pressure_rr.toFixed(1);

    // Brakes
    updateBrakeTemp('FL', data.brake_temp_fl);
    updateBrakeTemp('FR', data.brake_temp_fr);
    updateBrakeTemp('RL', data.brake_temp_rl);
    updateBrakeTemp('RR', data.brake_temp_rr);

    // Volante (Steering Wheel) Calculations
    const currentTimestamp = data.timestamp || Date.now() / 1000;
    const currentSteeringAngle = data.steering; // Already in degrees from AC

    if (previousTimestamp > 0) {
        const deltaTime = currentTimestamp - previousTimestamp;

        if (deltaTime > 0) {
            // Calculate angular velocity (degrees per second)
            const angularVelocity = (currentSteeringAngle - previousSteeringAngle) / deltaTime;

            // Calculate angular acceleration (degrees per second squared)
            const angularAcceleration = (angularVelocity - previousAngularVelocity) / deltaTime;

            // Calculate sample frequency (Hz)
            const sampleFrequency = 1.0 / deltaTime;

            // Update frequency buffer for averaging
            frequencyBuffer.push(sampleFrequency);
            if (frequencyBuffer.length > FREQUENCY_BUFFER_SIZE) {
                frequencyBuffer.shift();
            }
            const avgFrequency = frequencyBuffer.reduce((a, b) => a + b, 0) / frequencyBuffer.length;

            // Update volante display
            document.getElementById('steeringAngle').textContent = `${currentSteeringAngle.toFixed(1)}°`;
            document.getElementById('angularVelocity').textContent = `${angularVelocity.toFixed(1)}°/s`;
            document.getElementById('angularAcceleration').textContent = `${angularAcceleration.toFixed(1)}°/s²`;
            document.getElementById('brakePct').textContent = `${(data.brake * 100).toFixed(1)}%`;
            document.getElementById('throttlePct').textContent = `${(data.throttle * 100).toFixed(1)}%`;
            document.getElementById('sampleFreq').textContent = `${avgFrequency.toFixed(0)} Hz`;

            // Update previous values
            previousAngularVelocity = angularVelocity;
        }
    }

    previousSteeringAngle = currentSteeringAngle;
    previousTimestamp = currentTimestamp;
}

function updateInputBar(type, value) {
    const bar = document.getElementById(`${type}Bar`);
    const valueElement = document.getElementById(`${type}Value`);

    bar.style.width = `${value}%`;
    valueElement.textContent = `${Math.round(value)}%`;
}

function updateSteeringBar(angle) {
    const bar = document.getElementById('steeringBar');
    const valueElement = document.getElementById('steeringValue');

    // Convert angle to percentage (-1 to 1 -> 0% to 100%)
    const percent = ((angle + 1) / 2) * 100;
    bar.style.left = `${percent}%`;

    valueElement.textContent = `${Math.round(angle * 90)}°`;
}

function updateTireTemp(position, temp) {
    const element = document.getElementById(`tire${position}`);
    const tempElement = element.querySelector('.tire-temp');

    tempElement.textContent = Math.round(temp);

    // Color coding
    element.classList.remove('cold', 'optimal', 'hot');
    if (temp < 75) {
        element.classList.add('cold');
    } else if (temp >= 75 && temp <= 95) {
        element.classList.add('optimal');
    } else {
        element.classList.add('hot');
    }
}

function updateBrakeTemp(position, temp) {
    const element = document.getElementById(`brake${position}`);
    const tempElement = element.querySelector('.brake-temp');

    tempElement.textContent = Math.round(temp);

    // Color coding
    element.classList.remove('cold', 'optimal', 'hot');
    if (temp < 200) {
        element.classList.add('cold');
    } else if (temp >= 200 && temp <= 400) {
        element.classList.add('optimal');
    } else {
        element.classList.add('hot');
    }
}

function handleLapComplete(data) {
    console.log('✓ Lap completed:', data);

    // Could show a notification or update lap counter
}

function handleRaceEnd(data) {
    console.log('🏁 Race ended:', data);
    window.currentSessionId = data.session_id;

    // Load analysis data
    loadAnalysis(data.session_id, data.analysis);

    // Switch to analysis view
    switchView('analysis');
}

async function loadAnalysis(sessionId, analysis) {
    // Update session summary
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        const sessionData = await response.json();

        // Update session type badge
        const sessionTypeBadge = document.getElementById('summarySessionType');
        sessionTypeBadge.textContent = sessionData.session.session_type || 'Unknown';
        sessionTypeBadge.className = 'value session-type-badge ' + (sessionData.session.session_type || 'unknown').toLowerCase();

        document.getElementById('summaryTrack').textContent = sessionData.session.track_name;
        document.getElementById('summaryCar').textContent = sessionData.session.car_name;
        document.getElementById('summaryLaps').textContent = sessionData.session.total_laps;
        document.getElementById('summaryBestLap').textContent = formatTime(sessionData.session.best_lap_time * 1000);

        // Load laps table
        loadLapsTable(sessionData.laps);

        // Display personal records
        if (analysis && analysis.personal_records) {
            displayPersonalRecords(
                analysis.personal_records,
                analysis.records_broken,
                sessionData.session.best_lap_time,
                sessionData.laps[0] // best lap from session
            );
        }

    } catch (error) {
        console.error('Error cargando datos de sesión:', error);
    }

    // Display analysis alert if incomplete or has recommendations
    const alertEl = document.getElementById('analysisAlert');
    const alertMsg = document.getElementById('analysisAlertMessage');

    if (alertEl && alertMsg) {
        if (analysis && analysis.analysis_complete === false) {
            alertEl.classList.remove('hidden');
            alertMsg.textContent = (analysis.recommendations && analysis.recommendations[0]) || 'El análisis de esta sesión está incompleto o faltan datos.';
        } else {
            alertEl.classList.add('hidden');
        }
    }

    // Display recommendations
    if (analysis && analysis.recommendations && analysis.analysis_complete !== false) {
        displayRecommendations(analysis.recommendations);
    }

    // Load and display official track map
    const trackMapImg = document.getElementById('trackMapImage');
    const trackMapLoading = document.getElementById('trackMapLoading');

    if (analysis && analysis.track_map_image) {
        trackMapImg.src = `data:image/png;base64,${analysis.track_map_image}`;
        trackMapImg.style.display = 'block';
        trackMapLoading.style.display = 'none';
    } else {
        trackMapLoading.textContent = 'Mapa del circuito no disponible';
        console.warn('Track map image not available in analysis');
    }

    // Load Volante Stats
    try {
        const volanteResponse = await fetch(`/api/sessions/${sessionId}/volante`);
        if (volanteResponse.ok) {
            const volanteData = await volanteResponse.json();
            if (volanteData.stats) {
                if (volanteData.stats.max_steering_angle !== undefined && volanteData.stats.max_steering_angle !== null) {
                    document.getElementById('maxSteeringAngle').textContent = `${Number(volanteData.stats.max_steering_angle).toFixed(1)}°`;
                }
                if (volanteData.stats.max_angular_velocity !== undefined && volanteData.stats.max_angular_velocity !== null) {
                    document.getElementById('maxAngularVelocity').textContent = `${Number(volanteData.stats.max_angular_velocity).toFixed(1)}°/s`;
                }
                if (volanteData.stats.max_angular_acceleration !== undefined && volanteData.stats.max_angular_acceleration !== null) {
                    document.getElementById('maxAngularAcceleration').textContent = `${Number(volanteData.stats.max_angular_acceleration).toFixed(1)}°/s²`;
                }
                if (volanteData.stats.avg_brake_percentage !== undefined && volanteData.stats.avg_brake_percentage !== null) {
                    document.getElementById('avgBrakeUsage').textContent = `${Number(volanteData.stats.avg_brake_percentage).toFixed(1)}%`;
                }
            }
        }
    } catch (e) {
        console.error('Error loading volante stats:', e);
    }

    // Display section analysis (Independent of map)
    if (analysis && analysis.track_sections) {
        displaySectionAnalysis(analysis.track_sections, analysis.section_records || []);
    } else {
        // Even if no sections found, verify display shows placeholders
        displaySectionAnalysis([], []);
    }

    // Explicitly load chart data
    if (window.loadChartData) {
        console.log('Loading chart data for session:', sessionId);
        window.loadChartData(sessionId);
    }
}

function displayPersonalRecords(records, recordsBroken, currentLapTime, bestLap) {
    // Check if elements exist before trying to update them
    const recordBestLapEl = document.getElementById('recordBestLap');
    if (recordBestLapEl && records && records.best_lap_time) {
        recordBestLapEl.textContent = formatTime(records.best_lap_time * 1000);
    }

    // Calculate and display delta
    const lapDeltaEl = document.getElementById('recordLapDelta');
    if (lapDeltaEl && records && records.best_lap_time && currentLapTime) {
        const lapDelta = currentLapTime - records.best_lap_time;
        if (Math.abs(lapDelta) < 0.001) {
            lapDeltaEl.textContent = '🏆 Récord actual';
            lapDeltaEl.className = 'delta record';
        } else if (lapDelta > 0) {
            lapDeltaEl.textContent = `+${lapDelta.toFixed(3)}s`;
            lapDeltaEl.className = 'delta positive';
        } else {
            lapDeltaEl.textContent = `${lapDelta.toFixed(3)}s`;
            lapDeltaEl.className = 'delta negative';
        }
    }

    // Display sector records with null checks
    ['sector1', 'sector2', 'sector3'].forEach((sector, index) => {
        const sectorNum = index + 1;
        const recordEl = document.getElementById(`recordS${sectorNum}`); // Changed to S1, S2, S3
        const deltaEl = document.getElementById(`recordS${sectorNum}Delta`); // Changed to S1Delta, S2Delta

        if (!recordEl || !deltaEl || !records) return;

        const recordKey = `best_sector_${sectorNum}`; // Changed to best_sector_1, best_sector_2, etc.
        const lapKey = `sector_${sectorNum}_time`; // Added lapKey for consistency

        if (records[recordKey]) {
            recordEl.textContent = formatTime(records[recordKey] * 1000);

            // Calculate delta if we have best lap data
            if (bestLap && bestLap[lapKey]) { // Used lapKey here
                const delta = bestLap[lapKey] - records[recordKey];
                if (Math.abs(delta) < 0.001) {
                    deltaEl.textContent = '🏆';
                    deltaEl.className = 'delta record';
                } else if (delta > 0) {
                    deltaEl.textContent = `+${delta.toFixed(3)}s`;
                    deltaEl.className = 'delta positive';
                } else {
                    deltaEl.textContent = `${delta.toFixed(3)}s`;
                    deltaEl.className = 'delta negative';
                }
            } else {
                deltaEl.textContent = ''; // Clear delta if no current lap data
            }
        } else {
            recordEl.textContent = '--';
            deltaEl.textContent = '';
        }
    });

    // Show records broken notice
    const notice = document.getElementById('recordsBrokenNotice');
    if (notice && recordsBroken && (recordsBroken.lap || recordsBroken.sectors.length > 0 || recordsBroken.sections.length > 0)) {
        notice.classList.remove('hidden');
    }
}

function displayRecommendations(recommendations) {
    const container = document.getElementById('recommendationsList');
    container.innerHTML = '';

    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<p class="loading">No hay recomendaciones disponibles.</p>';
        return;
    }

    recommendations.forEach(rec => {
        const item = document.createElement('div');
        item.className = 'recommendation-item';

        // Translate specific English message if backend hasn't been restarted
        if (rec === "Complete at least 2 laps for detailed analysis") {
            rec = "Completa al menos 2 vueltas para un análisis detallado";
        }

        // Determine severity
        if (rec.includes('🔴') || rec.includes('critical')) {
            item.classList.add('critical');
        } else if (rec.includes('🟡') || rec.includes('warning')) {
            item.classList.add('warning');
        }

        item.textContent = rec;
        container.appendChild(item);
    });
}

function loadLapsTable(laps) {
    const tbody = document.getElementById('lapsTableBody');
    tbody.innerHTML = '';

    if (!laps || laps.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No se registraron vueltas</td></tr>';
        return;
    }

    // Find best lap
    const bestLapTime = Math.min(...laps.map(l => l.lap_time));

    laps.forEach(lap => {
        const row = document.createElement('tr');
        if (lap.lap_time === bestLapTime) {
            row.classList.add('best-lap');
        }

        row.innerHTML = `
            <td>${lap.lap_number}</td>
            <td>${lap.lap_time.toFixed(3)}s</td>
            <td>${lap.sector_1_time ? lap.sector_1_time.toFixed(3) + 's' : '--'}</td>
            <td>${lap.sector_2_time ? lap.sector_2_time.toFixed(3) + 's' : '--'}</td>
            <td>${lap.sector_3_time ? lap.sector_3_time.toFixed(3) + 's' : '--'}</td>
            <td>${lap.is_valid ? '✓' : '✗'}</td>
        `;

        tbody.appendChild(row);
    });
}

// Utility Functions
function formatTime(milliseconds) {
    if (!milliseconds || milliseconds <= 0) {
        return '--:--.---';
    }

    const totalSeconds = milliseconds / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.floor(totalSeconds % 60);
    const ms = Math.round((totalSeconds % 1) * 1000);

    return `${minutes}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
}


function displaySectionAnalysis(sections, sectionRecords = []) {
    const container = document.getElementById('sectionAnalysisTable');

    if (!sections) sections = [];

    // Removed early return to ensure placeholders are always rendered
    // if (!sections || sections.length === 0) { ... }

    console.log('📊 Analyzing sections:', sections);
    const cornerCount = sections.filter(s => s.type === 'corner').length;
    const straightCount = sections.filter(s => s.type === 'straight').length;
    console.log(`Found ${cornerCount} corners and ${straightCount} straights`);

    // Create a map of section records for quick lookup
    const recordsMap = {};
    sectionRecords.forEach(record => {
        recordsMap[record.section_id] = record;
    });

    // Sort by ID to ensure sequential order (Curve 1, Curve 2, etc.)
    const curves = sections.filter(s => s.type === 'corner').sort((a, b) => a.section_id - b.section_id);
    const straights = sections.filter(s => s.type === 'straight').sort((a, b) => a.section_id - b.section_id);

    // Removed placeholder logic to show only actual sections

    let html = '';

    // Display curves
    if (curves.length > 0) {
        html += '<div class="section-group">';
        html += '<h3>🔄 CURVAS</h3>';
        html += '<div class="section-cards">';

        curves.forEach((section, index) => {
            if (section.isPlaceholder) {
                html += `
                    <div class="section-card waiting">
                        <div class="section-card-header">
                            <span class="section-number">Curva ${index + 1}</span>
                            <div class="section-time-container">
                                <span class="section-time">--</span>
                            </div>
                        </div>
                        <div class="section-card-body">
                            <div class="section-stat">
                                <span class="stat-label">Entrada</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Salida</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Promedio</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                const entrySpeed = section.entry_speed || section.min_speed || 0;
                const exitSpeed = section.exit_speed || section.max_speed || 0;
                const avgSpeed = section.avg_speed || 0;
                const time = section.time || 0;
                const isValid = section.is_valid !== false; // Default to true if not specified

                // Get best time for this section
                const record = recordsMap[section.section_id];
                const bestTime = record ? record.best_time : null;
                const isNewRecord = record && Math.abs(time - bestTime) < 0.001; // Within 1ms

                // Calculate delta
                let delta = null;
                let deltaClass = '';
                let deltaText = '';
                if (bestTime && !isNewRecord) {
                    delta = time - bestTime;
                    if (delta < 0) {
                        deltaClass = 'delta-positive'; // Faster (green)
                        deltaText = `${Math.abs(delta).toFixed(3)}s`;
                    } else {
                        deltaClass = 'delta-negative'; // Slower (red)
                        deltaText = `+${delta.toFixed(3)}s`;
                    }
                }

                // Color code based on average speed
                let speedClass = 'speed-low';
                if (avgSpeed > 150) speedClass = 'speed-high';
                else if (avgSpeed > 100) speedClass = 'speed-medium';

                // Add invalid class if off-track
                const validityClass = !isValid ? 'invalid-section' : '';

                // Sequential Label: Curva 1, Curva 2, etc. (Original ID in tooltips if needed)
                html += `
                    <div class="section-card ${speedClass} ${isNewRecord ? 'new-record' : ''} ${validityClass}">
                        <div class="section-card-header">
                            <span class="section-number">Curva ${index + 1}</span>
                            <div class="section-time-container">
                                <span class="section-time">${time.toFixed(3)}s</span>
                                ${isNewRecord ? '<span class="record-badge">🏆 RÉCORD</span>' : ''}
                                ${delta !== null ? `<span class="section-delta ${deltaClass}">${deltaText}</span>` : ''}
                            </div>
                        </div>
                        <div class="section-card-body">
                            ${bestTime && !isNewRecord ? `
                                <div class="section-stat best-time-stat">
                                    <span class="stat-label">⭐ Mejor Tiempo</span>
                                    <span class="stat-value">${bestTime.toFixed(3)}s</span>
                                </div>
                            ` : ''}
                            <div class="section-stat">
                                <span class="stat-label">Entrada</span>
                                <span class="stat-value">${Math.round(entrySpeed)} km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Salida</span>
                                <span class="stat-value">${Math.round(exitSpeed)} km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Promedio</span>
                                <span class="stat-value">${Math.round(avgSpeed)} km/h</span>
                            </div>
                            ${!isValid && section.recommendation ? `
                                <div class="section-warning">
                                    <div class="warning-text">⚠️ Saliste de pista</div>
                                    ${section.recommended_speed ? `
                                        <div class="recommendation-text">
                                            Velocidad recomendada: ${Math.round(section.recommended_speed)} km/h
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
        });

        html += '</div></div>';
    }

    // Display straights
    if (straights.length > 0) {
        html += '<div class="section-group">';
        html += '<h3>➡️ RECTAS</h3>';
        html += '<div class="section-cards">';

        straights.forEach((section, index) => {
            if (section.isPlaceholder) {
                html += `
                    <div class="section-card waiting">
                        <div class="section-card-header">
                            <span class="section-number">Recta ${index + 1}</span>
                            <div class="section-time-container">
                                <span class="section-time">--</span>
                            </div>
                        </div>
                        <div class="section-card-body">
                            <div class="section-stat">
                                <span class="stat-label">Entrada</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Salida</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Máxima</span>
                                <span class="stat-value">-- km/h</span>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                const entrySpeed = section.entry_speed || section.min_speed || 0;
                const exitSpeed = section.exit_speed || section.max_speed || 0;
                const maxSpeed = section.max_speed || 0;
                const time = section.time || 0;

                // Get best time for this section
                const record = recordsMap[section.section_id];
                const bestTime = record ? record.best_time : null;
                const isNewRecord = record && Math.abs(time - bestTime) < 0.001;

                // Calculate delta
                let delta = null;
                let deltaClass = '';
                let deltaText = '';
                if (bestTime && !isNewRecord) {
                    delta = time - bestTime;
                    if (delta < 0) {
                        deltaClass = 'delta-positive';
                        deltaText = `${Math.abs(delta).toFixed(3)}s`;
                    } else {
                        deltaClass = 'delta-negative';
                        deltaText = `+${delta.toFixed(3)}s`;
                    }
                }

                // Color code based on max speed
                let speedClass = 'speed-low';
                if (maxSpeed > 200) speedClass = 'speed-high';
                else if (maxSpeed > 150) speedClass = 'speed-medium';

                html += `
                    <div class="section-card ${speedClass} ${isNewRecord ? 'new-record' : ''}">
                        <div class="section-card-header">
                            <span class="section-number">Recta ${index + 1}</span>
                            <div class="section-time-container">
                                <span class="section-time">${time.toFixed(3)}s</span>
                                ${isNewRecord ? '<span class="record-badge">🏆 RÉCORD</span>' : ''}
                                ${delta !== null ? `<span class="section-delta ${deltaClass}">${deltaText}</span>` : ''}
                            </div>
                        </div>
                        <div class="section-card-body">
                            ${bestTime && !isNewRecord ? `
                                <div class="section-stat best-time-stat">
                                    <span class="stat-label">⭐ Mejor Tiempo</span>
                                    <span class="stat-value">${bestTime.toFixed(3)}s</span>
                                </div>
                            ` : ''}
                            <div class="section-stat">
                                <span class="stat-label">Entrada</span>
                                <span class="stat-value">${Math.round(entrySpeed)} km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Salida</span>
                                <span class="stat-value">${Math.round(exitSpeed)} km/h</span>
                            </div>
                            <div class="section-stat">
                                <span class="stat-label">Máxima</span>
                                <span class="stat-value">${Math.round(maxSpeed)} km/h</span>
                            </div>
                        </div>
                    </div>
                `;
            }
        });

        html += '</div></div>';
    }

    container.innerHTML = html;
}

// History View Logic
async function loadHistoryTracks() {
    // Directly fetch tracks and select the last one (or current if valid)
    try {
        const response = await fetch('/api/history/tracks');
        const data = await response.json();

        if (data.tracks && data.tracks.length > 0) {
            // Check if we have a current track from the race
            const currentTrackElement = document.getElementById('currentTrack');
            let trackToLoad = data.tracks[data.tracks.length - 1]; // Default to most recent

            if (currentTrackElement && currentTrackElement.textContent !== '--') {
                const currentTrackName = currentTrackElement.textContent;
                if (data.tracks.includes(currentTrackName)) {
                    trackToLoad = currentTrackName;
                }
            }

            // Auto-select the track
            selectTrack(trackToLoad);
        } else {
            document.getElementById('selectedTrackTitle').textContent = 'ANÁLISIS DE CIRCUITO: No hay datos disponibles';
            showTrackList();
        }
    } catch (e) {
        console.error('Error loading tracks:', e);
    }
}

async function showTrackList() {
    document.getElementById('trackHistoryDashboard').classList.add('hidden');
    document.getElementById('trackSelectionContainer').classList.remove('hidden');

    const listContainer = document.getElementById('trackList');
    listContainer.innerHTML = '<p class="loading">Cargando circuitos...</p>';

    try {
        const response = await fetch('/api/history/tracks');
        const data = await response.json();

        if (data.tracks && data.tracks.length > 0) {
            listContainer.innerHTML = '';
            data.tracks.forEach(track => {
                const card = document.createElement('div');
                card.className = 'track-card';
                // Inline styles for quick implementation
                card.style.cssText = `
                    background: rgba(20, 24, 30, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 20px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                `;

                card.onmouseenter = function () {
                    this.style.borderColor = 'var(--accent-cyan)';
                    this.style.transform = 'translateY(-5px)';
                    this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.3)';
                    this.style.background = 'rgba(30, 36, 45, 0.8)';
                };
                card.onmouseleave = function () {
                    this.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = 'none';
                    this.style.background = 'rgba(20, 24, 30, 0.6)';
                };

                card.innerHTML = `
                    <div style="font-size: 2rem; margin-bottom: 10px; opacity: 0.5;">🏁</div>
                    <h3 style="margin: 0 0 10px 0; font-size: 1.2rem; font-family: 'Exo 2', sans-serif;">${track}</h3>
                    <div style="margin-top: 15px;">
                        <span style="font-size: 0.9rem; color: var(--accent-cyan); font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Ver Análisis ➔</span>
                    </div>
                `;

                card.addEventListener('click', () => selectTrack(track));
                listContainer.appendChild(card);
            });
        } else {
            listContainer.innerHTML = '<p>No hay circuitos registrados aún.</p>';
        }
    } catch (e) {
        console.error('Error loading tracks:', e);
        listContainer.innerHTML = '<p class="error">Error cargando circuitos.</p>';
    }
}

async function selectTrack(trackName) {
    // Hide list, show dashboard
    document.getElementById('trackSelectionContainer').classList.add('hidden');
    document.getElementById('trackHistoryDashboard').classList.remove('hidden');

    document.getElementById('selectedTrackTitle').textContent = `ANÁLISIS DE CIRCUITO: ${trackName}`;

    // Reset charts
    if (lastRacesChartInstance) lastRacesChartInstance.destroy();
    if (lastLapsChartInstance) lastLapsChartInstance.destroy();
    if (speedComparisonChartInstance) speedComparisonChartInstance.destroy();
    lastRacesChartInstance = null;
    lastLapsChartInstance = null;
    speedComparisonChartInstance = null;

    // 1. Load Last 3 Races Analysis
    try {
        const response = await fetch(`/api/history/${encodeURIComponent(trackName)}`);
        const data = await response.json();

        if (data.available) {
            renderLastRacesChart(data);
            renderHistoryTable(data.raw_data);
            renderRaceAnalysis(data); // Render Race Analysis

            // Render Speed Comparison Chart if data exists
            if (data.speed_comparison && data.speed_comparison.length > 0) {
                renderSpeedComparisonChart(data.speed_comparison);
            }

            // If we have sessions, load the Last 3 Laps of the most recent session
            if (data.raw_data && data.raw_data.length > 0) {
                // Determine latest session (assuming response raw_data is chronological)
                // Main logic: get_last_n_sessions sorted by start_time. Last element is newest.
                const latestSession = data.raw_data[data.raw_data.length - 1];
                loadLastLapsAnalysis(latestSession.id);
            }
        }
    } catch (e) {
        console.error('Error loading track history:', e);
    }
}

async function loadLastLapsAnalysis(sessionId) {
    try {
        const response = await fetch(`/api/history/sessions/${sessionId}/last-laps`);
        const data = await response.json();

        if (data.available) {
            renderLastLapsChart(data);
            renderLapAnalysis(data); // Render Lap Analysis
        }
    } catch (e) {
        console.error('Error loading last laps:', e);
    }
}

function renderHistoryTable(sessions) {
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '';

    // Reverse to show newest first in table
    [...sessions].reverse().forEach(session => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        row.style.transition = 'background 0.2s';
        row.onmouseenter = function () { this.style.background = 'rgba(255,255,255,0.02)'; };
        row.onmouseleave = function () { this.style.background = 'transparent'; };

        // Handle date parsing safely
        let dateStr = 'Unknown';
        try {
            // Handle "2023-10-27 10:00:00.000000" format or ISO
            const date = new Date(session.start_time);
            dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) { dateStr = session.start_time; }

        const bestLap = session.best_lap_time ? formatTime(session.best_lap_time * 1000) : '--:--.---';

        row.innerHTML = `
            <td style="padding: 12px; color: var(--text-secondary);">${dateStr}</td>
            <td style="padding: 12px; font-weight: 500;">${session.car_name}</td>
            <td style="padding: 12px;">${session.total_laps}</td>
            <td style="padding: 12px; font-weight: bold; color: var(--accent-cyan); font-family: 'Space Grotesk', sans-serif;">${bestLap}</td>
            <td style="padding: 12px;">
                <button onclick="loadAnalysis(${session.id}, null); switchView('analysis');" style="background: transparent; border: 1px solid var(--text-secondary); color: var(--text-primary); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; transition: all 0.2s;">Ver Detalle</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Global Chart Instances
let lastRacesChartInstance = null;
let lastLapsChartInstance = null;
let speedComparisonChartInstance = null;

function renderLastRacesChart(data) {
    const ctx = document.getElementById('lastRacesChart').getContext('2d');

    if (lastRacesChartInstance) {
        lastRacesChartInstance.destroy();
    }

    // Prepare gradients
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(0, 255, 255, 0.6)');
    gradient.addColorStop(1, 'rgba(0, 255, 255, 0.1)');

    lastRacesChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.dates, // e.g., ["10/10/2023", ...]
            datasets: [{
                label: 'Mejor Vuelta (s)',
                data: data.best_laps,
                backgroundColor: gradient,
                borderColor: '#00ffff',
                borderWidth: 1,
                borderRadius: 4,
                barThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        label: function (context) {
                            return `Tiempo: ${context.raw.toFixed(3)}s`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false, // Zoom in on the times
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#888' },
                    title: { display: true, text: 'Segundos', color: '#666' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#ccc' }
                }
            }
        }
    });
}

function renderLastLapsChart(data) {
    const ctx = document.getElementById('lastLapsChart').getContext('2d');

    if (lastLapsChartInstance) {
        lastLapsChartInstance.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(255, 0, 85, 0.4)');
    gradient.addColorStop(1, 'rgba(255, 0, 85, 0.0)');

    lastLapsChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels, // ["Vuelta 3", "Vuelta 4", ...]
            datasets: [{
                label: 'Tiempo de Vuelta',
                data: data.times,
                borderColor: '#ff0055',
                backgroundColor: gradient,
                tension: 0.3,
                fill: true,
                pointRadius: 6,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#ff0055',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `Consistencia: ${data.consistency_score}% (${data.std_dev.toFixed(3)}s desviación)`,
                    color: '#ccc',
                    font: { size: 14, weight: 'normal' }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    callbacks: {
                        label: function (context) {
                            return ` ${context.raw.toFixed(3)}s`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#888' },
                    title: { display: true, text: 'Segundos', color: '#666' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#ccc' }
                }
            }
        }
    });
}

function renderSpeedComparisonChart(datasets) {
    const ctx = document.getElementById('speedComparisonChart').getContext('2d');

    if (speedComparisonChartInstance) {
        speedComparisonChartInstance.destroy();
    }

    // Color palette for lines
    const colors = [
        '#00ffff', // Cyan
        '#ff0055', // Red
        '#00ff88', // Green
        '#ffaa00', // Orange
        '#aa00ff'  // Purple
    ];

    const chartDatasets = datasets.map((d, index) => {
        const color = colors[index % colors.length];
        return {
            label: d.label,
            data: d.data, // [{x, y}, ...]
            borderColor: color,
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 0, // Hide points for clean line
            pointHoverRadius: 4,
            tension: 0.4
        };
    });

    speedComparisonChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: chartDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: '#ccc' }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        title: (items) => `Posición: ${items[0].parsed.x}`,
                        label: (context) => `${context.dataset.label}: ${context.parsed.y} km/h`
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    display: true,
                    title: { display: true, text: 'Progreso Vuelta (Puntos)', color: '#666' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#888' }
                },
                y: {
                    display: true,
                    title: { display: true, text: 'Velocidad (km/h)', color: '#666' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#888' }
                }
            }
        }
    });
}

// --- Render Race Analysis Container ---
function renderRaceAnalysis(data) {
    const list = document.getElementById('raceAnalysisContent');
    if (!list) return;

    if (!data || !data.session_stats || data.session_stats.length === 0) {
        list.innerHTML = '<p class="no-data">No hay suficientes datos de carrera para analizar.</p>';
        return;
    }

    const stats = data.session_stats;
    let html = '<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">';

    // Generate cards for each session
    stats.forEach(session => {
        html += `
            <div class="stat-card" style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border-left: 3px solid var(--accent-cyan);">
                <h4 style="margin: 0 0 5px 0; color: var(--accent-cyan); font-size: 1rem;">${session.date} (S${session.id})</h4>
                <div style="font-size: 0.9em; line-height: 1.4;">
                    <p style="margin: 2px 0;">🏁 Vueltas: <span style="font-weight: bold;">${session.total_laps}</span></p>
                    <p style="margin: 2px 0;">⚡ Vel. Prom: <span style="font-weight: bold;">${session.avg_speed} km/h</span></p>
                    <p style="margin: 2px 0;">⚠️ Salidas: <span style="font-weight: bold; color: ${session.off_tracks > 0 ? 'var(--accent-red)' : 'var(--accent-green)'};">${session.off_tracks}</span></p>
                    <p style="margin: 2px 0;">⏱️ Mejor: <span style="font-weight: bold;">${session.best_lap < 9999 ? session.best_lap.toFixed(3) + 's' : '--'}</span></p>
                </div>
            </div>
        `;
    });
    html += '</div>';

    // Best Session Recommendation
    if (data.best_session) {
        html += `
            <div class="recommendation-box" style="margin-top: 15px; padding: 12px; border-radius: 8px; border-left: 4px solid var(--accent-green); background: rgba(var(--accent-green-rgb), 0.1);">
                <h4 style="margin: 0 0 5px 0; color: var(--accent-green); display: flex; align-items: center; gap: 8px;">
                    🏆 Mejor Sesión: ${data.best_session.date}
                </h4>
                <p style="margin: 0; font-size: 0.95em;">
                    Lograste tu mejor tiempo de <strong>${data.best_session.best_lap.toFixed(3)}s</strong> 
                    con <strong>${data.best_session.off_tracks}</strong> salidas de pista.
                    Mantuviste una velocidad promedio de <strong>${data.best_session.avg_speed} km/h</strong>.
                </p>
            </div>
        `;
    }

    list.innerHTML = html;
}

// --- Render Lap Analysis Container ---
function renderLapAnalysis(data) {
    const list = document.getElementById('lapAnalysisContent');
    if (!list) return;

    if (!data.raw_data || data.raw_data.length === 0) {
        list.innerHTML = '<p class="no-data">No hay datos de vueltas recientes.</p>';
        return;
    }

    const laps = data.raw_data; // Use raw_data which contains the laps
    let html = '<div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">';

    laps.forEach(lap => {
        const isBest = data.best_lap_id === lap.id;
        const borderStyle = isBest ? 'border: 1px solid var(--accent-gold); box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);' : 'border: 1px solid rgba(255,255,255,0.1);';
        const validIcon = lap.is_valid ? '<span style="color: var(--accent-green);">✅ Válida</span>' : '<span style="color: var(--accent-red);">❌ Inválida</span>';
        const avgSpeed = lap.avg_speed ? lap.avg_speed.toFixed(1) : '--';

        html += `
            <div class="stat-card" style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; ${borderStyle}">
                <h4 style="margin: 0 0 5px 0; color: var(--text-primary); font-size: 0.95rem; display: flex; justify-content: space-between;">
                    Vuelta ${lap.lap_number} ${isBest ? '👑' : ''}
                </h4>
                <div style="font-size: 0.85em; line-height: 1.4;">
                    <p style="margin: 2px 0; font-size: 1.1em; font-weight: bold; color: var(--accent-cyan);">${lap.lap_time.toFixed(3)}s</p>
                    <p style="margin: 2px 0;">⚡ ${avgSpeed} km/h</p>
                    <p style="margin: 2px 0;">${validIcon}</p>
                </div>
            </div>
        `;
    });
    html += '</div>';

    // Consistency Analysis
    if (data.consistency_score !== undefined) {
        let color = 'var(--accent-green)';
        let msg = '¡Muy constante!';
        if (data.consistency_score < 50) { color = 'var(--accent-red)'; msg = 'Ritmo irregular.'; }
        else if (data.consistency_score < 80) { color = 'var(--accent-gold)'; msg = 'Buena consistencia.'; }

        html += `
            <div class="recommendation-box" style="margin-top: 15px; padding: 12px; border-radius: 8px; border-left: 4px solid ${color}; background: rgba(255,255,255, 0.05);">
                <h4 style="margin: 0 0 5px 0; color: ${color};">📊 Puntuación de Consistencia: ${data.consistency_score}%</h4>
                <p style="margin: 0; font-size: 0.95em;">
                    ${msg} Desviación estándar de <strong>${data.std_dev}s</strong> entre estas vueltas.
                    ${data.consistency_score > 80 ? 'Estás rodando como un reloj suizo.' : 'Intenta frenar en los mismos puntos para mejorar.'}
                </p>
            </div>
        `;
    }

    list.innerHTML = html;
}
