"""
Main Application - Orchestrates telemetry reading, data storage, and WebSocket streaming
"""
import asyncio
import time
import webbrowser
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import uvicorn
import subprocess
from threading import Thread

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import SERVER_CONFIG, TELEMETRY_CONFIG
from backend.domain.telemetry.reader import TelemetryReader
from backend.database.database import Database
from backend.domain.analysis.analyzer import DataAnalyzer
from backend.domain.telemetry.ffb import FFBAnalyzer
from backend.domain.analysis.pedals import PedalAnalyzer
from backend.api.websocket import get_app, get_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelemetrySystem:
    """Main telemetry system orchestrator"""
    
    def __init__(self):
        """Initialize all components"""
        self.telemetry_reader = TelemetryReader()
        self.database = Database()
        self.analyzer = DataAnalyzer(self.database)
        self.ffb_analyzer = FFBAnalyzer()
        self.pedal_analyzer = PedalAnalyzer()
        self.manager = get_manager()
        self.preferred_browser = "default"  # Added to support GUI selection
        
        # State tracking
        self.current_session_id: Optional[int] = None
        self.current_lap_id: Optional[int] = None
        self.current_lap_number: int = 0
        self.lap_telemetry_buffer: List[Dict[str, Any]] = []
        self.in_race: bool = False
        self.last_completed_lap: int = 0
        self.was_connected: bool = False  # Track AC connection state
        self.car_has_moved: bool = False  # Track if car has started moving
        self.ignore_first_lap: bool = False  # Flag to ignore first lap in practice mode
        
        # Sector tracking
        self.last_sector_index: int = -1  # Track which sector we're in
        self.sector_times: Dict[int, float] = {}  # Store sector times for current lap (1, 2, 3)

        # Lap validity tracking
        # AC resets isValidLap to False at the start of each new lap, so we must
        # track validity ourselves: once False during a lap, it stays False.
        self.current_lap_valid: bool = True
        self.volante_buffer: List[Dict[str, Any]] = []
        self.previous_steering_angle: float = 0.0
        self.previous_angular_velocity: float = 0.0
        self.previous_timestamp: float = 0.0
        
        # Session tracking for restarts
        self.last_session_index: int = -1
        self.current_session_type: str = ""
        
        # Initialize database schema
        self.database.create_schema()
        logger.info("✓ Telemetry system initialized")
    
    async def monitor_and_stream(self):
        """Main loop: monitor AC and stream telemetry"""
        logger.info("🔍 Monitoring for Assetto Corsa...")
        
        while True:
            try:
                # Try to connect to AC
                if not self.telemetry_reader.connected:
                    if self.telemetry_reader.connect():
                        logger.info("✓ Connected to Assetto Corsa")
                        
                        # Notify clients of connection
                        if not self.was_connected:
                            await self.manager.broadcast({
                                'type': 'ac_connected',
                                'message': 'Assetto Corsa conectado'
                            })
                            self.was_connected = True
                else:
                    # Check if we just connected
                    if not self.was_connected:
                        await self.manager.broadcast({
                            'type': 'ac_connected',
                            'message': 'Assetto Corsa conectado'
                        })
                        self.was_connected = True
                
                # If connected, check race state
                if self.telemetry_reader.connected:
                    # Check for session change/restart
                    snapshot = self.telemetry_reader.get_telemetry_snapshot()
                    if snapshot:
                        current_index = snapshot.get('session_index', -1)
                        current_type = snapshot.get('session_type', '')
                        
                        # Detect session change or restart
                        if self.in_race and (current_index != self.last_session_index or current_type != self.current_session_type):
                            logger.info(f"🔄 Session change detected! (Index: {self.last_session_index}->{current_index}, Type: {self.current_session_type}->{current_type})")
                            await self.on_race_end()
                            # Force immediate start of new session
                            self.in_race = False
                        
                        # Update session trackers
                        self.last_session_index = current_index
                        self.current_session_type = current_type

                    if self.telemetry_reader.is_in_race():
                        if not self.in_race:
                            await self.on_race_start()
                        
                        # Stream telemetry
                        await self.stream_telemetry()
                    else:
                        if self.in_race:
                            await self.on_race_end()
                else:
                    # Disconnected - notify clients
                    if self.was_connected:
                        logger.warning("⚠️ Assetto Corsa disconnected")
                        await self.manager.broadcast({
                            'type': 'ac_disconnected',
                            'message': 'Assetto Corsa desconectado - Esperando conexión...'
                        })
                        self.was_connected = False
                        
                        # End race if in progress
                        if self.in_race:
                            await self.on_race_end()
                
                # Sample rate
                await asyncio.sleep(TELEMETRY_CONFIG['sample_rate_ms'] / 1000.0)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)
    
    async def on_race_start(self):
        """Handle race start"""
        logger.info("🏁 Race started!")
        self.in_race = True
        
        # Get session info
        snapshot = self.telemetry_reader.get_telemetry_snapshot()
        if not snapshot:
            return
        
        # Create session in database with actual session type
        # Construct full track name with layout if available
        track = snapshot['track_name']
        config = snapshot.get('track_config')
        full_track_name = f"{track}@{config}" if config and config.strip() else track

        # Create session in database with actual session type
        self.current_session_id = self.database.create_session(
            track_name=full_track_name,
            car_name=snapshot['car_name'],
            session_type=snapshot['session_type'],  # Use actual session type from AC
            start_time=datetime.now()
        )
        
        # Reset state
        # In practice mode, start at -1 so after ignoring first lap we're at -1, then first real lap goes to 0
        # In race/qualifying, start at 0 normally
        session_type = snapshot['session_type'].lower()
        is_practice = 'practice' in session_type or 'practica' in session_type
        
        self.current_lap_number = -1 if is_practice else 0  # Start at -1 for practice, 0 for race
        self.last_completed_lap = -1  # Start at -1 so first lap (0) triggers completion
        self.lap_telemetry_buffer = []
        self.car_has_moved = False  # Reset movement detection
        
        # In practice mode, ignore the first lap completion (partial lap from spawn to finish line)
        # In race/qualifying, start from finish line so all laps are complete
        self.ignore_first_lap = is_practice
        
        # Reset sector tracking
        self.last_sector_index = -1
        self.sector_times = {}
        
        # Create the first lap immediately so telemetry data can be stored
        self.current_lap_id = self.database.create_lap(
            session_id=self.current_session_id,
            lap_number=1,  # Display lap number is always current_lap_number + 1
            lap_time=0.0,  # Provisional time, will be updated on completion
            is_valid=True,
            max_speed=0.0,
            avg_speed=0.0
        )
        
        # Notify clients with session type and track map
        await self.manager.broadcast({
            'type': 'race_start',
            'data': {
                'session_id': self.current_session_id,
                'track': snapshot['track_name'],
                'car': snapshot['car_name'],
                'session_type': snapshot['session_type']
            }
        })
    
    async def stream_telemetry(self):
        """Stream current telemetry to clients"""
        snapshot = self.telemetry_reader.get_telemetry_snapshot()
        if not snapshot:
            return
        
        # Detect if car has started moving (speed > 5 km/h)
        if not self.car_has_moved and snapshot['speed'] > 5:
            self.car_has_moved = True
            logger.info("🚗 Car started moving - timer started")
        
        # Only process telemetry if car has moved
        if not self.car_has_moved:
            # Still broadcast telemetry for live view, but don't record to database
            
            # --- INTEGRACIÓN GRUPO 3 ---
            # Analizamos FFB en tiempo real incluso si no se mueve
            ffb_data = self.ffb_analyzer.analyze_realtime(snapshot)
            snapshot.update(ffb_data)
            # ---------------------------
            
            await self.manager.broadcast({
                'type': 'telemetry',
                'data': snapshot
            })
            return
        
        # Check for sector completion
        current_sector = snapshot['current_sector_index']
        last_sector_time = snapshot['last_sector_time']
        
        # Detect sector change (sector completed)
        if current_sector != self.last_sector_index and self.last_sector_index >= 0:
            # A sector was just completed
            sector_number = self.last_sector_index + 1  # Convert 0-based to 1-based
            if sector_number in [1, 2, 3] and last_sector_time > 0:
                self.sector_times[sector_number] = last_sector_time / 1000.0  # Convert ms to seconds
                logger.debug(f"Sector {sector_number} completed: {self.sector_times[sector_number]:.3f}s")
        
        self.last_sector_index = current_sector
        
        # Check for lap completion
        current_lap = snapshot['completed_laps']
        if current_lap > self.last_completed_lap:
            await self.on_lap_complete(snapshot)

        self.last_completed_lap = current_lap

        # Update lap validity: once AC marks it invalid, it stays invalid for this lap.
        # We check AFTER on_lap_complete so the flag is reset for the new lap.
        if not snapshot.get('is_valid_lap', True):
            self.current_lap_valid = False
        
        # Add to buffer for database storage
        if self.current_lap_id:
            self.lap_telemetry_buffer.append({
                'lap_id': self.current_lap_id,
                'timestamp': snapshot['timestamp'],
                'speed': snapshot['speed'],
                'rpm': snapshot['rpm'],
                'gear': snapshot['gear'],
                'pos_x': snapshot['pos_x'],
                'pos_y': snapshot['pos_y'],
                'pos_z': snapshot['pos_z'],
                'normalized_position': snapshot.get('normalized_position', 0.0),
                'throttle': snapshot['throttle'],
                'brake': snapshot['brake'],
                'steering': snapshot['steering'],
                'g_force_lat': snapshot['g_force_lat'],
                'g_force_long': snapshot['g_force_long'],
                'tire_temp_fl': snapshot['tire_temp_fl'],
                'tire_temp_fr': snapshot['tire_temp_fr'],
                'tire_temp_rl': snapshot['tire_temp_rl'],
                'tire_temp_rr': snapshot['tire_temp_rr'],
                'tire_pressure_fl': snapshot['tire_pressure_fl'],
                'tire_pressure_fr': snapshot['tire_pressure_fr'],
                'tire_pressure_rl': snapshot['tire_pressure_rl'],
                'tire_pressure_rr': snapshot['tire_pressure_rr'],
                'brake_temp_fl': snapshot['brake_temp_fl'],
                'brake_temp_fr': snapshot['brake_temp_fr'],
                'brake_temp_rl': snapshot['brake_temp_rl'],
                'brake_temp_rr': snapshot['brake_temp_rr'],
                'fuel': snapshot['fuel'],
                'n_tires_out': snapshot.get('n_tires_out', 0)
            })
            
            # Calculate and store volante (steering wheel) data
            current_timestamp = snapshot['timestamp']
            current_steering = snapshot['steering']  # Already in degrees from AC
            
            # Calculate time delta
            if self.previous_timestamp > 0:
                delta_time = current_timestamp - self.previous_timestamp
                
                if delta_time > 0:
                    # Calculate frequency
                    sample_freq = 1.0 / delta_time
                    snapshot['sample_frequency'] = sample_freq
                    
                    # Calculate angular velocity (degrees per second)
                    angular_velocity = (current_steering - self.previous_steering_angle) / delta_time
                    
                    # Calculate angular acceleration (degrees per second squared)
                    angular_acceleration = (angular_velocity - self.previous_angular_velocity) / delta_time
                    
                    # Calculate sample frequency (Hz)
                    sample_frequency = 1.0 / delta_time
                    
                    # --- Update Snapshot for Broadcast ---
                    snapshot['angular_velocity'] = angular_velocity
                    snapshot['angular_acceleration'] = angular_acceleration
                    snapshot['sample_frequency'] = sample_frequency
                    
                    # Convert brake and throttle to percentages (AC provides 0-1 range)
                    brake_pct = snapshot['brake'] * 100.0
                    throttle_pct = snapshot['throttle'] * 100.0
                    
                    # Add to volante buffer
                    self.volante_buffer.append({
                        'lap_id': self.current_lap_id,
                        'timestamp': current_timestamp,
                        'steering_angle': current_steering,
                        'angular_velocity': angular_velocity,
                        'angular_acceleration': angular_acceleration,
                        'brake_percentage': brake_pct,
                        'throttle_percentage': throttle_pct,
                        'sample_frequency': sample_frequency
                    })
                    
                    # Update previous values
                    self.previous_angular_velocity = angular_velocity
            
            self.previous_steering_angle = current_steering
            self.previous_timestamp = current_timestamp
            
            # Flush buffers periodically (every 50 samples = ~0.5 seconds at 100Hz)
            if len(self.lap_telemetry_buffer) >= 50:
                self.database.insert_telemetry_batch(self.lap_telemetry_buffer)
                self.lap_telemetry_buffer = []
            
            if len(self.volante_buffer) >= 50:
                self.database.insert_volante_batch(self.volante_buffer)
                self.volante_buffer = []
        
        # Broadcast to clients
        
        # --- INTEGRACIÓN GRUPO 3 ---
        # Analizamos FFB en tiempo real
        ffb_data = self.ffb_analyzer.analyze_realtime(snapshot)
        snapshot.update(ffb_data)
        
        # Analizamos Pedales en tiempo real
        pedal_stats = self.pedal_analyzer.procesar_muestra(snapshot)
        snapshot.update(pedal_stats)
        # ---------------------------
        
        await self.manager.broadcast({
            'type': 'telemetry',
            'data': snapshot
        })
    
    async def on_lap_complete(self, snapshot: Dict[str, Any]):
        """Handle lap completion"""
        # Check if this is the first lap in practice mode (should be ignored)
        if self.ignore_first_lap and self.current_lap_number == -1:
            logger.info("⏭️ Ignoring first lap completion (practice mode - partial lap from spawn)")
            # Don't increment counter, don't create new lap, just set flag to false
            # The counter stays at -1, so next real lap will be counted as lap 0 (displays as 1)
            self.ignore_first_lap = False  # Only ignore the very first one
            # Clear the buffer for this partial lap
            self.lap_telemetry_buffer = []
            # Update last_completed_lap so we don't trigger again
            self.last_completed_lap = snapshot['completed_laps']
            return
        
        # Flush remaining telemetry for the completed lap
        if self.lap_telemetry_buffer:
            self.database.insert_telemetry_batch(self.lap_telemetry_buffer)
            self.lap_telemetry_buffer = []
        
        # Flush remaining volante data for the completed lap
        if self.volante_buffer:
            self.database.insert_volante_batch(self.volante_buffer)
            self.volante_buffer = []
        
        # Update the completed lap with final statistics
        if self.current_lap_id:
            lap_telemetry = self.database.get_lap_telemetry(self.current_lap_id)
            if lap_telemetry:
                max_speed = max([t['speed'] for t in lap_telemetry])
                avg_speed = sum([t['speed'] for t in lap_telemetry]) / len(lap_telemetry)
            else:
                max_speed = avg_speed = 0
            
            # Update the completed lap with actual time and stats
            lap_time = snapshot['last_lap_time'] / 1000.0  # Convert ms to seconds
            if lap_time > 0:
                conn = self.database.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE laps 
                        SET lap_time = ?, max_speed = ?, avg_speed = ?, is_valid = ?,
                            sector_1_time = ?, sector_2_time = ?, sector_3_time = ?
                        WHERE id = ?
                    """, (
                        lap_time, max_speed, avg_speed,
                        1 if self.current_lap_valid else 0,  # use tracked validity, not snapshot
                        self.sector_times.get(1), self.sector_times.get(2), self.sector_times.get(3),
                        self.current_lap_id
                    ))
                    conn.commit()
                    cursor.close()
                finally:
                    self.database.return_connection(conn)

                logger.info(f"✓ Lap {self.current_lap_number + 1} completed: {lap_time:.3f}s valid={self.current_lap_valid}")
        
        # Reset validity flag for the NEW lap (starts valid until AC says otherwise)
        self.current_lap_valid = True

        # Create new lap for the next one
        self.current_lap_number += 1
        self.current_lap_id = self.database.create_lap(
            session_id=self.current_session_id,
            lap_number=self.current_lap_number + 1,  # Display lap number
            lap_time=0.0,  # Provisional time, will be updated on completion
            is_valid=True,
            max_speed=0.0,
            avg_speed=0.0
        )
        
        # Reset sector times for the new lap
        self.sector_times = {}
        self.last_sector_index = -1
        
        # Update session with completed laps count
        self.database.update_session(
            self.current_session_id,
            total_laps=self.current_lap_number + 1,  # +1 because we just completed a lap (current_lap_number is 0-indexed)
            best_lap_time=snapshot['best_lap_time'] / 1000.0 if snapshot['best_lap_time'] > 0 else None
        )
        
        # Notify clients about the completed lap
        await self.manager.broadcast({
            'type': 'lap_complete',
            'data': {
                'lap_number': self.current_lap_number,
                'lap_time': snapshot['last_lap_time'] / 1000.0,
                'is_valid': self.current_lap_valid,
                'best_lap_time': snapshot['best_lap_time'] / 1000.0
            }
        })


    
    async def on_race_end(self):
        """Handle race end"""
        logger.info("🏁 Race ended!")
        self.in_race = False
        
        # Flush any remaining telemetry
        if self.lap_telemetry_buffer:
            self.database.insert_telemetry_batch(self.lap_telemetry_buffer)
            self.lap_telemetry_buffer = []
        
        # Flush any remaining volante data
        if self.volante_buffer:
            self.database.insert_volante_batch(self.volante_buffer)
            self.volante_buffer = []
            
        # Save pedal analysis
        self.pedal_analyzer.guardar_sesion()
        self.pedal_analyzer.resetear_sesion()
        
        # Update session end time
        if self.current_session_id:
            self.database.update_session(
                self.current_session_id,
                end_time=datetime.now()
            )
            
            # Perform analysis
            logger.info("📊 Analyzing session...")
            try:
                analysis = self.analyzer.analyze_session(self.current_session_id)
            except Exception as e:
                logger.error(f"❌ Error during session analysis: {e}")
                analysis = {
                    'recommendations': [f"Error durante el análisis: {str(e)}"],
                    'analysis_complete': False
                }
            
            # Broadcast analysis (or error info) to clients
            await self.manager.broadcast({
                'type': 'race_end',
                'data': {
                    'session_id': self.current_session_id,
                    'analysis': analysis
                }
            })
            
            if analysis.get('analysis_complete', True):
                logger.info(f"✓ Analysis complete: {len(analysis.get('recommendations', []))} recommendations")
            else:
                logger.warning("⚠️ Analysis finished with errors or incomplete data")
        
        # Reset state
        self.current_session_id = None
        self.current_lap_id = None
        self.current_lap_number = 0
    
    def open_browser_incognito(self, url: str):
        """Try to open the browser in incognito mode"""
        browsers = [
            # Chrome
            {"name": "chrome", "args": ["--incognito"], "paths": [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe")
            ]},
            # Brave
            {"name": "brave", "args": ["--incognito"], "paths": [
                os.path.expandvars(r"%ProgramFiles%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                os.path.expandvars(r"%LocalAppData%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe")
            ]},
            # Edge
            {"name": "edge", "args": ["--inprivate"], "paths": [
                os.path.expandvars(r"%ProgramFiles(x86)%\\Microsoft\Edge\Application\\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\\Microsoft\Edge\Application\\msedge.exe")
            ]},
            # Firefox
            {"name": "firefox", "args": ["--private-window"], "paths": [
                os.path.expandvars(r"%ProgramFiles%\\Mozilla Firefox\\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\\Mozilla Firefox\\firefox.exe")
            ]}
        ]
        
        opened = False
        
        # Prioritize preferred browser if it's not 'default'
        priority_browsers = browsers
        if self.preferred_browser != "default":
            # Reorder list to put preferred browser first
            matches = [b for b in browsers if self.preferred_browser.lower() in b["name"].lower()]
            others = [b for b in browsers if self.preferred_browser.lower() not in b["name"].lower()]
            priority_browsers = matches + others

        for browser in priority_browsers:
            for path in browser["paths"]:
                if os.path.exists(path):
                    try:
                        logger.info(f"🌐 Opening {browser['name']} in incognito mode...")
                        subprocess.Popen([path] + browser["args"] + [url], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                        opened = True
                        break
                    except Exception as e:
                        logger.debug(f"Could not open {browser['name']} at {path}: {e}")
            if opened:
                break
        
        if not opened:
            logger.warning("⚠️ No supported browser found for incognito mode. Using default browser.")
            webbrowser.open(url)

    def run(self):
        """Run the telemetry system"""
        logger.info("🚀 Starting Assetto Corsa Telemetry System")
        logger.info(f"🌐 Server will run on http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
        logger.info("📡 Waiting for Assetto Corsa to start a race...")
        
        # Start FastAPI server in a separate thread
        def run_server():
            uvicorn.run(
                get_app(),
                host=SERVER_CONFIG['host'],
                port=SERVER_CONFIG['port'],
                log_level="warning"
            )
        
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Open browser automatically after a short delay to ensure server is starting
        host = "127.0.0.1" # Using 127.0.0.1 is more reliable than 0.0.0.0 or localhost on some Windows setups
        url = f"http://{host}:{SERVER_CONFIG['port']}"
        
        # Increased delay for portable environments
        time.sleep(2.5)
        self.open_browser_incognito(url)
        
        # Run telemetry monitoring
        asyncio.run(self.monitor_and_stream())


def main():
    """Entry point"""
    try:
        system = TelemetrySystem()
        system.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
