// Analysis View Logic
console.log("📊 Analysis JS loaded");

document.addEventListener('DOMContentLoaded', () => {
    // Check URL params
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');

    loadAnalysis(sessionId);

    // Setup Tabs
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Add to current
            tab.classList.add('active');
            const contentId = tab.dataset.tab + 'Tab';
            document.getElementById(contentId).classList.add('active');
        });
    });
});

async function loadAnalysis(sessionId) {
    try {
        const url = sessionId
            ? `/api/analysis/session/${sessionId}`
            : `/api/analysis/latest`;

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch data");

        const data = await response.json();
        renderAnalysis(data);

    } catch (error) {
        console.error("Error loading analysis", error);
        document.querySelector('.session-summary').innerHTML = `<p class="error">No se pudieron cargar los datos de la sesión.</p>`;
    }
}

function renderAnalysis(data) {
    if (!data || !data.session) return;

    // 1. Summary
    const s = data.session;
    setText('summarySessionType', translateSessionType(s.type));
    setText('summaryTrack', s.track);
    setText('summaryCar', s.car);
    setText('summaryLaps', s.total_laps);
    setText('summaryBestLap', formatTime(s.best_lap));

    // 2. Laps Table
    const tbody = document.querySelector('#lapsTable tbody');
    if (tbody && data.laps) {
        tbody.innerHTML = '';
        data.laps.forEach(lap => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${lap.lap_number}</td>
                <td class="${lap.is_best ? 'highlight' : ''}">${formatTime(lap.time)}</td>
                <td>${formatTime(lap.sectors[0])}</td>
                <td>${formatTime(lap.sectors[1])}</td>
                <td>${formatTime(lap.sectors[2])}</td>
                <td>${lap.is_valid ? '✅' : '❌'}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // 3. AI Recommendations
    const recList = document.getElementById('recommendationsList');
    if (recList && data.recommendations) {
        recList.innerHTML = '';
        data.recommendations.forEach(rec => {
            const div = document.createElement('div');
            div.className = 'recommendation-item';
            div.textContent = rec;
            // Add icon
            // div.innerHTML = `<span class="icon">💡</span> ${rec}`;
            recList.appendChild(div);
        });
    }

    // 4. Telemetry Chart
    if (data.telemetry) {
        renderTelemetryChart(data.telemetry);
    }

    // 5. Track Map
    if (data.analysis && data.analysis.track_sections && data.session) {
        // Find best lap or last lap to use for map geometry
        // We need actual telemetry points to draw the map
        const bestLap = data.laps.find(l => l.is_best) || data.laps[data.laps.length - 1];
        if (bestLap) {
            loadAndRenderMap(bestLap.id, data.analysis.track_sections);
            // 6. Volante Chart (New)
            loadAndRenderSteeringChart(bestLap.id);
        }
    }

    // 7. Load Volante Stats
    loadVolanteStats(data.session.id);
}

let trackMapRenderer = null;

async function loadAndRenderMap(lapId, sections) {
    try {
        const response = await fetch(`/api/laps/${lapId}/telemetry`);
        if (!response.ok) return;

        const data = await response.json();
        if (!data.telemetry || data.telemetry.length === 0) return;

        // Prepare track layout from telemetry
        const trackLayout = {
            positions: data.telemetry.map(p => [p.normalized_position, 0.5]), // Fallback if no coord
            // Ideally we need x,z but TrackMapRenderer might expect normalized or world?
            // Let's check TrackMapRenderer. It expects 'positions' array.
            // If it uses normalizedToCanvas, it expects [0-1], [0-1].
            // Our telemetry has pos_x, pos_z. We need to normalize them.
            // Or if TrackMapRenderer expects normalized car position along track (scalar)?
            // app.js passes: positions.push(data.normalized_position) ?? No.
            // Let's check app.js or TrackMapRenderer.
        };

        // Re-reading TrackMapRenderer: 
        // drawTrack() iterates positions and calls this.normalizedToCanvas(positions[i])
        // normalizedToCanvas takes [x, y].
        // So we need 2D normalized coordinates.
        // We can compute bounding box of pos_x, pos_z and normalize.

        const coords = data.telemetry.map(p => ({ x: p.pos_x, z: p.pos_z }));
        const minX = Math.min(...coords.map(c => c.x));
        const maxX = Math.max(...coords.map(c => c.x));
        const minZ = Math.min(...coords.map(c => c.z));
        const maxZ = Math.max(...coords.map(c => c.z));

        const rangeX = maxX - minX || 1;
        const rangeZ = maxZ - minZ || 1;

        // Normalize to 0-1 (keeping aspect ratio? TrackMapRenderer stretches to canvas)
        // trackmap.js simple scaling:
        // const x = this.padding + normalizedPos[0] * (this.width - 2 * this.padding);

        const normalizedPositions = coords.map(c => [
            (c.x - minX) / rangeX,
            (c.z - minZ) / rangeZ
        ]);

        const speeds = data.telemetry.map(p => p.speed);

        if (!trackMapRenderer) {
            trackMapRenderer = new TrackMapRenderer('trackMapCanvas');
        }

        trackMapRenderer.loadTrackData(
            { positions: normalizedPositions, speeds: speeds },
            sections
        );
        trackMapRenderer.render();

    } catch (e) {
        console.error("Error loading map telemetry:", e);
    }
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function renderTelemetryChart(telemetry) {
    const ctx = document.getElementById('telemetryChartMain');
    if (!ctx) return;

    // Check if chart already exists
    if (window.mainTelemetryChart instanceof Chart) {
        window.mainTelemetryChart.destroy();
    }
}

// --- New Steering Analysis Logic ---

async function loadVolanteStats(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}/volante`);
        if (!response.ok) return;
        const data = await response.json();
        const stats = data.stats;

        if (stats) {
            setText('maxSteeringAngle', formatValue(stats.max_steering_angle, 1, '°'));
            setText('maxAngularVelocity', formatValue(stats.max_angular_velocity, 1, '°/s'));
            setText('maxAngularAcceleration', formatValue(stats.max_angular_acceleration, 1, '°/s²'));
            // Fix: Database returns avg_brake_usage (alias for percentage)
            setText('avgBrakeUsage', formatValue(stats.avg_brake_usage, 1, '%'));
        }
    } catch (e) {
        console.error("Error loading volante stats:", e);
    }
}

function formatValue(val, decimals, unit) {
    if (val === undefined || val === null) return '--';
    return Number(val).toFixed(decimals) + unit;
}

let steeringChartInstance = null;

async function loadAndRenderSteeringChart(lapId) {
    try {
        const response = await fetch(`/api/laps/${lapId}/volante`);
        if (!response.ok) return;
        const data = await response.json();

        if (data.volante_data && data.volante_data.length > 0) {
            renderSteeringChart(data.volante_data);
        }
    } catch (e) {
        console.error("Error loading steering chart:", e);
    }
}

function renderSteeringChart(data) {
    const ctx = document.getElementById('steeringAnalysisChart');
    if (!ctx) return;

    if (steeringChartInstance) {
        steeringChartInstance.destroy();
    }

    // Normalize timestamps to start at 0
    const startTime = data[0].timestamp;
    const timestamps = data.map(d => (d.timestamp - startTime).toFixed(2));
    const steeringAngles = data.map(d => d.steering_angle);
    const angularVelocities = data.map(d => d.angular_velocity);

    steeringChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [
                {
                    label: 'Ángulo de Dirección (°)',
                    data: steeringAngles,
                    borderColor: '#00ffff',
                    borderWidth: 2,
                    yAxisID: 'y',
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: 'Velocidad Angular (°/s)',
                    data: angularVelocities,
                    borderColor: '#ff00ff',
                    borderWidth: 1,
                    yAxisID: 'y1',
                    pointRadius: 0,
                    tension: 0.1,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    type: 'linear',
                    display: true,
                    title: { display: true, text: 'Tiempo (s)', color: '#888' },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#888' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Grados (°)', color: '#00ffff' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#ccc' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Velocidad (°/s)', color: '#ff00ff' },
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#ccc' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#fff' }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}
