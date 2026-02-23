"""
SQLite Database Manager for Assetto Corsa Telemetry System
"""
import sqlite3
import json
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.core.config import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager"""
    
    def __init__(self):
        """Initialize database connection"""
        self.db_path = DB_CONFIG['database_path']
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Test connection
        try:
            conn = self.get_connection()
            conn.close()
            logger.info("✓ Database connection pool created")
        except Exception as e:
            logger.error(f"✗ Failed to create connection: {e}")
            raise
    
    def get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    
    def return_connection(self, conn):
        """Close a connection (for compatibility with PostgreSQL version)"""
        conn.close()
    
    def create_schema(self):
        """Create all database tables"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_name TEXT NOT NULL,
                    car_name TEXT NOT NULL,
                    session_type TEXT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    total_laps INTEGER DEFAULT 0,
                    best_lap_time REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Laps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS laps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                    lap_number INTEGER NOT NULL,
                    lap_time REAL NOT NULL,
                    sector_1_time REAL,
                    sector_2_time REAL,
                    sector_3_time REAL,
                    is_valid INTEGER DEFAULT 1,
                    max_speed REAL,
                    avg_speed REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Telemetry table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lap_id INTEGER REFERENCES laps(id) ON DELETE CASCADE,
                    timestamp REAL NOT NULL,
                    speed REAL,
                    rpm INTEGER,
                    gear INTEGER,
                    pos_x REAL,
                    pos_y REAL,
                    pos_z REAL,
                    normalized_position REAL,
                    throttle REAL,
                    brake REAL,
                    steering REAL,
                    g_force_lat REAL,
                    g_force_long REAL,
                    tire_temp_fl REAL,
                    tire_temp_fr REAL,
                    tire_temp_rl REAL,
                    tire_temp_rr REAL,
                    tire_pressure_fl REAL,
                    tire_pressure_fr REAL,
                    tire_pressure_rl REAL,
                    tire_pressure_rr REAL,
                    brake_temp_fl REAL,
                    brake_temp_fr REAL,
                    brake_temp_rl REAL,
                    brake_temp_rr REAL,
                    fuel REAL,
                    n_tires_out INTEGER
                )
            """)
            
            # Analysis table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                    analysis_type TEXT,
                    recommendations TEXT,
                    ideal_line_data TEXT,
                    braking_points TEXT,
                    acceleration_points TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Personal records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS personal_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_name TEXT NOT NULL,
                    car_name TEXT NOT NULL,
                    best_lap_time REAL NOT NULL,
                    best_sector_1 REAL,
                    best_sector_2 REAL,
                    best_sector_3 REAL,
                    session_id INTEGER REFERENCES sessions(id),
                    achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track_name, car_name)
                )
            """)
            
            # Section records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS section_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_name TEXT NOT NULL,
                    car_name TEXT NOT NULL,
                    section_id INTEGER NOT NULL,
                    section_type TEXT NOT NULL,
                    best_time REAL NOT NULL,
                    best_avg_speed REAL,
                    best_max_speed REAL,
                    session_id INTEGER REFERENCES sessions(id),
                    achieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track_name, car_name, section_id)
                )
            """)
            
            # Volante (Steering Wheel) table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS volante (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lap_id INTEGER REFERENCES laps(id) ON DELETE CASCADE,
                    timestamp REAL NOT NULL,
                    steering_angle REAL,
                    angular_velocity REAL,
                    angular_acceleration REAL,
                    brake_percentage REAL,
                    throttle_percentage REAL,
                    sample_frequency REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_laps_session ON laps(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_lap ON telemetry(lap_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_session ON analysis(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personal_records_track_car ON personal_records(track_name, car_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_section_records_track_car ON section_records(track_name, car_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_volante_lap ON volante(lap_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_volante_timestamp ON volante(timestamp)")
            
            conn.commit()
            logger.info("✓ Database schema created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to create schema: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def create_session(self, track_name: str, car_name: str, session_type: str, start_time) -> int:
        """Create a new session and return its ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (track_name, car_name, session_type, start_time)
                VALUES (?, ?, ?, ?)
            """, (track_name, car_name, session_type, start_time))
            session_id = cursor.lastrowid
            conn.commit()
            logger.info(f"✓ Created session {session_id}: {car_name} at {track_name}")
            return session_id
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to create session: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def update_session(self, session_id: int, **kwargs):
        """Update session fields"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [session_id]
            cursor.execute(f"""
                UPDATE sessions SET {set_clause}
                WHERE id = ?
            """, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to update session: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def create_lap(self, session_id: int, lap_number: int, lap_time: float, **kwargs) -> int:
        """Create a new lap and return its ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO laps (session_id, lap_number, lap_time, sector_1_time, sector_2_time, sector_3_time, is_valid, max_speed, avg_speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, lap_number, lap_time,
                kwargs.get('sector_1_time'), kwargs.get('sector_2_time'), kwargs.get('sector_3_time'),
                1 if kwargs.get('is_valid', True) else 0, kwargs.get('max_speed'), kwargs.get('avg_speed')
            ))
            lap_id = cursor.lastrowid
            conn.commit()
            logger.info(f"✓ Created lap {lap_number} (ID: {lap_id}) - Time: {lap_time:.3f}s")
            return lap_id
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to create lap: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def insert_telemetry_batch(self, telemetry_data: List[Dict[str, Any]]):
        """Bulk insert telemetry data for performance"""
        if not telemetry_data:
            return
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Prepare bulk insert
            values = []
            for data in telemetry_data:
                values.append((
                    data['lap_id'], data['timestamp'], data['speed'], data['rpm'], data['gear'],
                    data['pos_x'], data['pos_y'], data['pos_z'],
                    data.get('normalized_position', 0.0),
                    data['throttle'], data['brake'], data['steering'],
                    data['g_force_lat'], data['g_force_long'],
                    data['tire_temp_fl'], data['tire_temp_fr'], data['tire_temp_rl'], data['tire_temp_rr'],
                    data['tire_pressure_fl'], data['tire_pressure_fr'], data['tire_pressure_rl'], data['tire_pressure_rr'],
                    data['brake_temp_fl'], data['brake_temp_fr'], data['brake_temp_rl'], data['brake_temp_rr'],
                    data['fuel'],
                    data.get('n_tires_out', 0)
                ))
            
            cursor.executemany("""
                INSERT INTO telemetry (
                    lap_id, timestamp, speed, rpm, gear,
                    pos_x, pos_y, pos_z,
                    normalized_position,
                    throttle, brake, steering,
                    g_force_lat, g_force_long,
                    tire_temp_fl, tire_temp_fr, tire_temp_rl, tire_temp_rr,
                    tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr,
                    brake_temp_fl, brake_temp_fr, brake_temp_rl, brake_temp_rr,
                    fuel,
                    n_tires_out
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            
            conn.commit()
            logger.debug(f"✓ Inserted {len(telemetry_data)} telemetry points")
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to insert telemetry batch: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def insert_volante_batch(self, volante_data: List[Dict[str, Any]]):
        """Bulk insert volante (steering wheel) data for performance"""
        if not volante_data:
            return
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Prepare bulk insert
            values = []
            for data in volante_data:
                values.append((
                    data['lap_id'], 
                    data['timestamp'], 
                    data['steering_angle'],
                    data['angular_velocity'], 
                    data['angular_acceleration'],
                    data['brake_percentage'], 
                    data['throttle_percentage'],
                    data['sample_frequency']
                ))
            
            cursor.executemany("""
                INSERT INTO volante (
                    lap_id, timestamp, steering_angle, angular_velocity, 
                    angular_acceleration, brake_percentage, throttle_percentage, 
                    sample_frequency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            
            conn.commit()
            logger.debug(f"✓ Inserted {len(volante_data)} volante data points")
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to insert volante batch: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_lap_volante_data(self, lap_id: int) -> List[Dict]:
        """Get all volante data for a lap"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM volante
                WHERE lap_id = ?
                ORDER BY timestamp
            """, (lap_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_session_volante_stats(self, session_id: int) -> Optional[Dict]:
        """Get aggregate volante statistics for a session"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    MAX(ABS(v.steering_angle)) as max_steering_angle,
                    MAX(ABS(v.angular_velocity)) as max_angular_velocity,
                    MAX(ABS(v.angular_acceleration)) as max_angular_acceleration,
                    AVG(v.brake_percentage) as avg_brake_usage,
                    AVG(v.throttle_percentage) as avg_throttle_usage,
                    AVG(v.sample_frequency) as avg_sample_frequency
                FROM volante v
                JOIN laps l ON v.lap_id = l.id
                WHERE l.session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_lap_volante_data(self, lap_id: int) -> List[Dict]:
        """Get time-series volante data for a specific lap"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    timestamp,
                    steering_angle,
                    angular_velocity,
                    angular_acceleration,
                    brake_percentage,
                    throttle_percentage,
                    force_feedback
                FROM volante
                WHERE lap_id = ?
                ORDER BY timestamp ASC
            """, (lap_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def save_analysis(self, session_id: int, analysis_type: str, recommendations: dict, 
                     ideal_line_data: dict = None, braking_points: dict = None, 
                     acceleration_points: dict = None):
        """Save analysis results"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis (session_id, analysis_type, recommendations, ideal_line_data, braking_points, acceleration_points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, analysis_type, 
                  json.dumps(recommendations),
                  json.dumps(ideal_line_data) if ideal_line_data else None,
                  json.dumps(braking_points) if braking_points else None,
                  json.dumps(acceleration_points) if acceleration_points else None))
            conn.commit()
            logger.info(f"✓ Saved analysis for session {session_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to save analysis: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_sessions(self, limit: int = 50) -> List[Dict]:
        """Get recent sessions"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_session_laps(self, session_id: int) -> List[Dict]:
        """Get all laps for a session"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM laps
                WHERE session_id = ?
                ORDER BY lap_number
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_lap_telemetry_stats(self, lap_id: int) -> Dict:
        """Aggregate telemetry stats for a single lap using SQL (efficient)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    MAX(speed)                                              AS max_speed_tel,
                    AVG(speed)                                              AS avg_speed_tel,
                    MAX(ABS(g_force_lat))                                   AS max_g_lat,
                    MAX(ABS(g_force_long))                                  AS max_g_long,
                    SUM(CASE WHEN brake > 0.8 THEN 1 ELSE 0 END)           AS hard_brakes,
                    SUM(CASE WHEN n_tires_out > 0 THEN 1 ELSE 0 END)       AS off_track_events,
                    AVG(brake)                                              AS avg_brake,
                    AVG(throttle)                                           AS avg_throttle,
                    MAX(ABS(steering))                                      AS max_steering,
                    COUNT(*)                                                AS sample_count,
                    -- Tire temperatures (avg per wheel)
                    AVG(tire_temp_fl)                                       AS avg_tire_temp_fl,
                    AVG(tire_temp_fr)                                       AS avg_tire_temp_fr,
                    AVG(tire_temp_rl)                                       AS avg_tire_temp_rl,
                    AVG(tire_temp_rr)                                       AS avg_tire_temp_rr,
                    MAX(tire_temp_fl)                                       AS max_tire_temp_fl,
                    MAX(tire_temp_fr)                                       AS max_tire_temp_fr,
                    MAX(tire_temp_rl)                                       AS max_tire_temp_rl,
                    MAX(tire_temp_rr)                                       AS max_tire_temp_rr,
                    -- Tire pressure (avg per wheel)
                    AVG(tire_pressure_fl)                                   AS avg_tire_pres_fl,
                    AVG(tire_pressure_fr)                                   AS avg_tire_pres_fr,
                    AVG(tire_pressure_rl)                                   AS avg_tire_pres_rl,
                    AVG(tire_pressure_rr)                                   AS avg_tire_pres_rr,
                    -- Brake temperatures (avg per corner)
                    AVG(brake_temp_fl)                                      AS avg_brake_temp_fl,
                    AVG(brake_temp_fr)                                      AS avg_brake_temp_fr,
                    AVG(brake_temp_rl)                                      AS avg_brake_temp_rl,
                    AVG(brake_temp_rr)                                      AS avg_brake_temp_rr,
                    MAX(brake_temp_fl)                                      AS max_brake_temp_fl,
                    MAX(brake_temp_fr)                                      AS max_brake_temp_fr,
                    MAX(brake_temp_rl)                                      AS max_brake_temp_rl,
                    MAX(brake_temp_rr)                                      AS max_brake_temp_rr,
                    -- Tire wear proxy: max temp delta across all 4 wheels at any point
                    -- (high delta = uneven wear / overheating on one corner)
                    MAX(
                        MAX(tire_temp_fl, tire_temp_fr, tire_temp_rl, tire_temp_rr) -
                        MIN(tire_temp_fl, tire_temp_fr, tire_temp_rl, tire_temp_rr)
                    )                                                       AS max_tire_temp_delta
                FROM telemetry
                WHERE lap_id = ?
            """, (lap_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_session_telemetry_stats(self, session_id: int) -> Dict:
        """Aggregate telemetry stats for an entire session (all laps)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    MAX(t.speed)                                                AS max_speed_tel,
                    AVG(t.speed)                                                AS avg_speed_tel,
                    MAX(ABS(t.g_force_lat))                                     AS max_g_lat,
                    MAX(ABS(t.g_force_long))                                    AS max_g_long,
                    SUM(CASE WHEN t.brake > 0.8 THEN 1 ELSE 0 END)             AS hard_brakes,
                    SUM(CASE WHEN t.n_tires_out > 0 THEN 1 ELSE 0 END)         AS off_track_events,
                    AVG(t.brake)                                                AS avg_brake,
                    AVG(t.throttle)                                             AS avg_throttle,
                    COUNT(DISTINCT l.id)                                        AS laps_with_telemetry,
                    -- Tire temperatures
                    AVG(t.tire_temp_fl)                                         AS avg_tire_temp_fl,
                    AVG(t.tire_temp_fr)                                         AS avg_tire_temp_fr,
                    AVG(t.tire_temp_rl)                                         AS avg_tire_temp_rl,
                    AVG(t.tire_temp_rr)                                         AS avg_tire_temp_rr,
                    MAX(t.tire_temp_fl)                                         AS max_tire_temp_fl,
                    MAX(t.tire_temp_fr)                                         AS max_tire_temp_fr,
                    MAX(t.tire_temp_rl)                                         AS max_tire_temp_rl,
                    MAX(t.tire_temp_rr)                                         AS max_tire_temp_rr,
                    -- Tire pressure
                    AVG(t.tire_pressure_fl)                                     AS avg_tire_pres_fl,
                    AVG(t.tire_pressure_fr)                                     AS avg_tire_pres_fr,
                    AVG(t.tire_pressure_rl)                                     AS avg_tire_pres_rl,
                    AVG(t.tire_pressure_rr)                                     AS avg_tire_pres_rr,
                    -- Brake temperatures
                    AVG(t.brake_temp_fl)                                        AS avg_brake_temp_fl,
                    AVG(t.brake_temp_fr)                                        AS avg_brake_temp_fr,
                    AVG(t.brake_temp_rl)                                        AS avg_brake_temp_rl,
                    AVG(t.brake_temp_rr)                                        AS avg_brake_temp_rr,
                    MAX(t.brake_temp_fl)                                        AS max_brake_temp_fl,
                    MAX(t.brake_temp_fr)                                        AS max_brake_temp_fr,
                    MAX(t.brake_temp_rl)                                        AS max_brake_temp_rl,
                    MAX(t.brake_temp_rr)                                        AS max_brake_temp_rr,
                    -- Tire wear proxy
                    MAX(
                        MAX(t.tire_temp_fl, t.tire_temp_fr, t.tire_temp_rl, t.tire_temp_rr) -
                        MIN(t.tire_temp_fl, t.tire_temp_fr, t.tire_temp_rl, t.tire_temp_rr)
                    )                                                           AS max_tire_temp_delta
                FROM telemetry t
                JOIN laps l ON t.lap_id = l.id
                WHERE l.session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            cursor.close()
            self.return_connection(conn)


    def get_lap_telemetry(self, lap_id: int) -> List[Dict]:
        """Get all telemetry data for a lap"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM telemetry
                WHERE lap_id = ?
                ORDER BY timestamp
            """, (lap_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_session_analysis(self, session_id: int) -> Optional[Dict]:
        """Get analysis for a session"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse JSON fields
                if result.get('recommendations'):
                    result['recommendations'] = json.loads(result['recommendations'])
                if result.get('ideal_line_data'):
                    result['ideal_line_data'] = json.loads(result['ideal_line_data'])
                if result.get('braking_points'):
                    result['braking_points'] = json.loads(result['braking_points'])
                if result.get('acceleration_points'):
                    result['acceleration_points'] = json.loads(result['acceleration_points'])
                return result
            return None
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get session details by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            self.return_connection(conn)
    
    # Personal Records Methods
    
    def get_personal_records(self, track_name: str, car_name: str) -> Optional[Dict]:
        """Get personal records for a track/car combination"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM personal_records 
                WHERE track_name = ? AND car_name = ?
            """, (track_name, car_name))
            
            row = cursor.fetchone()
            if row:
                return {
                    'best_lap_time': row['best_lap_time'],
                    'best_sector_1': row['best_sector_1'],
                    'best_sector_2': row['best_sector_2'],
                    'best_sector_3': row['best_sector_3'],
                    'session_id': row['session_id'],
                    'achieved_date': row['achieved_date'],
                    'updated_date': row['updated_date']
                }
            return None
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def update_personal_records(self, track_name: str, car_name: str, 
                               session_id: int, lap_time: float,
                               sector_1: float = None, sector_2: float = None, 
                               sector_3: float = None) -> Dict[str, bool]:
        """Update personal records if new bests achieved. Returns dict of what was updated."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get current records
            current = self.get_personal_records(track_name, car_name)
            
            records_broken = {
                'lap': False,
                'sector_1': False,
                'sector_2': False,
                'sector_3': False
            }
            
            if not current:
                # First record for this track/car
                cursor.execute("""
                    INSERT INTO personal_records 
                    (track_name, car_name, best_lap_time, best_sector_1, 
                     best_sector_2, best_sector_3, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (track_name, car_name, lap_time, sector_1, sector_2, sector_3, session_id))
                records_broken = {'lap': True, 'sector_1': True, 'sector_2': True, 'sector_3': True}
                logger.info(f"🏆 New personal records set for {car_name} at {track_name}")
            else:
                # Check and update individual records
                updates = []
                values = []
                
                if lap_time < current['best_lap_time']:
                    updates.append("best_lap_time = ?")
                    values.append(lap_time)
                    updates.append("session_id = ?")
                    values.append(session_id)
                    records_broken['lap'] = True
                    logger.info(f"🏆 New lap record: {lap_time:.3f}s (was {current['best_lap_time']:.3f}s)")
                
                if sector_1 and (not current['best_sector_1'] or sector_1 < current['best_sector_1']):
                    updates.append("best_sector_1 = ?")
                    values.append(sector_1)
                    records_broken['sector_1'] = True
                
                if sector_2 and (not current['best_sector_2'] or sector_2 < current['best_sector_2']):
                    updates.append("best_sector_2 = ?")
                    values.append(sector_2)
                    records_broken['sector_2'] = True
                
                if sector_3 and (not current['best_sector_3'] or sector_3 < current['best_sector_3']):
                    updates.append("best_sector_3 = ?")
                    values.append(sector_3)
                    records_broken['sector_3'] = True
                
                if updates:
                    updates.append("updated_date = CURRENT_TIMESTAMP")
                    values.extend([track_name, car_name])
                    
                    cursor.execute(f"""
                        UPDATE personal_records 
                        SET {', '.join(updates)}
                        WHERE track_name = ? AND car_name = ?
                    """, values)
            
            conn.commit()
            return records_broken
            
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to update personal records: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def get_section_records(self, track_name: str, car_name: str) -> List[Dict]:
        """Get all section records for a track/car combination"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM section_records 
                WHERE track_name = ? AND car_name = ?
                ORDER BY section_id
            """, (track_name, car_name))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)
    
    def update_section_records(self, track_name: str, car_name: str,
                              session_id: int, sections: List[Dict]) -> List[int]:
        """Update section records if new bests achieved. Returns list of section IDs with new records."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get current section records
            current_records = {r['section_id']: r for r in self.get_section_records(track_name, car_name)}
            
            sections_improved = []
            
            for section in sections:
                section_id = section['section_id']
                section_type = section['type']
                time = section['time']
                avg_speed = section.get('avg_speed')
                max_speed = section.get('max_speed')
                
                current = current_records.get(section_id)
                
                if not current:
                    # New section record
                    cursor.execute("""
                        INSERT INTO section_records 
                        (track_name, car_name, section_id, section_type, best_time, 
                         best_avg_speed, best_max_speed, session_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (track_name, car_name, section_id, section_type, time, 
                          avg_speed, max_speed, session_id))
                    sections_improved.append(section_id)
                    
                elif time < current['best_time']:
                    # Improved section record
                    cursor.execute("""
                        UPDATE section_records 
                        SET best_time = ?, best_avg_speed = ?, best_max_speed = ?, 
                            session_id = ?, updated_date = CURRENT_TIMESTAMP
                        WHERE track_name = ? AND car_name = ? AND section_id = ?
                    """, (time, avg_speed, max_speed, session_id, track_name, car_name, section_id))
                    sections_improved.append(section_id)
                    logger.info(f"🏆 Section {section_id} ({section_type}) record: {time:.3f}s")
            
            conn.commit()
            
            if sections_improved:
                logger.info(f"🏆 Improved {len(sections_improved)} section records")
            
            return sections_improved
            
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Failed to update section records: {e}")
            raise
        finally:
            cursor.close()
            self.return_connection(conn)
    

    def get_unique_tracks(self) -> List[str]:
        """Get list of all unique tracks"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT track_name FROM sessions
                ORDER BY track_name
            """)
            rows = cursor.fetchall()
            return [row['track_name'] for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_history_sessions(self, track_name: str) -> List[Dict]:
        """Get all sessions for a specific track"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                WHERE track_name = ?
                ORDER BY start_time DESC
            """, (track_name,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_last_n_sessions_by_track(self, track_name: str, n: int = 3) -> List[Dict]:
        """Get the last N sessions for a specific track"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                WHERE track_name = ? AND total_laps > 0
                ORDER BY start_time DESC
                LIMIT ?
            """, (track_name, n))
            rows = cursor.fetchall()
            # Return in chronological order (oldest to newest) for charts
            return sorted([dict(row) for row in rows], key=lambda x: x['start_time'])
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_session_laps(self, session_id: int) -> List[Dict]:
        """Get all laps for a specific session"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM laps
                WHERE session_id = ?
                ORDER BY lap_number
            """, (session_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_last_n_laps_of_session(self, session_id: int, n: int = 3) -> List[Dict]:
        """Get the last N laps of a session (including invalid ones for analysis)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM laps
                WHERE session_id = ?
                ORDER BY lap_number DESC
                LIMIT ?
            """, (session_id, n))
            rows = cursor.fetchall()
            # Return in chronological order
            return sorted([dict(row) for row in rows], key=lambda x: x['lap_number'])
        finally:
            cursor.close()
            self.return_connection(conn)

    def close(self):
        """Close database (for compatibility with PostgreSQL version)"""
        logger.info("✓ Database connections closed")

