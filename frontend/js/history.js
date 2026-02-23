// History View Logic
console.log("📜 History JS loaded");

// ─── Module state ──────────────────────────────────────────────────────────
let _annotatedMapRenderer = null;  // AnnotatedMapRenderer instance (lazy init)
let _annotatedMapData = null;   // { sessions: [...], track_map_image: ... }

// ─── Initialisation ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadTrackList();

    const backBtn = document.getElementById('backToTracksBtn');
    if (backBtn) backBtn.addEventListener('click', showTrackList);
});

// ══════════════════════════════════════════════════════════════════════════════
// TRACK LIST
// ══════════════════════════════════════════════════════════════════════════════
async function loadTrackList() {
    const container = document.getElementById('trackList');
    if (!container) return;

    try {
        const response = await fetch('/api/history/tracks');
        const data = await response.json();
        const tracks = data.tracks || [];

        container.innerHTML = '';

        if (tracks.length === 0) {
            container.innerHTML = '<p>No hay historial disponible.</p>';
            return;
        }

        tracks.forEach(track => {
            const card = createTrackCard(track);
            container.appendChild(card);
        });
    } catch (error) {
        console.error("Error loading tracks:", error);
        container.innerHTML = '<p class="error">Error al cargar historial.</p>';
    }
}

function createTrackCard(track) {
    const div = document.createElement('div');
    div.className = 'track-card panel';
    div.style.cursor = 'pointer';
    div.innerHTML = `
        <div class="track-info">
            <h3>${track.name}</h3>
            <p>${track.sessions_count} sesiones</p>
            <p class="highlight">Mejor: ${formatTime(track.best_lap)}</p>
        </div>
    `;
    div.addEventListener('click', () => loadTrackHistory(track.name));
    return div;
}

// ══════════════════════════════════════════════════════════════════════════════
// TRACK HISTORY DASHBOARD
// ══════════════════════════════════════════════════════════════════════════════
async function loadTrackHistory(trackName) {
    // Show dashboard, hide track-list
    document.getElementById('trackSelectionContainer').classList.add('hidden');
    document.getElementById('trackHistoryDashboard').classList.remove('hidden');
    document.getElementById('selectedTrackTitle').textContent = `ANÁLISIS: ${trackName}`;

    const listContainer = document.getElementById('sessionList');
    listContainer.innerHTML = '<p class="loading">Cargando sesiones...</p>';

    // ── Reset annotated map state ──────────────────────────────────────────
    _annotatedMapData = null;
    if (_annotatedMapRenderer) _annotatedMapRenderer.clear();
    document.getElementById('annotatedMapPanel').style.display = 'none';

    try {
        // 1. Session list
        const sessResp = await fetch(`/api/history/sessions?track=${encodeURIComponent(trackName)}`);
        const sessData = await sessResp.json();
        const sessions = sessData.sessions || [];

        listContainer.innerHTML = '';
        if (sessions.length === 0) {
            listContainer.innerHTML = '<p>No hay sesiones registradas para esta pista.</p>';
        } else {
            sessions.forEach(session => {
                const item = document.createElement('div');
                item.className = 'session-item panel-row';
                item.style.cssText = 'padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center;';

                const date = new Date(session.date).toLocaleString();
                item.innerHTML = `
                    <div>
                        <strong>${translateSessionType(session.type)}</strong>
                        <span style="color:#aaa;font-size:.9em;margin-left:10px;">${date}</span>
                    </div>
                    <div style="display:flex;gap:15px;align-items:center;">
                        <span class="highlight">${formatTime(session.best_lap)}</span>
                        <a href="/analysis?session_id=${session.id}" class="nav-btn" style="padding:4px 10px;font-size:.8em;">Ver Análisis</a>
                    </div>
                `;
                listContainer.appendChild(item);
            });
        }

        // 2. Charts – init
        if (window.initHistoryCharts) window.initHistoryCharts();

        // 3. Race-pace chart (simple best-lap-per-session trend)
        if (window.updateRacePaceChart) {
            const chartData = sessions.map((s, i) => ({
                lap_number: i,
                lap_time: s.best_lap * 1000
            })).reverse();
            window.updateRacePaceChart(chartData);
        }

        // 4. Last-Races speed comparison chart
        try {
            const analysisResp = await fetch(`/api/history/${encodeURIComponent(trackName)}`);
            const analysisData = await analysisResp.json();
            if (analysisData.available && window.updateLastRacesChart) {
                window.updateLastRacesChart(analysisData.speed_comparison);
            }
        } catch (err) {
            console.error("Error loading race analysis charts:", err);
        }

        // 5. Last-Laps speed comparison chart (latest session)
        if (sessions.length > 0 && window.updateLastLapsChart) {
            try {
                const lapsResp = await fetch(`/api/history/sessions/${sessions[0].id}/last-laps`);
                const lapsData = await lapsResp.json();
                if (lapsData.available) window.updateLastLapsChart(lapsData);
            } catch (err) {
                console.error("Error loading last laps analysis:", err);
            }
        }

        // 6. History Speed Comparison (Best + Last 2 Races)
        if (window.loadHistorySpeedComparison) {
            window.loadHistorySpeedComparison(trackName);
        }

        // 7. Annotated map (async, non-blocking)
        loadAnnotatedMap(trackName);

    } catch (error) {
        console.error("Error loading sessions", error);
        listContainer.innerHTML = '<p class="error">Error al cargar sesiones.</p>';
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// ANNOTATED MAP
// ══════════════════════════════════════════════════════════════════════════════
async function loadAnnotatedMap(trackName) {
    const panel = document.getElementById('annotatedMapPanel');
    const noDataDiv = document.getElementById('annotatedMapNoData');
    const tabsWrapper = document.getElementById('annotatedMapTabs');

    try {
        const resp = await fetch(`/api/history/${encodeURIComponent(trackName)}/annotated-map`);
        const data = await resp.json();

        if (!data.available || !data.sessions || data.sessions.length === 0) {
            noDataDiv.style.display = 'block';
            panel.style.display = 'block';
            return;
        }

        _annotatedMapData = data;

        // Show panel
        panel.style.display = 'block';
        noDataDiv.style.display = 'none';

        // Build session tabs (most–recent first = data.sessions order)
        tabsWrapper.innerHTML = '';
        data.sessions.forEach((session, idx) => {
            const tab = document.createElement('button');
            tab.className = 'session-tab' + (idx === 0 ? ' active' : '');
            tab.id = `mapTab_${session.session_id}`;
            tab.textContent = `Sesión ${_fmtDate(session.date)} · ${_fmtLapTime(session.best_lap_time)}`;
            tab.dataset.idx = idx;
            tab.addEventListener('click', () => selectAnnotatedSession(idx, trackName));
            tabsWrapper.appendChild(tab);
        });

        // Render first session
        selectAnnotatedSession(0, trackName);

    } catch (err) {
        console.error("Error loading annotated map:", err);
        noDataDiv.style.display = 'block';
        panel.style.display = 'block';
    }
}

function selectAnnotatedSession(idx, trackName) {
    if (!_annotatedMapData) return;
    const data = _annotatedMapData;
    const session = data.sessions[idx];
    if (!session) return;

    // Update active tab
    document.querySelectorAll('.session-tab').forEach(t => t.classList.remove('active'));
    const activeTab = document.querySelector(`[data-idx="${idx}"].session-tab`);
    if (activeTab) activeTab.classList.add('active');

    // Lazy-init renderer
    if (!_annotatedMapRenderer) {
        _annotatedMapRenderer = new AnnotatedMapRenderer('annotatedMapCanvas');
    }

    // Render the canvas
    _annotatedMapRenderer.render(session, trackName);

    // Update quick-stats bar
    const infoDiv = document.getElementById('mapSessionInfo');
    if (infoDiv) {
        const cornerCount = session.sections.filter(s => s.type === 'corner').length;
        const straightCount = session.sections.filter(s => s.type === 'straight').length;
        const avgSpeed = session.sections.length
            ? Math.round(session.sections.reduce((a, s) => a + s.avg_speed, 0) / session.sections.length)
            : '--';

        infoDiv.innerHTML = `
            <div class="map-session-stat">
                <span class="label">Sesión:</span>
                <span class="value">${session.date}</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Mejor vuelta:</span>
                <span class="value">${_fmtLapTime(session.best_lap_time)}</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Total vueltas:</span>
                <span class="value">${session.total_laps}</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Curvas:</span>
                <span class="value">${cornerCount}</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Rectas:</span>
                <span class="value">${straightCount}</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Vel. media:</span>
                <span class="value">${avgSpeed} km/h</span>
            </div>
            <div class="map-session-stat">
                <span class="label">Auto:</span>
                <span class="value">${session.car_name || '—'}</span>
            </div>
        `;
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════════════
function showTrackList() {
    document.getElementById('trackHistoryDashboard').classList.add('hidden');
    document.getElementById('trackSelectionContainer').classList.remove('hidden');
}

/** Format lap time in seconds as M:SS.mmm */
function _fmtLapTime(sec) {
    if (!sec || sec <= 0) return '--:--.---';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.round((sec % 1) * 1000);
    return `${m}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

/** Shorten a datetime string for the tab label */
function _fmtDate(dateStr) {
    if (!dateStr) return '';
    // e.g. "18/02/2026 17:55" → "18/02 17:55"
    return dateStr.replace(/\/\d{4}/, '').trim();
}
