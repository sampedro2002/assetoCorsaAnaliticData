"""
FastAPI WebSocket Server for Real-Time Telemetry Streaming
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import asyncio
import glob
import json
from typing import List, Dict, Any
from pathlib import Path
import sys
import os
# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.config import SERVER_CONFIG
from backend.database.database import Database
from backend.domain.analysis.analyzer import DataAnalyzer
from backend.core.config import AC_CONFIG

# Helper to get base path for bundled files
def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    # Go up 3 levels: backend/api/websocket.py -> backend/api -> backend -> root
    return Path(__file__).parent.parent.parent

BASE_PATH = get_base_path()
FRONTEND_PATH = BASE_PATH / "frontend"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Assetto Corsa Telemetry API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

# Database instance
db: Database = None

# Active WebSocket connections
active_connections: List[WebSocket] = []

# Current telemetry data (shared state)
current_telemetry: Dict[str, Any] = {}


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✓ Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        self.active_connections.remove(websocket)
        logger.info(f"✓ Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    global db
    db = Database()
    db.create_schema()
    logger.info("✓ FastAPI server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if db:
        db.close()
    logger.info("✓ FastAPI server shutdown")


@app.get("/")
async def read_root():
    """Serve the frontend HTML"""
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/styles.css")
async def get_styles():
    """Serve CSS file"""
    return FileResponse(FRONTEND_PATH / "styles.css")


@app.get("/app.js")
async def get_app_js():
    """Serve main JavaScript file"""
    return FileResponse(FRONTEND_PATH / "app.js")


@app.get("/charts.js")
async def get_charts_js():
    """Serve charts JavaScript file"""
    return FileResponse(FRONTEND_PATH / "charts.js")


@app.get("/js/history.js")
async def get_history_js():
    """Serve history JavaScript file"""
    return FileResponse(FRONTEND_PATH / "js/history.js")


@app.get("/js/annotatedMap.js")
async def get_annotated_map_js():
    """Serve annotated map JavaScript file"""
    return FileResponse(FRONTEND_PATH / "js/annotatedMap.js")


@app.get("/api/pedal-sessions")
async def list_pedal_sessions():
    """List all available pedal analysis sessions"""
    try:
        # Assuming path relative to backend execution
        # In pedals.py: SESIONES_DIR = "data/pedal_analysis"
        path = "data/pedal_analysis/*.json"
        files = glob.glob(path)
        # return filenames only, sorted by newest
        files.sort(key=os.path.getmtime, reverse=True)
        return [os.path.basename(f) for f in files]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/pedal-sessions/{filename}")
async def get_pedal_session(filename: str):
    """Get details of a specific pedal analysis session"""
    try:
        path = os.path.join("data/pedal_analysis", filename)
        if not os.path.exists(path):
            return {"error": "File not found"}
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back or handle client requests if needed
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/sessions")
async def get_sessions(limit: int = 50):
    """Get recent sessions"""
    try:
        sessions = db.get_sessions(limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return {"error": str(e)}, 500


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    """Get session details"""
    try:
        sessions = db.get_sessions(limit=1000)
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            return {"error": "Session not found"}, 404
        
        laps = db.get_session_laps(session_id)
        analysis = db.get_session_analysis(session_id)
        
        return {
            "session": session,
            "laps": laps,
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/sessions/{session_id}/laps")
async def get_session_laps(session_id: int):
    """Get all laps for a session"""
    try:
        laps = db.get_session_laps(session_id)
        return {"laps": laps}
    except Exception as e:
        logger.error(f"Error fetching laps for session {session_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/laps/{lap_id}/telemetry")
async def get_lap_telemetry(lap_id: int):
    """Get telemetry data for a specific lap"""
    try:
        telemetry = db.get_lap_telemetry(lap_id)
        return {"telemetry": telemetry}
    except Exception as e:
        logger.error(f"Error fetching telemetry for lap {lap_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/sessions/{session_id}/analysis")
async def get_session_analysis(session_id: int):
    """Get analysis results for a session"""
    try:
        analysis = db.get_session_analysis(session_id)
        if not analysis:
            return {"error": "Analysis not found"}, 404
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error fetching analysis for session {session_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/sessions/{session_id}/volante")
async def get_session_volante_stats(session_id: int):
    """Get steering wheel statistics for a session"""
    try:
        stats = db.get_session_volante_stats(session_id)
        if not stats:
            return {"error": "Stats not found"}, 404
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error fetching volante stats for session {session_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/laps/{lap_id}/volante")
async def get_lap_volante_data(lap_id: int):
    """Get time-series steering data for a specific lap"""
    try:
        data = db.get_lap_volante_data(lap_id)
        return {"volante_data": data}
    except Exception as e:
        logger.error(f"Error fetching lap volante data for lap {lap_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/history/tracks")
async def get_history_tracks():
    """Get list of all tracks with history"""
    try:
        tracks = db.get_unique_tracks()
        return {"tracks": tracks}
    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
        return {"error": str(e)}, 500


@app.get("/api/history/sessions")
async def get_history_sessions(track: str):
    """Get all sessions for a specific track"""
    try:
        sessions = db.get_history_sessions(track)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error fetching history sessions for {track}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/history/{track_name}/annotated-map")
async def get_annotated_map(track_name: str):
    """Get annotated track map with section stats for every session on a track"""
    try:
        analyzer = DataAnalyzer(db)
        result = analyzer.analyze_annotated_map_by_track(track_name)
        return result
    except Exception as e:
        logger.error(f"Error building annotated map for {track_name}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/history/{track_name}")
async def get_track_history(track_name: str):
    """Get analysis for last 3 races on a track"""
    try:
        analyzer = DataAnalyzer(db)
        analysis = analyzer.analyze_last_3_races(track_name)
        return analysis
    except Exception as e:
        logger.error(f"Error fetching track history for {track_name}: {e}")
        return {"error": str(e)}, 500


@app.post("/api/track-map/generate")
async def generate_track_map_data(track_name: str, length_m: float, interval_m: float = 200.0):
    """
    Generate synchronization data for a track map.
    Returns the list of coordinates for the given interval.
    """
    try:
        mapper = TrackMapper(track_name, AC_CONFIG['install_path'])
        
        # Process map
        points, cum_dist = mapper.process_track_map(length_m)
        
        # Generate points
        dist_markers = []
        d = 0
        while d < length_m:
            dist_markers.append(d)
            d += interval_m
            
        # Get coordinates
        results = mapper.get_interpolated_coordinates(points, cum_dist, dist_markers)
        
        # Save to disk for caching
        output_dir = Path("data/track_maps")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{track_name}_map.json"
        
        with open(json_path, 'w') as f:
            json.dump(results, f)
            
        return {"track": track_name, "points": results}
        
    except Exception as e:
        logger.error(f"Error generating track map data: {e}")
        return {"error": str(e)}, 500

@app.get("/api/track-map/{track_name}")
async def get_track_map_data(track_name: str):
    """Get cached track map data"""
    try:
        json_path = Path("data/track_maps") / f"{track_name}_map.json"
        if json_path.exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
            return {"track": track_name, "points": data}
        else:
            return {"error": "Map data not found. Please generate first."}, 404
    except Exception as e:
        logger.error(f"Error fetching track map data: {e}")
        return {"error": str(e)}, 500




@app.get("/api/sessions/{session_id}/lap-table")
async def get_session_lap_table(session_id: int):
    """Get lap comparison table (with telemetry stats + score) for a single session"""
    try:
        analyzer = DataAnalyzer(db)
        result = analyzer.build_single_session_lap_table(session_id)
        return result
    except Exception as e:
        logger.error(f"Error building lap table for session {session_id}: {e}")
        return {"error": str(e)}, 500


@app.get("/api/history/sessions/{session_id}/last-laps")
async def get_last_laps_analysis(session_id: int):
    """Get analysis for last 3 laps of a session"""
    try:
        analyzer = DataAnalyzer(db)
        analysis = analyzer.analyze_last_3_laps(session_id)
        return analysis
    except Exception as e:
        logger.error(f"Error fetching last laps analysis for session {session_id}: {e}")
        return {"error": str(e)}, 500


async def broadcast_telemetry(telemetry_data: Dict[str, Any]):
    """Broadcast telemetry data to all connected clients"""
    await manager.broadcast({
        "type": "telemetry",
        "data": telemetry_data
    })


async def broadcast_race_start(session_info: Dict[str, Any]):
    """Notify clients that a race has started"""
    await manager.broadcast({
        "type": "race_start",
        "data": session_info
    })


async def broadcast_race_end(session_id: int, analysis: Dict[str, Any]):
    """Notify clients that a race has ended with analysis"""
    await manager.broadcast({
        "type": "race_end",
        "data": {
            "session_id": session_id,
            "analysis": analysis
        }
    })


async def broadcast_lap_complete(lap_info: Dict[str, Any]):
    """Notify clients that a lap was completed"""
    await manager.broadcast({
        "type": "lap_complete",
        "data": lap_info
    })


def get_app():
    """Return the FastAPI app instance"""
    return app


def get_manager():
    """Return the connection manager"""
    return manager
