import sys
import os
import sqlite3
import json
import logging
from typing import List, Dict, Any

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import Database
from backend.data_analyzer import DataAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_session(session_id=None):
    db = Database()
    analyzer = DataAnalyzer(db)
    
    if session_id is None:
        # Get latest session
        sessions = db.get_sessions(limit=1)
        if not sessions:
            print("No sessions found")
            return
        session_id = sessions[0]['id']
    
    print(f"--- Debugging Session {session_id} ---")
    
    # Get laps
    laps = db.get_session_laps(session_id)
    print(f"Total laps: {len(laps)}")
    
    for lap in laps:
        print(f"  Lap {lap['lap_number']}: Time={lap['lap_time']}, Valid={lap['is_valid']}")
    
    valid_laps = [lap for lap in laps if lap['is_valid'] and lap['lap_time'] > 0]
    print(f"Valid laps: {len(valid_laps)}")
    
    # RELAXING REQUIREMENT FOR DEBUGGING
    if not valid_laps:
        print("No valid laps found. Attempting to use ANY complete lap...")
        valid_laps = [lap for lap in laps if lap['lap_time'] > 0]

    if not valid_laps:
        print("No complete laps found either.")
        return

    best_lap = min(valid_laps, key=lambda x: x['lap_time'])
    print(f"Best lap ID: {best_lap['id']}, Time: {best_lap['lap_time']}")
    
    # Get telemetry
    telemetry = db.get_lap_telemetry(best_lap['id'])
    print(f"Telemetry points for best lap: {len(telemetry)}")
    
    if not telemetry:
        print("Telemetry is empty!")
        return

    # Check max values
    max_g_lat = max([abs(p.get('g_force_lat', 0)) for p in telemetry])
    max_steering = max([abs(p.get('steering', 0)) for p in telemetry])
    print(f"Max G-Lat: {max_g_lat}")
    print(f"Max Steering (Raw): {max_steering}")
    
    # Run detection
    try:
        print("Running _detect_track_sections...")
        sections = analyzer._detect_track_sections(telemetry)
        print(f"Sections found: {len(sections)}")
        for i, section in enumerate(sections):
            print(f"  Section {i+1}: {section['type']} ({len(section['points'])} points)")
    except Exception as e:
        print(f"Error in detection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_session(int(sys.argv[1]))
    else:
        debug_session()
