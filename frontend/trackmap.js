// Track Map Renderer
// Visualizes the circuit layout with performance analysis

class TrackMapRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas with id "${canvasId}" not found`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.trackData = null;
        this.sections = null;
        this.selectedSection = null;

        // Live tracking data
        this.livePositions = [];
        this.liveSpeeds = [];
        this.isLiveMode = false;

        // Canvas dimensions
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.padding = 40;

        // Colors
        this.colors = {
            background: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim(),
            track: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
            liveTrack: '#00D9FF',
            straight: '#4CAF50',
            corner: '#FF9800',
            optimal: '#2196F3',
            suboptimal: '#F44336',
            highlight: '#FFD700'
        };

        // Setup mouse events
        this.setupEvents();
    }

    setupEvents() {
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.handleMouseLeave());
    }

    loadTrackData(trackLayout, sections, sectionRecords = []) {
        this.trackData = trackLayout;
        this.sections = sections;
        this.sectionRecords = sectionRecords;

        // Create a map for quick record lookup
        this.recordsMap = {};
        sectionRecords.forEach(record => {
            this.recordsMap[record.section_id] = record;
        });

        console.log('Track data loaded:', {
            points: trackLayout?.positions?.length,
            sections: sections?.length,
            records: sectionRecords?.length
        });
    }

    startLiveMode() {
        this.isLiveMode = true;
        this.livePositions = [];
        this.liveSpeeds = [];
        console.log('🎬 Live track drawing started');
    }

    stopLiveMode() {
        this.isLiveMode = false;
        console.log('🛑 Live track drawing stopped');
    }

    addPositionPoint(normalizedPos, speed) {
        if (!this.isLiveMode) return;

        this.livePositions.push(normalizedPos);
        this.liveSpeeds.push(speed);

        // Render every 10 points to avoid too many redraws
        if (this.livePositions.length % 10 === 0) {
            this.renderLive();
        }
    }

    clearLiveData() {
        this.livePositions = [];
        this.liveSpeeds = [];
        this.isLiveMode = false;
    }


    render() {
        if (!this.trackData || !this.trackData.positions || this.trackData.positions.length === 0) {
            this.renderNoData();
            return;
        }

        // Clear canvas
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Draw track
        this.drawTrack();

        // Draw sections overlay
        if (this.sections && this.sections.length > 0) {
            this.drawSections();
        }

        // Draw speed heatmap
        this.drawSpeedHeatmap();
    }

    renderLive() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.width, this.height);

        // Draw live track data
        if (this.livePositions.length < 2) {
            this.renderNoData();
            return;
        }

        this.drawLiveTrack();
        this.drawLiveSpeedHeatmap();
    }

    renderNoData() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.fillStyle = this.colors.track;
        this.ctx.font = '16px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('No hay datos de mapa disponibles', this.width / 2, this.height / 2);
    }

    drawTrack() {
        const positions = this.trackData.positions;

        if (!positions || positions.length < 2) return;

        this.ctx.beginPath();
        this.ctx.lineWidth = 8;
        this.ctx.strokeStyle = this.colors.track;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        // Convert normalized positions to canvas coordinates
        const canvasPos = this.normalizedToCanvas(positions[0]);
        this.ctx.moveTo(canvasPos.x, canvasPos.y);

        for (let i = 1; i < positions.length; i++) {
            const pos = this.normalizedToCanvas(positions[i]);
            this.ctx.lineTo(pos.x, pos.y);
        }

        this.ctx.stroke();
    }

    drawLiveTrack() {
        if (!this.livePositions || this.livePositions.length < 2) return;

        this.ctx.beginPath();
        this.ctx.lineWidth = 8;
        this.ctx.strokeStyle = this.colors.liveTrack;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        // Convert normalized positions to canvas coordinates
        const canvasPos = this.normalizedToCanvas(this.livePositions[0]);
        this.ctx.moveTo(canvasPos.x, canvasPos.y);

        for (let i = 1; i < this.livePositions.length; i++) {
            const pos = this.normalizedToCanvas(this.livePositions[i]);
            this.ctx.lineTo(pos.x, pos.y);
        }

        this.ctx.stroke();

        // Draw current position marker
        const lastPos = this.normalizedToCanvas(this.livePositions[this.livePositions.length - 1]);
        this.ctx.beginPath();
        this.ctx.arc(lastPos.x, lastPos.y, 6, 0, Math.PI * 2);
        this.ctx.fillStyle = '#FF0000';
        this.ctx.fill();
    }

    drawLiveSpeedHeatmap() {
        if (!this.livePositions || !this.liveSpeeds || this.livePositions.length < 2) return;

        const maxSpeed = Math.max(...this.liveSpeeds);
        const minSpeed = Math.min(...this.liveSpeeds);

        for (let i = 0; i < this.livePositions.length - 1; i++) {
            const speed = this.liveSpeeds[i];
            const normalizedSpeed = (speed - minSpeed) / (maxSpeed - minSpeed);

            // Color gradient from red (slow) to green (fast)
            const hue = normalizedSpeed * 120; // 0 = red, 120 = green
            const color = `hsl(${hue}, 80%, 50%)`;

            this.ctx.beginPath();
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 4;
            this.ctx.globalAlpha = 0.5;

            const pos1 = this.normalizedToCanvas(this.livePositions[i]);
            const pos2 = this.normalizedToCanvas(this.livePositions[i + 1]);

            this.ctx.moveTo(pos1.x, pos1.y);
            this.ctx.lineTo(pos2.x, pos2.y);
            this.ctx.stroke();
        }

        this.ctx.globalAlpha = 1.0;
    }


    drawSections() {
        if (!this.sections || !this.trackData) return;

        const positions = this.trackData.positions;

        this.sections.forEach((section, index) => {
            const startIdx = section.start_idx;
            const endIdx = section.end_idx;

            // Skip if indices are out of bounds
            if (startIdx >= positions.length || endIdx >= positions.length) return;

            // Check if there's a record for this section
            const record = this.recordsMap[section.section_id];

            // Determine color based on performance vs record
            let color;
            const isSelected = this.selectedSection === index;

            if (record) {
                const performance = section.time / record.best_time;

                if (performance <= 1.0) {
                    // New record or tied
                    color = '#FFD700';  // Gold
                } else if (performance < 1.02) {
                    // Within 2% of record - excellent
                    color = '#00ff88';  // Green
                } else if (performance < 1.05) {
                    // Within 5% of record - good
                    color = '#4CAF50';  // Light green
                } else {
                    // More than 5% off record - needs improvement
                    color = '#FF6B6B';  // Red
                }
            } else {
                // No record yet - use default colors
                color = section.type === 'straight' ? this.colors.straight : this.colors.corner;
            }

            this.ctx.beginPath();
            this.ctx.lineWidth = isSelected ? 12 : 6;
            this.ctx.strokeStyle = isSelected ? this.colors.highlight : color;
            this.ctx.globalAlpha = isSelected ? 1.0 : 0.7;
            this.ctx.lineCap = 'round';
            this.ctx.lineJoin = 'round';

            const startPos = this.normalizedToCanvas(positions[startIdx]);
            this.ctx.moveTo(startPos.x, startPos.y);

            for (let i = startIdx + 1; i <= endIdx && i < positions.length; i++) {
                const pos = this.normalizedToCanvas(positions[i]);
                this.ctx.lineTo(pos.x, pos.y);
            }

            this.ctx.stroke();
            this.ctx.globalAlpha = 1.0;

            // Draw section number at midpoint
            if (!isSelected) {
                const midIdx = Math.floor((startIdx + endIdx) / 2);
                if (midIdx < positions.length) {
                    const midPos = this.normalizedToCanvas(positions[midIdx]);
                    this.drawSectionLabel(midPos.x, midPos.y, section.section_id);
                }
            }
        });
    }

    drawSectionLabel(x, y, sectionId) {
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 3;
        this.ctx.font = 'bold 14px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        const text = sectionId.toString();
        this.ctx.strokeText(text, x, y);
        this.ctx.fillText(text, x, y);
    }

    drawSpeedHeatmap() {
        if (!this.trackData || !this.trackData.speeds) return;

        const positions = this.trackData.positions;
        const speeds = this.trackData.speeds;

        const maxSpeed = Math.max(...speeds);
        const minSpeed = Math.min(...speeds);

        for (let i = 0; i < positions.length - 1; i++) {
            const speed = speeds[i];
            const normalizedSpeed = (speed - minSpeed) / (maxSpeed - minSpeed);

            // Color gradient from red (slow) to green (fast)
            const hue = normalizedSpeed * 120; // 0 = red, 120 = green
            const color = `hsl(${hue}, 80%, 50%)`;

            this.ctx.beginPath();
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 4;
            this.ctx.globalAlpha = 0.5;

            const pos1 = this.normalizedToCanvas(positions[i]);
            const pos2 = this.normalizedToCanvas(positions[i + 1]);

            this.ctx.moveTo(pos1.x, pos1.y);
            this.ctx.lineTo(pos2.x, pos2.y);
            this.ctx.stroke();
        }

        this.ctx.globalAlpha = 1.0;
    }

    normalizedToCanvas(normalizedPos) {
        // Convert normalized [0-1] coordinates to canvas coordinates
        const x = this.padding + normalizedPos[0] * (this.width - 2 * this.padding);
        const y = this.padding + normalizedPos[1] * (this.height - 2 * this.padding);
        return { x, y };
    }

    canvasToNormalized(canvasX, canvasY) {
        // Convert canvas coordinates to normalized [0-1]
        const normX = (canvasX - this.padding) / (this.width - 2 * this.padding);
        const normY = (canvasY - this.padding) / (this.height - 2 * this.padding);
        return [normX, normY];
    }

    handleMouseMove(e) {
        if (!this.sections || !this.trackData) return;

        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Find nearest section
        let nearestSection = null;
        let minDistance = Infinity;

        this.sections.forEach((section, index) => {
            const midIdx = Math.floor((section.start_idx + section.end_idx) / 2);
            if (midIdx < this.trackData.positions.length) {
                const midPos = this.normalizedToCanvas(this.trackData.positions[midIdx]);
                const distance = Math.sqrt(
                    Math.pow(mouseX - midPos.x, 2) + Math.pow(mouseY - midPos.y, 2)
                );

                if (distance < minDistance && distance < 50) {
                    minDistance = distance;
                    nearestSection = index;
                }
            }
        });

        if (nearestSection !== this.selectedSection) {
            this.selectedSection = nearestSection;
            this.render();

            if (nearestSection !== null) {
                this.showSectionInfo(this.sections[nearestSection]);
            } else {
                this.hideSectionInfo();
            }
        }
    }

    handleMouseLeave() {
        if (this.selectedSection !== null) {
            this.selectedSection = null;
            this.render();
            this.hideSectionInfo();
        }
    }

    showSectionInfo(section) {
        const infoPanel = document.getElementById('sectionInfo');
        if (!infoPanel) return;

        document.getElementById('sectionName').textContent = `Sección ${section.section_id}`;
        document.getElementById('sectionType').textContent =
            section.type === 'straight' ? 'Recta' : 'Curva';
        document.getElementById('sectionAvgSpeed').textContent = `${section.avg_speed} km/h`;
        document.getElementById('sectionMaxSpeed').textContent = `${section.max_speed} km/h`;
        document.getElementById('sectionTime').textContent = `${section.time}s`;

        // Add record comparison if available
        const record = this.recordsMap[section.section_id];
        let recordInfo = document.getElementById('sectionRecordInfo');

        if (!recordInfo) {
            // Create record info element if it doesn't exist
            recordInfo = document.createElement('div');
            recordInfo.id = 'sectionRecordInfo';
            recordInfo.className = 'section-record-info';
            infoPanel.querySelector('.section-stats').appendChild(recordInfo);
        }

        if (record) {
            const delta = section.time - record.best_time;
            const performance = section.time / record.best_time;

            let statusIcon, statusText, statusClass;
            if (delta <= 0) {
                statusIcon = '🏆';
                statusText = '¡Nuevo récord!';
                statusClass = 'record-new';
            } else if (performance < 1.02) {
                statusIcon = '💚';
                statusText = `+${delta.toFixed(3)}s (Excelente)`;
                statusClass = 'record-excellent';
            } else if (performance < 1.05) {
                statusIcon = '💛';
                statusText = `+${delta.toFixed(3)}s (Bueno)`;
                statusClass = 'record-good';
            } else {
                statusIcon = '❤️';
                statusText = `+${delta.toFixed(3)}s (Mejorable)`;
                statusClass = 'record-poor';
            }

            recordInfo.innerHTML = `
                <div class="stat ${statusClass}">
                    <span class="label">${statusIcon} vs Récord:</span>
                    <span>${statusText}</span>
                </div>
            `;
        } else {
            recordInfo.innerHTML = `
                <div class="stat record-first">
                    <span class="label">🆕 Primer récord</span>
                </div>
            `;
        }

        infoPanel.classList.remove('hidden');
    }

    hideSectionInfo() {
        const infoPanel = document.getElementById('sectionInfo');
        if (infoPanel) {
            infoPanel.classList.add('hidden');
        }
    }
}

// Export for use in app.js
window.TrackMapRenderer = TrackMapRenderer;
