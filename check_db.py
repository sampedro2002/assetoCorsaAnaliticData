import sqlite3

conn = sqlite3.connect('data/assetto_corsa.db')
cursor = conn.cursor()

# Check laps
cursor.execute('SELECT COUNT(*) FROM laps')
print(f'Total laps: {cursor.fetchone()[0]}')

cursor.execute('SELECT id, lap_number, lap_time, is_valid FROM laps ORDER BY id DESC LIMIT 5')
print('\nRecent laps:')
for row in cursor.fetchall():
    print(f'  Lap ID {row[0]}: lap_number={row[1]}, time={row[2]:.3f}s, valid={row[3]}')

# Check telemetry
cursor.execute('SELECT lap_id, COUNT(*) as points FROM telemetry GROUP BY lap_id ORDER BY lap_id DESC LIMIT 5')
print('\nTelemetry points per lap:')
for row in cursor.fetchall():
    print(f'  Lap {row[0]}: {row[1]} points')

# Check if normalized_position exists and has data
cursor.execute('SELECT lap_id, COUNT(*) as total, SUM(CASE WHEN normalized_position > 0 THEN 1 ELSE 0 END) as with_pos FROM telemetry GROUP BY lap_id ORDER BY lap_id DESC LIMIT 3')
print('\nNormalized position data:')
for row in cursor.fetchall():
    print(f'  Lap {row[0]}: {row[2]}/{row[1]} points have normalized_position > 0')

conn.close()
