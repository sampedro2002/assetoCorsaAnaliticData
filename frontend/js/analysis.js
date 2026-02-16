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
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function renderTelemetryChart(telemetry) {
    const ctx = document.getElementById('telemetryChartMain');
    if (!ctx) return;

    // Simple verification content for now
    // In a real scenario, we parse the telemetry arrays (speed, rpm, time)
    // new Chart(ctx, { ... });
}
