import sqlite3
import os
import json

DB_PATH = './data/assetto_corsa.db'

def check_data():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest session
    cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1")
    session = cursor.fetchone()
    
    if not session:
        print("No sessions found in database.")
        conn.close()
        return

    session_id = session['id']
    print(f"Indices examining latest session ID: {session_id}")
    print(f"Track: {session['track_name']}, Car: {session['car_name']}")
    
    # Get analysis
    cursor.execute("SELECT * FROM analysis WHERE session_id = ?", (session_id,))
    analysis = cursor.fetchone()
    if analysis:
        print("\nExisting Analysis Found:")
        print(f"Recommendations: {analysis['recommendations'][:100]}...")
    else:
        print("\nNo analysis found for this session.")

    # Get telemetry stats
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            MAX(ABS(g_force_lat)) as max_g_lat,
            MAX(ABS(steering)) as max_steering,
            AVG(ABS(g_force_lat)) as avg_g_lat,
            AVG(ABS(steering)) as avg_steering
        FROM telemetry 
        WHERE lap_id IN (SELECT id FROM laps WHERE session_id = ?)
    """, (session_id,))
    
    stats = cursor.fetchone()
    
    output = {
        "session_id": session_id,
        "track": session['track_name'],
        "car": session['car_name'],
        "count": stats['count'],
        "max_g_lat": stats['max_g_lat'],
        "max_steering": stats['max_steering'],
        "avg_g_lat": stats['avg_g_lat'],
        "avg_steering": stats['avg_steering']
    }
    
    print(json.dumps(output, indent=2))
    with open('debug_output.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Check sample of raw data
    cursor.execute("""
        SELECT timestamp, g_force_lat, steering 
        FROM telemetry 
        WHERE lap_id IN (SELECT id FROM laps WHERE session_id = ?)
        LIMIT 5
    """, (session_id,))
    rows = cursor.fetchall()
    print("\nFirst 5 telemetry points:")
    for row in rows:
        print(f"Time: {row['timestamp']:.2f}, G-Lat: {row['g_force_lat']:.4f}, Steering: {row['steering']:.4f}")

    conn.close()

if __name__ == "__main__":
    check_data()
