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
        const response = await fetch('/api/history/tracks'); // Adjust API endpoint as needed
        const tracks = await response.json();

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
        const sessions = await response.json();

        listContainer.innerHTML = '';
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

        // Render charts if needed (omitted for brevity, can be added)

    } catch (error) {
        console.error("Error loading sessions", error);
        listContainer.innerHTML = '<p class="error">Error al cargar sesiones.</p>';
    }
}

function showTrackList() {
    document.getElementById('trackHistoryDashboard').classList.add('hidden');
    document.getElementById('trackSelectionContainer').classList.remove('hidden');
}
