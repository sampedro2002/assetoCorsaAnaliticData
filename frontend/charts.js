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
                    ticks: { display: false } // Hide index numbers
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
                    ticks: { display: false }
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

    // Reset datasets
    lastRacesChart.data.datasets = [];
    lastRacesChart.data.labels = [];

    // Colors for different races
    const colors = ['#00ffff', '#ff0055', '#00ff88', '#ffff00'];

    if (speedComparisonData.length > 0) {
        // Use the first dataset to set labels (assuming all are approx same length/normalized)
        // or just use 0-100%
        const pointsCount = speedComparisonData[0].data.length;
        lastRacesChart.data.labels = Array.from({ length: pointsCount }, (_, i) => i);
    }

    speedComparisonData.forEach((session, index) => {
        const color = colors[index % colors.length];

        lastRacesChart.data.datasets.push({
            label: session.label,
            data: session.data.map(p => p.y), // p.y is speed
            borderColor: color,
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.4
        });
    });

    lastRacesChart.update();
}

function updateLastLapsChart(lapsData) {
    if (!lastLapsChart || !lapsData) return;

    // Reset datasets
    lastLapsChart.data.datasets = [];
    lastLapsChart.data.labels = [];

    // Colors for different laps
    const colors = ['#00ffff', '#ff0055', '#00ff88', '#ffff00'];

    // Check if we have speed comparison data (new format)
    if (lapsData.speed_comparison && lapsData.speed_comparison.length > 0) {
        const speedData = lapsData.speed_comparison;

        // Use first dataset for labels
        const pointsCount = speedData[0].data.length;
        lastLapsChart.data.labels = Array.from({ length: pointsCount }, (_, i) => i);

        speedData.forEach((lap, index) => {
            const color = colors[index % colors.length];

            lastLapsChart.data.datasets.push({
                label: lap.label,
                data: lap.data.map(p => p.y), // p.y is speed
                borderColor: color,
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            });
        });

        // Update Chart Title or Axis if needed? 
        // options are already set for Speed in init

    } else if (lapsData.times) {
        // Fallback to old Bar Chart logic if speed data missing?
        // But we changed init to Line chart... so we should probably stick to line.
        // If no telemetry, we can't show speed trace.
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

        let validLaps = completeLaps.filter(l => l.is_valid);

        // Fallback to all complete laps if no valid ones exist
        if (validLaps.length === 0) {
            console.warn('No valid laps found for charts, using all complete laps');
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

        // DEBUG: Log telemetry data structure
        console.log('📊 Best Telemetry:', {
            length: bestTelemetry.telemetry?.length || 0,
            firstPoint: bestTelemetry.telemetry?.[0],
            hasNormalizedPosition: bestTelemetry.telemetry?.[0]?.normalized_position !== undefined
        });
        console.log('📊 Last Telemetry:', {
            length: lastTelemetry.telemetry?.length || 0,
            firstPoint: lastTelemetry.telemetry?.[0],
            hasNormalizedPosition: lastTelemetry.telemetry?.[0]?.normalized_position !== undefined
        });

        // Update speed chart
        updateSpeedChart(bestTelemetry.telemetry, lastTelemetry.telemetry);

        // Update inputs chart
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
function resampleTelemetry(telemetryData, targetPoints = 100) {
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

function updateSpeedChart(bestData, lastData) {
    if (!speedChart || !bestData || !lastData) return;

    // Resample both to 200 points (0% to 100%) for perfect alignment
    const resolution = 200;
    const bestResampled = resampleTelemetry(bestData, resolution);
    const lastResampled = resampleTelemetry(lastData, resolution);

    // DEBUG: Log resampled data
    console.log('📈 Speed Chart Data:', {
        bestResampledLength: bestResampled.length,
        lastResampledLength: lastResampled.length,
        bestSample: bestResampled.slice(0, 5).map(d => d.speed),
        lastSample: lastResampled.slice(0, 5).map(d => d.speed)
    });

    // Generate labels (0% to 100%)
    const labels = bestResampled.map((_, i) => {
        // Show label every 10%
        const pct = Math.round((i / resolution) * 100);
        return pct % 5 === 0 ? pct + '%' : '';
    });

    speedChart.data.labels = labels;
    speedChart.data.datasets[0].data = bestResampled.map(d => d.speed);
    speedChart.data.datasets[1].data = lastResampled.map(d => d.speed);

    // Update X axis title
    speedChart.options.scales.x.title.text = 'Distancia de Vuelta (%)';

    speedChart.update();
}

function updateInputsChart(telemetryData) {
    if (!inputsChart || !telemetryData) return;

    // Resample to 200 points for "Entire Lap" view
    const resolution = 200;
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
