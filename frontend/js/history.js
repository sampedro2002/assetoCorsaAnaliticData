// History View Logic
console.log("📜 History JS loaded");

document.addEventListener('DOMContentLoaded', () => {
    loadTrackList();

    const backBtn = document.getElementById('backToTracksBtn');
    if (backBtn) {
        backBtn.addEventListener('click', showTrackList);
    }
});

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

async function loadTrackHistory(trackName) {
    // Hide list, show dashboard
    document.getElementById('trackSelectionContainer').classList.add('hidden');
    document.getElementById('trackHistoryDashboard').classList.remove('hidden');
    document.getElementById('selectedTrackTitle').textContent = `ANÁLISIS: ${trackName}`;

    const listContainer = document.getElementById('sessionList');
    listContainer.innerHTML = '<p class="loading">Cargando sesiones...</p>';

    try {
        const response = await fetch(`/api/history/sessions?track=${encodeURIComponent(trackName)}`);
        const data = await response.json();
        const sessions = data.sessions || [];

        listContainer.innerHTML = '';
        if (sessions.length === 0) {
            listContainer.innerHTML = '<p>No hay sesiones registradas para esta pista.</p>';
            return;
        }

        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item panel-row';
            item.style.padding = '10px';
            item.style.borderBottom = '1px solid #333';
            item.style.display = 'flex';
            item.style.justifyContent = 'space-between';
            item.style.alignItems = 'center';

            const date = new Date(session.date).toLocaleString();

            item.innerHTML = `
                <div>
                    <strong>${translateSessionType(session.type)}</strong>
                    <span style="color:#aaa; font-size:0.9em; margin-left:10px;">${date}</span>
                </div>
                <div style="display:flex; gap:15px; align-items:center;">
                    <span class="highlight">${formatTime(session.best_lap)}</span>
                    <a href="/analysis?session_id=${session.id}" class="nav-btn" style="padding:4px 10px; font-size:0.8em;">Ver Análisis</a>
                </div>
            `;
            listContainer.appendChild(item);
        });

        // Render charts if needed
        if (window.initHistoryCharts) {
            window.initHistoryCharts();
        }

        if (window.updateRacePaceChart) {
            // We need laps for the chart. The sessions endpoint returns session summaries.
            // We'll use the 'best_lap' data from sessions to plot progress over sessions.
            // OR, if we want detailed lap times for a specific session, that's different.
            // The Race Pace Chart in history view usually shows trend of best laps over sessions.

            const chartData = sessions.map(s => ({
                lap_number: s.id, // Using Session ID as X-axis for now, or index
                lap_time: s.best_lap * 1000 // Convert back to ms for uniformity
            })).reverse(); // Oldest first

            // Remap to match expected format
            const formattedData = chartData.map((d, i) => ({
                lap_number: i,
                lap_time: d.lap_time
            }));

            window.updateRacePaceChart(formattedData);
        }

        // 2. Last Races Chart: Speed Comparison of last 3 races
        try {
            const analysisResponse = await fetch(`/api/history/${encodeURIComponent(trackName)}`);
            const analysisData = await analysisResponse.json();

            if (analysisData.available && window.updateLastRacesChart) {
                window.updateLastRacesChart(analysisData.speed_comparison);
            }
        } catch (err) {
            console.error("Error loading track analysis for charts:", err);
        }

        // 3. Last Laps Chart: Speed Comparison of last 3 laps (Latest Session)
        if (sessions.length > 0 && window.updateLastLapsChart) {
            // Get latest session (sessions are ordered by date desc in backend usually, but here likely newest first?)
            // In createTrackCard, sessions_count is used.
            // In loadTrackHistory, sessions are iterated.
            // Let's assume the first one in the list is the newest, or check dates.
            // The API /api/history/sessions returns list. Usually DB returns newest first.
            const latestSession = sessions[0];

            try {
                const lapsResponse = await fetch(`/api/history/sessions/${latestSession.id}/last-laps`);
                const lapsData = await lapsResponse.json();

                if (lapsData.available) {
                    window.updateLastLapsChart(lapsData);
                }
            } catch (err) {
                console.error("Error loading last laps analysis:", err);
            }
        }

    } catch (error) {
        console.error("Error loading sessions", error);
        listContainer.innerHTML = '<p class="error">Error al cargar sesiones.</p>';
    }
}

function showTrackList() {
    document.getElementById('trackHistoryDashboard').classList.add('hidden');
    document.getElementById('trackSelectionContainer').classList.remove('hidden');
}
