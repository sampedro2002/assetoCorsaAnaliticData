import sys
import os
import json
import sqlite3
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Mock config before importing database
import backend.config
backend.config.DB_CONFIG = {'database_path': 'test_data/test.db'}

from backend.database import Database
from backend.data_analyzer import DataAnalyzer

def test_offtrack_detection():
    print("Initializing test database...")
    db = Database()
    db.create_schema()
    analyzer = DataAnalyzer(db)

    # 1. Create Session
    session_id = db.create_session("Test Track", "Test Car", "Practice", "2023-01-01 10:00:00")

    # 2. Create Best Lap (Valid)
    best_lap_id = db.create_lap(session_id, 1, 60.0, is_valid=True)
    
    # Generate Best Lap Telemetry (Corner at 50% progress)
    best_telem = []
    for i in range(100):
        # Straight -> Corner -> Straight
        steering = 0.5 if 40 <= i <= 60 else 0.0
        speed = 100 if 40 <= i <= 60 else 200
        best_telem.append({
            'lap_id': best_lap_id,
            'timestamp': i * 0.1,
            'speed': speed,
            'rpm': 5000,
            'gear': 3,
            'pos_x': float(i), 'pos_y': 0.0, 'pos_z': 0.0,
            'throttle': 0.5, 'brake': 0.0, 'steering': steering,
            'g_force_lat': 0.0, 'g_force_long': 0.0,
            'tire_temp_fl': 80.0, 'tire_temp_fr': 80.0, 'tire_temp_rl': 80.0, 'tire_temp_rr': 80.0,
            'tire_pressure_fl': 25.0, 'tire_pressure_fr': 25.0, 'tire_pressure_rl': 25.0, 'tire_pressure_rr': 25.0,
            'brake_temp_fl': 100.0, 'brake_temp_fr': 100.0, 'brake_temp_rl': 100.0, 'brake_temp_rr': 100.0,
            'fuel': 10.0,
            'n_tires_out': 0
        })
    db.insert_telemetry_batch(best_telem)

    # 3. Create Last Lap (Invalid in Corner)
    last_lap_id = db.create_lap(session_id, 2, 61.0, is_valid=False)

    last_telem = []
    for i in range(100):
        # Same corner, but 3 tires out
        steering = 0.5 if 40 <= i <= 60 else 0.0
        speed = 105 if 40 <= i <= 60 else 200 # Faster entry
        n_tires = 3 if 45 <= i <= 55 else 0 # Off track in middle of corner
        
        last_telem.append({
            'lap_id': last_lap_id,
            'timestamp': i * 0.1,
            'speed': speed,
            'rpm': 5000,
            'gear': 3,
            'pos_x': float(i), 'pos_y': 0.0, 'pos_z': 0.0,
            'throttle': 0.5, 'brake': 0.0, 'steering': steering,
            'g_force_lat': 0.0, 'g_force_long': 0.0,
            'tire_temp_fl': 80.0, 'tire_temp_fr': 80.0, 'tire_temp_rl': 80.0, 'tire_temp_rr': 80.0,
            'tire_pressure_fl': 25.0, 'tire_pressure_fr': 25.0, 'tire_pressure_rl': 25.0, 'tire_pressure_rr': 25.0,
            'brake_temp_fl': 100.0, 'brake_temp_fr': 100.0, 'brake_temp_rl': 100.0, 'brake_temp_rr': 100.0,
            'fuel': 10.0,
            'n_tires_out': n_tires
        })
    db.insert_telemetry_batch(last_telem)
    
    # 4. Analyze
    print("Analyzing...")
    result = analyzer.analyze_session(session_id)
    
    # 5. Check Recommendations
    print("\nRecommendations:")
    found_offtrack = False
    for rec in result['recommendations']:
        print(f"- {rec}")
        if "Salida de pista" in rec:
            found_offtrack = True
            
    if found_offtrack:
        print("\nSUCCESS: Off-track recommendation found!")
    else:
        print("\nFAILURE: Off-track recommendation NOT found.")

if __name__ == "__main__":
    test_offtrack_detection()
