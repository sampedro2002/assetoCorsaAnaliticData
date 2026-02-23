// Chart.js Configuration for Telemetry Analysis

let speedChart = null;
let inputsChart = null;

// Initialize charts when analysis view is shown
function initializeCharts() {
    initSpeedChart();
    initInputsChart();
}

function initSpeedChart() {
    const ctx = document.getElementById('speedChart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (speedChart) {
        speedChart.destroy();
        speedChart = null;
    }

    speedChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Mejor Vuelta',
                data: [],
                borderColor: 'rgb(0, 255, 255)',
                backgroundColor: 'rgba(0, 255, 255, 0.1)',
                borderWidth: 2,
                tension: 0.4
            }, {
                label: 'Última Vuelta',
                data: [],
                borderColor: 'rgb(255, 0, 85)',
                backgroundColor: 'rgba(255, 0, 85, 0.1)',
                borderWidth: 2,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary').trim()
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Distancia',
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    ticks: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Velocidad (km/h)',
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    ticks: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

function initInputsChart() {
    const ctx = document.getElementById('inputsChart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (inputsChart) {
        inputsChart.destroy();
        inputsChart = null;
    }

    inputsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Acelerador',
                data: [],
                borderColor: 'rgb(0, 255, 136)',
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                yAxisID: 'y'
            }, {
                label: 'Freno',
                data: [],
                borderColor: 'rgb(255, 0, 85)',
                backgroundColor: 'rgba(255, 0, 85, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                yAxisID: 'y'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary').trim()
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Distancia',
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    ticks: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Entrada (%)',
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    min: 0,
                    max: 100,
                    ticks: {
                        color: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary').trim()
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

// Global Chart References
let racePaceChart = null;
let speedComparisonChart = null;
let lastRacesChart = null;
let lastLapsChart = null;

function initHistoryCharts() {
    initRacePaceChart();
    initSpeedComparisonChart();
    initLastRacesChart();
    initLastLapsChart();
}

function initRacePaceChart() {
    const ctx = document.getElementById('racePaceChart');
    if (!ctx) return;

    if (racePaceChart) {
        racePaceChart.destroy();
        racePaceChart = null;
    }

    racePaceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Tiempo de Vuelta',
                data: [],
                borderColor: '#00ffff',
                backgroundColor: 'rgba(0, 255, 255, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    title: { display: true, text: 'Tiempo (s)', color: '#888' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#888' }
                },
                x: {
                    title: { display: true, text: 'Vuelta', color: '#888' },
                    grid: { display: false },
                    ticks: { color: '#888' }
                }
            }
        }
    });
}

function initSpeedComparisonChart() {
    const ctx = document.getElementById('speedComparisonChart');
    if (!ctx) return;

    if (speedComparisonChart) {
        speedComparisonChart.destroy();
        speedComparisonChart = null;
    }

    speedComparisonChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Mejor',
                    data: [],
                    borderColor: '#00ffff',
                    tension: 0.4
                },
                {
                    label: 'Promedio',
                    data: [],
                    borderColor: '#ff0055',
                    borderDash: [5, 5],
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    display: false
                },
                x: {
                    display: false
                }
            },
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function initLastRacesChart() {
    const ctx = document.getElementById('lastRacesChart');
    if (!ctx) return;

    if (lastRacesChart) {
        lastRacesChart.destroy();
        lastRacesChart = null;
    }

    lastRacesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'bottom',
                    labels: { color: '#888' }
                }
            },
            scales: {
                y: {
                    display: true,
                    title: { display: true, text: 'Velocidad (km/h)', color: '#888' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#888' }
                },
                x: {
                    display: true,
                    title: { display: true, text: 'Distancia (%)', color: '#888' },
                    grid: { display: false },
                    ticks: {
                        display: true,
                        color: '#888',
                        maxRotation: 0,
                        autoSkip: true
                    }
                }
            }
        }
    });
}

function initLastLapsChart() {
    const ctx = document.getElementById('lastLapsChart');
    if (!ctx) return;

    if (lastLapsChart) {
        lastLapsChart.destroy();
        lastLapsChart = null;
    }

    lastLapsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { color: '#888' }
                }
            },
            scales: {
                y: {
                    display: true,
                    title: { display: true, text: 'Velocidad (km/h)', color: '#888' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#888' }
                },
                x: {
                    display: true,
                    title: { display: true, text: 'Distancia (%)', color: '#888' },
                    grid: { display: false },
                    ticks: {
                        display: true,
                        color: '#888',
                        maxRotation: 0,
                        autoSkip: true
                    }
                }
            }
        }
    });
}


// Make available globally
window.initHistoryCharts = initHistoryCharts;
window.updateRacePaceChart = updateRacePaceChart;
window.updateLastRacesChart = updateLastRacesChart;
window.updateLastLapsChart = updateLastLapsChart;

function updateLastRacesChart(speedComparisonData) {
    if (!lastRacesChart || !speedComparisonData) return;

    // Always exactly 2 fixed colors:
    // index 0 → Best race  (cyan  🏆)
    // index 1 → Last race  (red   🔄)
    const FIXED_COLORS = ['#00ffff', '#ff0055'];

    // Reset datasets
    lastRacesChart.data.datasets = [];
    lastRacesChart.data.labels = [];

    // Use up to 2 entries from the backend (best + last)
    const twoEntries = speedComparisonData.slice(0, 2);

    if (twoEntries.length > 0) {
        const pointsCount = twoEntries[0].data.length;
        lastRacesChart.data.labels = Array.from({ length: pointsCount }, (_, i) => {
            const pct = Math.round((i / (pointsCount - 1 || 1)) * 100);
            return pct + '%';
        });
    }

    twoEntries.forEach((session, index) => {
        const color = FIXED_COLORS[index % FIXED_COLORS.length];
        const isBest = index === 0;

        lastRacesChart.data.datasets.push({
            label: session.label,
            data: session.data.map(p => p.y), // p.y is speed
            borderColor: color,
            backgroundColor: isBest ? 'rgba(0,255,255,0.05)' : 'rgba(255,0,85,0.05)',
            borderWidth: isBest ? 2.5 : 2,
            borderDash: isBest ? [] : [6, 3],
            pointRadius: 0,
            tension: 0.4
        });
    });

    lastRacesChart.update();
}

function updateLastLapsChart(lapsData) {
    if (!lastLapsChart || !lapsData) return;

    // Always exactly 2 fixed colors:
    // index 0 → Best lap  (cyan  🏆)
    // index 1 → Last lap  (red   🔄)
    const FIXED_COLORS = ['#00ffff', '#ff0055'];

    // Reset datasets
    lastLapsChart.data.datasets = [];
    lastLapsChart.data.labels = [];

    if (lapsData.speed_comparison && lapsData.speed_comparison.length > 0) {
        // Backend now returns exactly 2 entries: best + last
        const twoEntries = lapsData.speed_comparison.slice(0, 2);

        const pointsCount = twoEntries[0].data.length;
        // Generate percentage labels
        lastLapsChart.data.labels = Array.from({ length: pointsCount }, (_, i) => {
            const pct = Math.round((i / (pointsCount - 1 || 1)) * 100);
            return pct + '%';
        });

        twoEntries.forEach((lap, index) => {
            const color = FIXED_COLORS[index % FIXED_COLORS.length];
            const isBest = index === 0;

            lastLapsChart.data.datasets.push({
                label: lap.label,
                data: lap.data.map(p => p.y !== undefined ? p.y : p), // supports {x,y} or plain number
                borderColor: color,
                backgroundColor: isBest ? 'rgba(0,255,255,0.05)' : 'rgba(255,0,85,0.05)',
                borderWidth: isBest ? 2.5 : 2,
                borderDash: isBest ? [] : [6, 3],
                pointRadius: 0,
                tension: 0.4
            });
        });

    } else if (lapsData.times) {
        console.warn("No telemetry data for Last Laps chart");
    }

    lastLapsChart.update();
}

function updateRacePaceChart(laps) {
    if (!racePaceChart || !laps) return;

    // Filter valid laps and get times
    const validLaps = laps.filter(l => l.lap_time > 0);
    const labels = validLaps.map(l => l.lap_number + 1);
    const data = validLaps.map(l => l.lap_time / 1000.0); // Seconds

    racePaceChart.data.labels = labels;
    racePaceChart.data.datasets[0].data = data;

    // Calculate average for reference line? 
    // For now just basic plot

    racePaceChart.update();
}

async function loadChartData(sessionId) {
    try {
        // Get session laps
        const response = await fetch(`/api/sessions/${sessionId}/laps`);
        const data = await response.json();

        if (!data.laps || data.laps.length === 0) {
            console.log('No laps available for charts');
            return;
        }

        // Find best lap and last lap
        // Filter for complete laps first
        const completeLaps = data.laps.filter(l => l.lap_time > 0);

        if (completeLaps.length === 0) {
            console.log('No complete laps found');
            return;
        }

        // SQLite stores is_valid as INTEGER (1 = valid, 0 = invalid)
        let validLaps = completeLaps.filter(l => l.is_valid !== 0 && l.is_valid !== false);

        // Fallback to all complete laps if no valid ones exist
        if (validLaps.length === 0) {
            validLaps = completeLaps;
        }

        const bestLap = validLaps.reduce((best, lap) =>
            lap.lap_time < best.lap_time ? lap : best
        );
        // Last lap should be the actual last lap of the session (even if invalid)
        // provided it is complete.
        // If we want "Last VALID lap", use validLaps. 
        // Usually users want to compare against their *actual* last attempt.
        const lastLap = completeLaps[completeLaps.length - 1];

        // Load telemetry
        const bestTelemetry = await fetch(`/api/laps/${bestLap.id}/telemetry`).then(r => r.json());
        let lastTelemetry = { telemetry: [] };

        if (lastLap.id !== bestLap.id) {
            lastTelemetry = await fetch(`/api/laps/${lastLap.id}/telemetry`).then(r => r.json());
        } else {
            // Use same data or empty if only one lap
            lastTelemetry = bestTelemetry;
        }

        // Build datasets in the format expected by updateSpeedChart
        const speedDatasets = [];
        if (bestTelemetry.telemetry && bestTelemetry.telemetry.length > 0) {
            speedDatasets.push({
                label: `Mejor Vuelta (${formatTime(bestLap.lap_time)})`,
                data: bestTelemetry.telemetry
            });
        }
        if (lastTelemetry.telemetry && lastTelemetry.telemetry.length > 0 && lastLap.id !== bestLap.id) {
            speedDatasets.push({
                label: `Última Vuelta (${formatTime(lastLap.lap_time)})`,
                data: lastTelemetry.telemetry
            });
        }

        // Update speed chart
        if (speedDatasets.length > 0) {
            updateSpeedChart(speedDatasets);
        }

        // Update inputs chart (uses last lap telemetry)
        updateInputsChart(lastTelemetry.telemetry);

        // Update Race Pace chart
        updateRacePaceChart(data.laps);

    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Make loadChartData globally available
window.loadChartData = loadChartData;

// Helper to resample telemetry to a fixed number of points (normalized distance)
function resampleTelemetry(telemetryData, targetPoints = 21) {
    if (!telemetryData || telemetryData.length === 0) {
        console.warn('⚠️ Empty telemetry data, returning zeros');
        return Array(targetPoints).fill({ speed: 0, throttle: 0, brake: 0, normalized_position: 0 });
    }

    // Check if normalized_position exists and has valid variance
    const hasNormalizedPosition = telemetryData[0]?.normalized_position !== undefined;
    let useIndexBased = !hasNormalizedPosition;

    if (hasNormalizedPosition) {
        // Check if it's actually changing (some mod tracks return 0 always)
        const firstPos = telemetryData[0].normalized_position;
        const allSame = telemetryData.every(d => Math.abs(d.normalized_position - firstPos) < 0.0001);
        if (allSame) {
            console.warn('⚠️ normalized_position is constant (likely 0), falling back to index-based resampling');
            useIndexBased = true;
        }
    }

    if (useIndexBased) {
        console.warn('⚠️ normalized_position missing, using index-based resampling');
        // Fallback: use array index as position
        const resampled = [];
        for (let i = 0; i <= targetPoints; i++) {
            const sourceIndex = Math.floor((i / targetPoints) * (telemetryData.length - 1));
            const point = telemetryData[sourceIndex] || telemetryData[0];
            resampled.push({
                speed: point.speed || 0,
                throttle: point.throttle || 0,
                brake: point.brake || 0,
                normalized_position: i / targetPoints
            });
        }
        return resampled;
    }

    const resampled = [];

    // Sort just in case, though usually sorted by time
    // We assume normalized_position roughly increases monotonic

    for (let i = 0; i <= targetPoints; i++) {
        const targetPos = i / targetPoints;

        // Find closest point (simple nearest neighbor for robustness)
        // Optimization: could use binary search or sliding window, but loop is fine for <10k points

        let closest = telemetryData[0];
        let minDiff = Math.abs(telemetryData[0].normalized_position - targetPos);

        // Optimization: Start search from approximate index
        const approxIdx = Math.floor(targetPos * telemetryData.length);
        const searchRange = Math.floor(telemetryData.length * 0.1); // Search 10% window
        const start = Math.max(0, approxIdx - searchRange);
        const end = Math.min(telemetryData.length, approxIdx + searchRange);

        for (let j = 0; j < telemetryData.length; j++) {
            // Full search is safer against non-linear position updates (e.g. rewinds/glitches)
            // But valid laps should be monotonic. Let's use full scan to be safe or just find min.
            const diff = Math.abs(telemetryData[j].normalized_position - targetPos);
            if (diff < minDiff) {
                minDiff = diff;
                closest = telemetryData[j];
            }
        }
        resampled.push(closest);
    }
    return resampled;
}

// function updateSpeedChart(bestData, lastData) -- REPLACED
// New version accepts array of { label, data: telemetry[] }
// Always uses exactly 2 fixed colors:
//   index 0 → Best lap  (cyan  🏆)
//   index 1 → Last lap  (red   🔄)
function updateSpeedChart(lapsData) {
    if (!speedChart || !lapsData || lapsData.length === 0) return;

    // Reset datasets
    speedChart.data.datasets = [];
    speedChart.data.labels = [];

    const resolution = 21; // 20 Segments (0% to 100%)
    // Fixed 2-color scheme — same palette as the history charts
    const FIXED_COLORS = ['#00ffff', '#ff0055'];

    // Generate labels from 0% to 100%
    const labels = Array.from({ length: resolution }, (_, i) => {
        const pct = Math.round((i / (resolution - 1)) * 100);
        return pct + '%';
    });
    speedChart.data.labels = labels;

    // Process each lap (max 2)
    lapsData.slice(0, 2).forEach((lap, index) => {
        const resampled = resampleTelemetry(lap.data, resolution);
        const color = FIXED_COLORS[index % FIXED_COLORS.length];
        const isBest = index === 0;

        speedChart.data.datasets.push({
            label: lap.label,
            data: resampled.map(d => d.speed),
            borderColor: color,
            backgroundColor: isBest ? 'rgba(0,255,255,0.05)' : 'rgba(255,0,85,0.05)',
            borderWidth: isBest ? 2.5 : 2,
            borderDash: isBest ? [] : [6, 3],
            pointRadius: 0,
            tension: 0.4,
        });
    });

    // Update X axis title
    speedChart.options.scales.x.title.text = 'Distancia de Vuelta (%)';

    speedChart.update();
}


async function loadBestRaceComparison(trackName) {
    if (!trackName) return;
    console.log(`Loading best race comparison for: ${trackName}`);

    try {
        // 1. Get all sessions for this track to find the best one
        // Note: This matches history.js logic
        const response = await fetch(`/api/history/sessions?track=${encodeURIComponent(trackName)}`);
        const data = await response.json();
        const sessions = data.sessions || [];

        if (sessions.length === 0) {
            console.log("No sessions found for comparison.");
            return;
        }

        // 2. Find Best Session (lowest best_lap)
        // Sessions usually sorted by date, so we sort by best_lap
        const validSessions = sessions.filter(s => s.best_lap > 0);
        if (validSessions.length === 0) return;

        validSessions.sort((a, b) => a.best_lap - b.best_lap);
        const bestSession = validSessions[0];

        // 3. Get Laps for Best Session
        const lapsResp = await fetch(`/api/sessions/${bestSession.id}/laps`);
        const lapsData = await lapsResp.json();
        const laps = lapsData.laps || [];

        // 4. Find Best lap + Last lap (chronological order)
        laps.sort((a, b) => a.id - b.id);

        const completedLaps = [];
        let lapCounter = 1;
        laps.forEach(l => {
            if (l.lap_time > 0) {
                l.display_number = lapCounter++;
                completedLaps.push(l);
            }
        });

        if (completedLaps.length === 0) {
            console.log('No completed laps in best session');
            return;
        }

        // Best lap: lowest time among valid ones
        const validCompleted = completedLaps.filter(l => l.is_valid) || completedLaps;
        const bestLapEntry = (validCompleted.length ? validCompleted : completedLaps)
            .reduce((b, l) => l.lap_time < b.lap_time ? l : b);

        // Last lap: last in chronological order
        const lastLapEntry = completedLaps[completedLaps.length - 1];

        // 5. Fetch Telemetry for exactly 2 laps
        const datasets = [];
        const lapsToFetch = [
            { lap: bestLapEntry, labelPrefix: '🏆 Mejor Vuelta' },
            ...(lastLapEntry.id !== bestLapEntry.id
                ? [{ lap: lastLapEntry, labelPrefix: '🔄 Última Vuelta' }]
                : [])
        ];

        for (const { lap, labelPrefix } of lapsToFetch) {
            try {
                const telResp = await fetch(`/api/laps/${lap.id}/telemetry`);
                const telData = await telResp.json();

                if (telData.telemetry && telData.telemetry.length > 0) {
                    datasets.push({
                        label: `${labelPrefix} V${lap.display_number} (${formatTime(lap.lap_time)})`,
                        data: telData.telemetry
                    });
                }
            } catch (err) {
                console.error(`Error loading telemetry for lap ${lap.id}`, err);
            }
        }

        // 6. Update Chart with fixed colors
        if (datasets.length > 0) {
            if (!speedChart) initSpeedChart();
            updateSpeedChart(datasets);
            console.log(`Updated Speed Chart with ${datasets.length} laps (best+last) from Best Session ${bestSession.id}`);
        }

    } catch (e) {
        console.error("Error loading best race comparison:", e);
    }
}

// Helper needed if not present (formatTime might be in common.js but loadBestRaceComparison needs it)
// Checking if formatTime is available globally? Yes, usually common.js provides it.
// BUT loadBestRaceComparison is async and formatTime is sync.
// We'll rely on global formatTime or add fallback.
if (typeof formatTime === 'undefined') {
    window.formatTime = function (seconds) {
        if (!seconds) return '--:--';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        const ms = Math.floor((seconds * 1000) % 1000);
        return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
    };
}

window.loadBestRaceComparison = loadBestRaceComparison;

function updateInputsChart(telemetryData) {
    if (!inputsChart || !telemetryData) return;

    // Resample to 21 points for "Entire Lap" view (consistent with other charts)
    const resolution = 21;
    const sampled = resampleTelemetry(telemetryData, resolution);

    const labels = sampled.map((_, i) => {
        const pct = Math.round((i / resolution) * 100);
        return pct % 5 === 0 ? pct + '%' : '';
    });

    inputsChart.data.labels = labels;
    // Update labels to reflect it's the LAST LAP
    inputsChart.data.datasets[0].label = 'Acelerador (Última)';
    inputsChart.data.datasets[1].label = 'Freno (Última)';

    inputsChart.data.datasets[0].data = sampled.map(d => d.throttle * 100);
    inputsChart.data.datasets[1].data = sampled.map(d => d.brake * 100);

    // Update X axis title
    inputsChart.options.scales.x.title.text = 'Distancia de Vuelta (%)';

    inputsChart.update();
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
});

// Update charts when switching to analysis view
// Store reference to avoid multiple bindings
if (!window.chartViewHandlerAttached) {
    const originalSwitchView = window.switchView;
    window.switchView = function (view) {
        if (typeof originalSwitchView === 'function') {
            originalSwitchView(view);
        }

        if (view === 'analysis' && window.currentSessionId) {
            console.log('Switching to analysis view, initializing charts...');
            // Small delay to ensure DOM is ready and container dimensions are stable
            setTimeout(() => {
                initializeCharts();
                loadChartData(window.currentSessionId);
            }, 50);
        }
    };
    window.chartViewHandlerAttached = true;
}

async function loadHistorySpeedComparison(trackName) {
    if (!trackName) return;
    console.log(`Loading history speed comparison for: ${trackName}`);

    const ctx = document.getElementById('speedComparisonChart');
    if (!ctx) return;

    try {
        // 1. Get all sessions for this track
        const response = await fetch(`/api/history/sessions?track=${encodeURIComponent(trackName)}`);
        const data = await response.json();
        let sessions = data.sessions || [];

        if (sessions.length === 0) {
            console.log("No sessions found for comparison.");
            return;
        }


        // Always add Best Session first
        sessionsToCompare.push({
            session: bestSession,
            label: `🏆 Récord`
        });

        // Add Last Session if different
        if (sessions.length > 0) {
            const lastSession = sessions[0];
            if (lastSession.id !== bestSession.id) {
                sessionsToCompare.push({
                    session: lastSession,
                    label: `🔄 Última`
                });
            } else if (sessions.length > 1) {
                // If last was best, take 2nd last as "Last" comparison? 
                // Or just admit last is best. 
                // User wants "Best" and "Last 2".
                // If Best == Last, then we have [Best/Last, 2nd Last, 3rd Last] 
                // But let's stick to "Last 2 Recorded".
            }
        }

        // We need "Last 2 Sessions".
        // Let's take the first 2 from the sorted list (Last, 2nd Last).
        // Then add Best if it's not in that list.

        const lastTwo = sessions.slice(0, 2);
        const uniqueSessions = new Map();

        // Add Best first (to ensure specific color/order if needed, or just marking)
        uniqueSessions.set(bestSession.id, { session: bestSession, label: '🏆 Récord', isBest: true });

        // Add Last 2
        lastTwo.forEach((s, idx) => {
            let label = idx === 0 ? '🔄 Última' : '⏮️ Penúltima';

            if (uniqueSessions.has(s.id)) {
                // Already added (it's the best). Update label to indicate both?
                // "🏆 Récord (y Última)"
                const entry = uniqueSessions.get(s.id);
                entry.label = `🏆 Récord & ${label}`;
            } else {
                uniqueSessions.set(s.id, { session: s, label: label, isBest: false });
            }
        });

        const finalSessions = Array.from(uniqueSessions.values());

        // 2. Fetch Best Lap Telemetry for each session
        const datasets = [];

        for (const item of finalSessions) {
            const session = item.session;

            // Get best lap of this session
            // We assume backend 'sessions' list might include best_lap_id or we fetch laps.
            // history/sessions response currently has 'best_lap' time but maybe not ID.
            // Let's fetch laps for the session.

            try {
                const lapsResp = await fetch(`/api/sessions/${session.id}/laps`);
                const lapsData = await lapsResp.json();
                const laps = lapsData.laps || [];

                // Find best lap
                const validLaps = laps.filter(l => l.lap_time > 0);
                if (validLaps.length === 0) continue;

                validLaps.sort((a, b) => a.lap_time - b.lap_time);
                const bestLap = validLaps[0];

                // Fetch telemetry
                const telResp = await fetch(`/api/laps/${bestLap.id}/telemetry`);
                const telData = await telResp.json();

                if (telData.telemetry && telData.telemetry.length > 0) {
                    datasets.push({
                        label: `${item.label} (${formatTime(bestLap.lap_time)})`,
                        data: telData.telemetry,
                        isBest: item.isBest
                    });
                }
            } catch (err) {
                console.error("Error fetching comparison data", err);
            }
        }

        // 3. Update speedComparisonChart with datasets
        if (!speedComparisonChart) initSpeedComparisonChart();

        updateSpeedComparisonChartData(datasets);

    } catch (e) {
        console.error("Error loading history speed comparison:", e);
    }
}

function updateSpeedComparisonChartData(datasets) {
    if (!speedComparisonChart) return;

    speedComparisonChart.data.datasets = [];
    speedComparisonChart.data.labels = [];

    const resolution = 200;
    // Colors: Cyan (Best), Pink (Last), Orange (2nd Last)
    const COLORS = ['#00ffff', '#ff0055', '#ffaa00'];

    // Generate labels from 0% to 100%
    const labels = Array.from({ length: resolution + 1 }, (_, i) => {
        const pct = Math.round((i / resolution) * 100);
        return pct % 10 === 0 ? pct + '%' : '';
    });
    speedComparisonChart.data.labels = labels;

    datasets.forEach((ds, index) => {
        const resampled = resampleTelemetry(ds.data, resolution);
        // Use fixed colors based on role if possible, or just index
        // If we strictly ordered finalSessions: [Best, Last, 2nd Last], we can map indices.
        // But map order might vary.

        let color = COLORS[index % COLORS.length];
        if (ds.label.includes('Récord')) color = '#00ffff'; // Cyan
        else if (ds.label.includes('Última')) color = '#ff0055'; // Pink
        else if (ds.label.includes('Penúltima')) color = '#ffaa00'; // Orange

        speedComparisonChart.data.datasets.push({
            label: ds.label,
            data: resampled.map(d => d.speed),
            borderColor: color,
            backgroundColor: color + '10', // 10% opacity
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.4
        });
    });

    speedComparisonChart.update();
}

window.loadHistorySpeedComparison = loadHistorySpeedComparison;

