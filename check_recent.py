import sqlite3

conn = sqlite3.connect('data/assetto_corsa.db')
cursor = conn.cursor()

# Get the most recent session
cursor.execute('SELECT id, track_name, car_name, total_laps FROM sessions ORDER BY id DESC LIMIT 1')
session = cursor.fetchone()
print(f'Most recent session: ID={session[0]}, Track={session[1]}, Car={session[2]}, Laps={session[3]}')

# Get laps from that session
cursor.execute('SELECT id, lap_number, lap_time, is_valid FROM laps WHERE session_id = ? ORDER BY lap_number', (session[0],))
laps = cursor.fetchall()
print(f'\nLaps in session {session[0]}:')
for lap in laps:
    print(f'  Lap {lap[1]}: ID={lap[0]}, time={lap[2]:.3f}s, valid={lap[3]}')

# Check normalized_position for the last 2 laps
if len(laps) >= 2:
    lap1_id = laps[0][0]
    lap2_id = laps[1][0] if len(laps) > 1 else lap1_id
    
    print(f'\nChecking telemetry for lap {lap1_id}:')
    cursor.execute('SELECT COUNT(*), MIN(normalized_position), MAX(normalized_position), AVG(normalized_position) FROM telemetry WHERE lap_id = ?', (lap1_id,))
    result = cursor.fetchone()
    print(f'  Points: {result[0]}, Min pos: {result[1]}, Max pos: {result[2]}, Avg pos: {result[3]}')
    
    if len(laps) > 1:
        print(f'\nChecking telemetry for lap {lap2_id}:')
        cursor.execute('SELECT COUNT(*), MIN(normalized_position), MAX(normalized_position), AVG(normalized_position) FROM telemetry WHERE lap_id = ?', (lap2_id,))
        result = cursor.fetchone()
        print(f'  Points: {result[0]}, Min pos: {result[1]}, Max pos: {result[2]}, Avg pos: {result[3]}')

conn.close()
