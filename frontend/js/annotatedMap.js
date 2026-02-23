/**
 * AnnotatedMapRenderer v2.0
 * Draws the AC track map PNG as background, overlays the speed heatmap,
 * and places 10 numbered "checkpoint" dots (P1–P10) equidistant along the lap.
 */
class AnnotatedMapRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');

        // Fix canvas pixel size to match display size
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width || 1200;
        this.canvas.height = rect.height || 440;

        this._sessionData = null;
        this._mapImg = null;
        this._mapLoaded = false;
        this._tooltipPoint = null;   // label of hovered point

        this._palette = [
            '#00d4ff', '#ff4466', '#00ff88', '#ffaa00', '#aa44ff',
            '#ff6600', '#44aaff', '#ff00cc', '#aaff00', '#ff8844',
            '#00ffcc', '#ff2244', '#66ff00', '#ffcc00', '#8844ff',
            '#ff4400', '#00aaff', '#ee00ff', '#ccff00', '#ff6644'
        ];



        this.canvas.addEventListener('mousemove', e => this._onMove(e));
        this.canvas.addEventListener('mouseleave', () => {
            this._tooltipPoint = null;
            this._redraw();
        });
    }

    // ── Public API ────────────────────────────────────────────────────────────

    render(sessionData, trackName) {
        this._sessionData = sessionData;
        this._tooltipPoint = null;
        this._currentTrackName = trackName || 'unknown';

        // 1. Resolve Track Config
        // If trackName contains '@', split it: track@layout -> track_layout (common AC convention)
        let resolvedName = this._currentTrackName.replace('@', '_');

        // Load specific config or default dynamic path
        const config = typeof getTrackConfig !== 'undefined' ? getTrackConfig(resolvedName) : { image: `/static/assets/tracks/${resolvedName}.png` };
        const imagePath = config.image;

        // Resize canvas if needed
        const rect = this.canvas.getBoundingClientRect();
        const W = rect.width || 1200;
        const H = rect.height || 440;
        if (this.canvas.width !== W || this.canvas.height !== H) {
            this.canvas.width = W;
            this.canvas.height = H;
        }

        // 2. Load Image Only on Change
        if (imagePath !== this._lastMapSrc) {
            this._lastMapSrc = imagePath;
            this._mapLoaded = false;
            const img = new Image();
            img.onload = () => {
                this._mapImg = img;
                this._mapLoaded = true;
                this._redraw();
            };
            img.onerror = () => {
                console.warn(`Map image not found: ${imagePath}. Creating placeholder.`);
                this._mapImg = null; // Use dark fallback
                this._mapLoaded = false;
                this._redraw();
            };
            // Append timestamp to prevent caching
            img.src = imagePath + '?t=' + new Date().getTime();
        } else {
            this._redraw();
        }
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    _getPoints() {
        const d = this._sessionData;
        if (!d) return [];
        // Support both new shape (points[]) and legacy (sections[])
        return (d.points && d.points.length ? d.points : d.sections) || [];
    }

    _toCanvas(normXZ) {
        // Map normalized [0,1] coordinates to the image drawing area
        // This ensures points align with the map image
        const rect = this._getDrawRect();

        // Transform normalized coords based on rotation
        let u = normXZ[0];
        let v = normXZ[1];

        if (rect.isRotated) {
            // Rotation -90 deg (Counter-Clockwise)
            // Old (0,0) [Top-Left] -> New (0,1) [Bottom-Left]
            // Old (1,0) [Top-Right] -> New (0,0) [Top-Left]
            // Formula: u' = v, v' = 1 - u
            const oldU = u;
            u = v;
            v = 1 - oldU;
        }

        return {
            x: rect.x + u * rect.w,
            y: rect.y + v * rect.h
        };
    }

    _getDrawRect() {
        // Calculate the rectangle where the track/map is drawn
        // preserving aspect ratio
        const W = this.canvas.width;
        const H = this.canvas.height;
        const PAD = 30;

        // Default available area
        let availW = W - PAD * 2;
        let availH = H - PAD * 2;

        // If we have map image, use its aspect ratio
        if (this._mapImg && this._mapLoaded) {
            const isRotated = this._mapImg.height > this._mapImg.width;
            // If rotated (-90 deg), visual aspect is H/W instead of W/H
            const imgAspect = isRotated ? this._mapImg.height / this._mapImg.width : this._mapImg.width / this._mapImg.height;
            const canvasAspect = availW / availH;

            if (imgAspect > canvasAspect) {
                // Image is wider visually (fit width)
                const h = availW / imgAspect;
                return {
                    x: PAD,
                    y: PAD + (availH - h) / 2,
                    w: availW,
                    h: h,
                    isRotated: isRotated
                };
            } else {
                // Image is taller visually (fit height)
                const w = availH * imgAspect;
                return {
                    x: PAD + (availW - w) / 2,
                    y: PAD,
                    w: w,
                    h: availH,
                    isRotated: isRotated
                };
            }
        }

        // Fallback: If no image, try to use track bounds from data to deduce aspect
        if (this._sessionData?.track_layout?.bounds) {
            const b = this._sessionData.track_layout.bounds;
            const wWorld = (b.max_x - b.min_x) || 1000;
            const hWorld = (b.max_z - b.min_z) || 1000;
            const trackAspect = wWorld / hWorld;
            const canvasAspect = availW / availH;

            if (trackAspect > canvasAspect) {
                const h = availW / trackAspect;
                return { x: PAD, y: PAD + (availH - h) / 2, w: availW, h: h };
            } else {
                const w = availH * trackAspect;
                return { x: PAD + (availW - w) / 2, y: PAD, w: w, h: availH };
            }
        }

        // Just fill with padding if nothing else known
        return { x: PAD, y: PAD, w: availW, h: availH };
    }

    _redraw() {
        const ctx = this.ctx;
        const W = this.canvas.width;
        const H = this.canvas.height;

        ctx.clearRect(0, 0, W, H);

        // ── Draw Background (Map or Dark) ────────────────────────────────────
        const rect = this._getDrawRect();

        if (this._mapImg && this._mapLoaded) {
            // Draw Map Image
            if (rect.isRotated) {
                // Save context state
                ctx.save();
                // Move origin to center of drawing rect
                ctx.translate(rect.x + rect.w / 2, rect.y + rect.h / 2);
                // Rotate -90 degrees
                ctx.rotate(-Math.PI / 2);
                // Draw image centered (swap w/h dimensions relative to rotated context)
                // Source Image is W x H. We draw it into H x W visual box.
                ctx.drawImage(this._mapImg, -rect.h / 2, -rect.w / 2, rect.h, rect.w);
                ctx.restore();
            } else {
                ctx.drawImage(this._mapImg, rect.x, rect.y, rect.w, rect.h);
            }

            // Dark overlay for contrast
            ctx.fillStyle = 'rgba(0,0,0,0.5)';
            ctx.fillRect(0, 0, W, H);
        } else {
            // Default Dark Background
            ctx.fillStyle = 'rgba(8,10,16,1)';
            ctx.fillRect(0, 0, W, H);

            // Subtle dot-grid for spatial reference
            ctx.fillStyle = 'rgba(255,255,255,0.04)';
            const GRID = 40;
            for (let gx = GRID; gx < W; gx += GRID)
                for (let gy = GRID; gy < H; gy += GRID) {
                    ctx.beginPath();
                    ctx.arc(gx, gy, 1, 0, Math.PI * 2);
                    ctx.fill();
                }
        }

        const layout = this._sessionData?.track_layout;
        if (!layout || !layout.positions || layout.positions.length < 2) return;

        // ── Speed heatmap trace Removed ──────────────────────────────────────
        // We now rely on the static background image for the track layout.
        // If needed, we can overlay a simplified line, but user requested image base.


        // ── 10 numbered dots ─────────────────────────────────────────────────
        const points = this._getPoints();
        points.forEach((pt, i) => {
            if (!pt.mid_norm) return;
            this._drawDot(pt, i);
        });

        // ── Active tooltip card ──────────────────────────────────────────────
        if (this._tooltipPoint) {
            const pt = points.find(p => p.label === this._tooltipPoint);
            if (pt && pt.mid_norm) this._drawCard(pt);
        }
    }

    _drawHeatmap(layout) {
        const ctx = this.ctx;
        const pos = layout.positions;
        const speeds = layout.speeds || [];
        const maxSpd = Math.max(...speeds, 1);
        const minSpd = Math.min(...speeds, 0);

        // Pass 1: black shadow for track width contrast
        ctx.lineWidth = 10;
        ctx.strokeStyle = 'rgba(0,0,0,0.6)';
        ctx.beginPath();
        if (pos.length > 0) {
            const p0 = this._toCanvas(pos[0]);
            ctx.moveTo(p0.x, p0.y);
            pos.slice(1).forEach(p => { const c = this._toCanvas(p); ctx.lineTo(c.x, c.y); });
        }
        ctx.stroke();

        // Pass 2: speed heatmap
        for (let i = 0; i < pos.length - 1; i++) {
            const p1 = this._toCanvas(pos[i]);
            const p2 = this._toCanvas(pos[i + 1]);
            const t = speeds[i] ? (speeds[i] - minSpd) / (maxSpd - minSpd) : 0.5;
            // Red → yellow → green
            const r = Math.round(255 * (1 - t));
            const g = Math.round(255 * t);
            ctx.strokeStyle = `rgba(${r},${g},0,0.90)`;
            ctx.lineWidth = 5;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        }
    }

    _drawDot(pt, colorIdx) {
        const ctx = this.ctx;
        const pos = this._toCanvas(pt.mid_norm);
        const hovered = this._tooltipPoint === pt.label;
        const color = this._palette[colorIdx % this._palette.length];
        const R = hovered ? 17 : 13;

        // White outer ring (contrast against heatmap line)
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, R + 2.5, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fill();

        // Glow
        ctx.shadowColor = color;
        ctx.shadowBlur = hovered ? 24 : 12;

        // Filled circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, R, 0, Math.PI * 2);
        ctx.fillStyle = hovered ? color : 'rgba(12,14,22,0.92)';
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Number label
        ctx.fillStyle = hovered ? '#000' : color;
        ctx.font = `bold ${R > 15 ? 12 : 10}px 'Exo 2', sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(pt.point_num ?? pt.label, pos.x, pos.y);
    }

    _drawCard(pt) {
        const ctx = this.ctx;
        const pos = this._toCanvas(pt.mid_norm);
        const W = this.canvas.width;
        const H = this.canvas.height;

        // Card content lines
        const lines = [
            { label: '📍 Punto', value: pt.label },
            { label: '⚡ Velocidad', value: `${pt.speed} km/h` },
            { label: '🛑 Freno', value: `${pt.brake_pct}%  ${pt.is_braking ? '●' : ''}` },
            { label: '🏎️ Aceler.', value: `${pt.throttle_pct}%` },
            { label: '↩️ G-Lat', value: `${pt.g_lat} g` },
            { label: '✅ Vuelta', value: pt.lap_is_valid ? 'Válida' : '❌ Inválida' },
        ];

        const CW = 190, CH = lines.length * 20 + 22;
        let cx = pos.x + 18, cy = pos.y - CH / 2;
        if (cx + CW > W - 10) cx = pos.x - CW - 18;
        if (cy < 6) cy = 6;
        if (cy + CH > H - 6) cy = H - CH - 6;

        // Background
        ctx.fillStyle = 'rgba(10,12,18,0.93)';
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 1.2;
        this._roundRect(ctx, cx, cy, CW, CH, 7);
        ctx.fill();
        ctx.stroke();

        // Text
        lines.forEach((row, i) => {
            const y = cy + 16 + i * 20;
            ctx.fillStyle = '#555';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(row.label, cx + 8, y);
            ctx.fillStyle = '#e0e0e0';
            ctx.font = 'bold 10px sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(row.value, cx + CW - 8, y);
        });
    }

    _roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    _onMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        const mx = (e.clientX - rect.left) * scaleX;
        const my = (e.clientY - rect.top) * scaleY;

        const points = this._getPoints();
        let found = null;
        let minDist = 28;   // px hit radius

        points.forEach(pt => {
            if (!pt.mid_norm) return;
            const pos = this._toCanvas(pt.mid_norm);
            const d = Math.hypot(mx - pos.x, my - pos.y);
            if (d < minDist) { minDist = d; found = pt.label; }
        });

        this._tooltipPoint = found;
        this._redraw();
    }

    // SVG Reprojection Removed - Using Image Aspect Ratio
}
