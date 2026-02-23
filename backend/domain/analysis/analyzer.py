"""
Data Analysis Engine for Assetto Corsa Telemetry
Analyzes lap data and generates AI-powered recommendations
"""
try:
    import numpy as np
    from scipy import signal
    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False
    np = None
    signal = None

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import logging
import sys
import math
import os
import base64
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.database import Database
from backend.core.config import ANALYSIS_CONFIG, AC_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from backend.domain.analysis.map_analyzer import MapAnalyzer
    MAP_ANALYSIS_AVAILABLE = True
except Exception:
    logger.warning("MapAnalyzer not available (OpenCV/Numpy issue)")
    MAP_ANALYSIS_AVAILABLE = False
    MapAnalyzer = None


class DataAnalyzer:
    """Analyzes telemetry data and generates recommendations"""
    
    def __init__(self, database: Database):
        """Initialize analyzer with database connection"""
        self.db = database
        if MAP_ANALYSIS_AVAILABLE:
            try:
                self.map_analyzer = MapAnalyzer(AC_CONFIG['install_path'])
            except Exception as e:
                logger.error(f"Failed to initialize MapAnalyzer: {e}")
                self.map_analyzer = None
        else:
            self.map_analyzer = None
    
    def analyze_session(self, session_id: int) -> Dict[str, Any]:
        """
        Perform complete session analysis
        Returns recommendations and analysis data
        """
        logger.info(f"Analyzing session {session_id}...")
        
        # Check if analysis libraries are available
        if not ANALYSIS_AVAILABLE:
            logger.warning("Analysis libraries (numpy/scipy) not available. Install with: pip install numpy scipy")
            return {
                'recommendations': ["Análisis no disponible - faltan dependencias (numpy/scipy)"],
                'analysis_complete': False
            }
        
        # Get session laps
        laps = self.db.get_session_laps(session_id)
        logger.info(f"Session {session_id} has {len(laps)} total laps")
        
        if len(laps) < ANALYSIS_CONFIG['min_laps_for_analysis']:
            min_laps = ANALYSIS_CONFIG['min_laps_for_analysis']
            lap_word = "vuelta" if min_laps == 1 else "vueltas"
            logger.warning(f"Not enough laps for analysis (have {len(laps)}, need {min_laps})")
            return {
                'recommendations': [f"Completa al menos {min_laps} {lap_word} para un análisis detallado"],
                'analysis_complete': False
            }
        
        # Find best lap
        # Filter out incomplete laps (lap_time <= 0) which might be the current active lap
        complete_laps = [lap for lap in laps if lap['lap_time'] > 0]
        
        if not complete_laps:
            return {
                'recommendations': ["No se encontraron vueltas completas. Asegúrate de cruzar la meta."],
                'analysis_complete': False
            }
        
        # Try to find valid laps first
        valid_laps = [lap for lap in complete_laps if lap['is_valid']]
        
        if valid_laps:
            best_lap = min(valid_laps, key=lambda x: x['lap_time'])
        else:
            # Fallback to best complete lap (even if invalid)
            best_lap = min(complete_laps, key=lambda x: x['lap_time'])
            
        best_lap_id = best_lap['id']
        
        # Get telemetry for best lap and last lap
        best_lap_telemetry = self.db.get_lap_telemetry(best_lap_id)
        last_lap = complete_laps[-1]
        last_lap_telemetry = self.db.get_lap_telemetry(last_lap['id'])
        
        # Perform various analyses
        recommendations = []
        
        # 1. Braking analysis
        braking_recs = self._analyze_braking(best_lap_telemetry, last_lap_telemetry)
        recommendations.extend(braking_recs)
        
        # 2. Acceleration analysis
        accel_recs = self._analyze_acceleration(best_lap_telemetry, last_lap_telemetry)
        recommendations.extend(accel_recs)
        
        # 3. Corner speed analysis
        corner_recs = self._analyze_corners(best_lap_telemetry, last_lap_telemetry)
        recommendations.extend(corner_recs)
        
        # 4. Tire management
        tire_recs = self._analyze_tires(last_lap_telemetry)
        recommendations.extend(tire_recs)
        
        # 5. Consistency analysis
        consistency_recs = self._analyze_consistency(laps)
        recommendations.extend(consistency_recs)
        
        # 6. Sector analysis
        sector_recs = self._analyze_sectors(laps, best_lap)
        recommendations.extend(sector_recs)
        
        # Generate ideal line data
        ideal_line = self._calculate_ideal_line(best_lap_telemetry)
        
        # Identify braking and acceleration points
        braking_points = self._identify_braking_points(best_lap_telemetry)
        acceleration_points = self._identify_acceleration_points(best_lap_telemetry)
        
        # Extract track layout for visualization
        track_layout = self._extract_track_layout(best_lap_telemetry)
        
        # Detect track sections (straights and corners)
        # Try map-based analysis first
        map_sections = None
        if self.map_analyzer:
            try:
                map_sections = self.map_analyzer.analyze_map(session_info['track_name'])
            except Exception as e:
                logger.error(f"Map analysis failed: {e}")
        
        if map_sections:
            logger.info(f"Using map-based section detection for {session_info['track_name']}")
            track_sections = self._map_telemetry_to_sections(last_lap_telemetry, map_sections)
        else:
            logger.info("Fallback to telemetry-based section detection")
            track_sections = self._detect_track_sections(last_lap_telemetry)
        
        # Analyze performance in each section
        section_analysis = self._analyze_track_sections(track_sections)
        
        # Generate corner-specific recommendations from section analysis
        corner_recommendations = []
        if section_analysis:
            corner_count = 0
            for section in section_analysis:
                if section['type'] == 'corner':
                    corner_count += 1
                    # Check if this corner was off-track
                    if not section.get('is_valid', True) and section.get('recommended_speed'):
                        entry_speed = section.get('entry_speed', 0)
                        recommended_speed = section.get('recommended_speed', 0)
                        corner_recommendations.append(
                            f"⚠️ Curva {corner_count}: Saliste del circuito a {entry_speed:.0f} km/h. "
                            f"Frena antes para no salirte - velocidad recomendada: {recommended_speed:.0f} km/h."
                        )
        
        # Add corner recommendations to the main list
        recommendations.extend(corner_recommendations)
        
        # Get session info for track/car
        session_info = self.db.get_session(session_id)
        track_name = session_info['track_name']
        car_name = session_info['car_name']
        
        # Get personal records
        personal_records = self.db.get_personal_records(track_name, car_name)
        section_records = self.db.get_section_records(track_name, car_name)
        
        # Check and update records
        records_broken = {
            'lap': False,
            'sectors': [],
            'sections': []
        }
        
        # Update lap and sector records
        lap_records_broken = self.db.update_personal_records(
            track_name, car_name, session_id,
            best_lap['lap_time'],
            best_lap.get('sector_1_time'),
            best_lap.get('sector_2_time'),
            best_lap.get('sector_3_time')
        )
        
        records_broken['lap'] = lap_records_broken.get('lap', False)
        if lap_records_broken.get('sector_1'):
            records_broken['sectors'].append(1)
        if lap_records_broken.get('sector_2'):
            records_broken['sectors'].append(2)
        if lap_records_broken.get('sector_3'):
            records_broken['sectors'].append(3)
        
        # Update section records
        if section_analysis:
            sections_improved = self.db.update_section_records(
                track_name, car_name, session_id, section_analysis
            )
            records_broken['sections'] = sections_improved
        
        # Get updated records after potential changes
        personal_records = self.db.get_personal_records(track_name, car_name)
        section_records = self.db.get_section_records(track_name, car_name)
        
        # Add records info to recommendations if any were broken
        if records_broken['lap'] or records_broken['sectors'] or records_broken['sections']:
            records_msg = "🏆 ¡Nuevos récords personales establecidos! "
            if records_broken['lap']:
                records_msg += f"Mejor vuelta: {best_lap['lap_time']:.3f}s. "
            if records_broken['sectors']:
                records_msg += f"Sectores mejorados: {', '.join([f'S{s}' for s in records_broken['sectors']])}. "
            if records_broken['sections']:
                records_msg += f"{len(records_broken['sections'])} secciones mejoradas."
            recommendations.insert(0, records_msg)
        
        # Load and display official track map
        try:
            track_map_image = self._load_track_map(session_info['track_name'])
        except Exception as e:
            logger.error(f"Error loading track map in analysis: {e}")
            track_map_image = None
        
        analysis_result = {
            'recommendations': recommendations,
            'ideal_line_data': ideal_line,
            'braking_points': braking_points,
            'acceleration_points': acceleration_points,
            'track_layout': track_layout,
            'track_sections': section_analysis,
            'track_map_image': track_map_image,  # Official AC track map
            'personal_records': personal_records,
            'section_records': section_records,
            'records_broken': records_broken,
            'best_lap_id': best_lap_id,
            'best_lap_time': best_lap['lap_time'],
            'analysis_complete': True
        }
        
        # Save to database
        self.db.save_analysis(
            session_id=session_id,
            analysis_type='post_race',
            recommendations={'items': recommendations},
            ideal_line_data=ideal_line,
            braking_points=braking_points,
            acceleration_points=acceleration_points
        )
        
        logger.info(f"✓ Analysis complete: {len(recommendations)} recommendations generated")
        return analysis_result
    
    def _analyze_braking(self, best_lap: List[Dict], last_lap: List[Dict]) -> List[str]:
        """Analyze braking points and technique"""
        recommendations = []
        
        # Find braking zones (brake > 0.5)
        best_braking_zones = self._find_zones(best_lap, 'brake', threshold=0.5)
        last_braking_zones = self._find_zones(last_lap, 'brake', threshold=0.5)
        
        # Compare braking points
        for i, (best_zone, last_zone) in enumerate(zip(best_braking_zones, last_braking_zones)):
            if len(best_zone) == 0 or len(last_zone) == 0:
                continue
            
            # Calculate braking start position
            best_brake_start = best_zone[0]['pos_x']
            last_brake_start = last_zone[0]['pos_x']
            
            distance_diff = abs(best_brake_start - last_brake_start)
            
            if distance_diff > 5:  # More than 5 meters difference
                if last_brake_start < best_brake_start:
                    recommendations.append(
                        f"🔴 Curva {i+1}: Frenaste {distance_diff:.1f}m antes que en tu mejor vuelta. "
                        f"Intenta frenar más tarde para llevar más velocidad a la curva."
                    )
                else:
                    recommendations.append(
                        f"🟡 Curva {i+1}: Frenaste {distance_diff:.1f}m después que en tu mejor vuelta. "
                        f"Esto podría ser demasiado tarde - verifica si estás perdiendo el ápice."
                    )
        
        return recommendations
    
    def _analyze_acceleration(self, best_lap: List[Dict], last_lap: List[Dict]) -> List[str]:
        """Analyze acceleration points"""
        recommendations = []
        
        # Find acceleration zones (throttle > 0.8)
        best_accel_zones = self._find_zones(best_lap, 'throttle', threshold=0.8)
        last_accel_zones = self._find_zones(last_lap, 'throttle', threshold=0.8)
        
        for i, (best_zone, last_zone) in enumerate(zip(best_accel_zones, last_accel_zones)):
            if len(best_zone) == 0 or len(last_zone) == 0:
                continue
            
            # Check when full throttle was applied
            best_throttle_time = best_zone[0]['timestamp']
            last_throttle_time = last_zone[0]['timestamp']
            
            time_diff = last_throttle_time - best_throttle_time
            
            if time_diff > 0.2:  # More than 0.2s later
                recommendations.append(
                    f"🟢 Salida {i+1}: Aplicaste acelerador a fondo {time_diff:.2f}s después que en tu mejor vuelta. "
                    f"Intenta acelerar antes para mejor velocidad de salida."
                )
        
        return recommendations
    
    def _analyze_corners(self, best_lap: List[Dict], last_lap: List[Dict]) -> List[str]:
        """Analyze corner speeds"""
        recommendations = []
        
        # Find corners (high steering angle, low speed)
        best_corners = self._identify_corners(best_lap)
        last_corners = self._identify_corners(last_lap)
        
        for i, (best_corner, last_corner) in enumerate(zip(best_corners, last_corners)):
            if not best_corner or not last_corner:
                continue
            
            # Check for off-track (more than 2 tires out)
            max_tires_out = max([p.get('n_tires_out', 0) for p in last_corner])
            if max_tires_out > 2:
                entry_speed = last_corner[0]['speed']
                recommendations.append(
                    f"⚠️ Curva {i+1}: Velocidad de entrada {entry_speed:.0f} km/h - Demasiado rápido (Salida de pista). "
                    f"Intenta frenar antes para mantener el coche dentro de los límites."
                )
                continue  # Skip speed comparison if off-track

            # Find minimum speed (apex)
            best_apex_speed = min([p['speed'] for p in best_corner])
            last_apex_speed = min([p['speed'] for p in last_corner])
            
            speed_diff = best_apex_speed - last_apex_speed
            
            if speed_diff > 3:  # More than 3 km/h difference
                recommendations.append(
                    f"🔵 Curva {i+1}: Tu velocidad en el ápice fue {speed_diff:.1f} km/h más lenta que en tu mejor vuelta. "
                    f"Intenta llevar más velocidad en la curva o ajusta tu trazada."
                )
        
        return recommendations
    
    def _analyze_tires(self, last_lap: List[Dict]) -> List[str]:
        """Analyze tire temperatures and pressures"""
        recommendations = []
        
        if not last_lap:
            return recommendations
        
        # Get average tire temps
        avg_temps = {
            'fl': np.mean([p['tire_temp_fl'] for p in last_lap]),
            'fr': np.mean([p['tire_temp_fr'] for p in last_lap]),
            'rl': np.mean([p['tire_temp_rl'] for p in last_lap]),
            'rr': np.mean([p['tire_temp_rr'] for p in last_lap])
        }
        
        optimal_min, optimal_max = ANALYSIS_CONFIG['optimal_tire_temp_range']
        
        for tire, temp in avg_temps.items():
            tire_name = {'fl': 'Delantero-Izquierdo', 'fr': 'Delantero-Derecho', 'rl': 'Trasero-Izquierdo', 'rr': 'Trasero-Derecho'}[tire]
            
            if temp < optimal_min:
                recommendations.append(
                    f"🥶 Neumático {tire_name}: Temperatura {temp:.1f}°C está por debajo del rango óptimo ({optimal_min}-{optimal_max}°C). "
                    f"Considera conducción más agresiva o ajustes de presión."
                )
            elif temp > optimal_max:
                recommendations.append(
                    f"🔥 Neumático {tire_name}: Temperatura {temp:.1f}°C está por encima del rango óptimo ({optimal_min}-{optimal_max}°C). "
                    f"Podrías estar sobrecargando este neumático. Considera inputs más suaves o menor presión."
                )
        
        # Check for imbalance
        front_diff = abs(avg_temps['fl'] - avg_temps['fr'])
        rear_diff = abs(avg_temps['rl'] - avg_temps['rr'])
        
        if front_diff > 10:
            recommendations.append(
                f"⚖️ Desequilibrio de temperatura en neumáticos delanteros: {front_diff:.1f}°C de diferencia. "
                f"Revisa tu trazada en las curvas - podrías estar cargando más un lado que el otro."
            )
        
        if rear_diff > 10:
            recommendations.append(
                f"⚖️ Desequilibrio de temperatura en neumáticos traseros: {rear_diff:.1f}°C de diferencia. "
                f"Esto podría indicar problemas de configuración o salidas de curva inconsistentes."
            )
        
        return recommendations
    
    def _analyze_consistency(self, laps: List[Dict]) -> List[str]:
        """Analyze lap time consistency"""
        recommendations = []
        
        valid_laps = [lap for lap in laps if lap['is_valid']]
        if len(valid_laps) < 3:
            return recommendations
        
        lap_times = [lap['lap_time'] for lap in valid_laps]
        std_dev = np.std(lap_times)
        mean_time = np.mean(lap_times)
        
        consistency_pct = (std_dev / mean_time) * 100
        
        if consistency_pct < 1:
            recommendations.append(
                f"✨ ¡Excelente consistencia! Tus tiempos de vuelta varían solo un {consistency_pct:.2f}%. "
                f"Mantén este ritmo y enfócate en encontrar pequeñas mejoras."
            )
        elif consistency_pct < 2:
            recommendations.append(
                f"👍 Buena consistencia con {consistency_pct:.2f}% de variación. "
                f"Trabaja en mantener esto mientras buscas tiempos más rápidos."
            )
        else:
            recommendations.append(
                f"📊 La variación de tiempos de vuelta es {consistency_pct:.2f}%. "
                f"Enfócate en la consistencia antes de buscar vueltas más rápidas. Encuentra un ritmo sostenible."
            )
        
        return recommendations
    
    def _analyze_sectors(self, laps: List[Dict], best_lap: Dict) -> List[str]:
        """Analyze sector times"""
        recommendations = []
        
        valid_laps = [lap for lap in laps if lap['is_valid']]
        if len(valid_laps) < 2:
            return recommendations
        
        last_lap = valid_laps[-1]
        
        # Compare sectors
        for sector in [1, 2, 3]:
            best_sector_key = f'sector_{sector}_time'
            
            if best_lap.get(best_sector_key) and last_lap.get(best_sector_key):
                best_time = best_lap[best_sector_key]
                last_time = last_lap[best_sector_key]
                diff = last_time - best_time
                
                if diff > 0.1:  # Lost more than 0.1s
                    recommendations.append(
                        f"⏱️ Sector {sector}: Perdiste {diff:.3f}s comparado con tu mejor vuelta. "
                        f"Revisa esta sección para posibles mejoras."
                    )
                elif diff < -0.05:  # Gained time
                    recommendations.append(
                        f"🚀 Sector {sector}: ¡Ganaste {abs(diff):.3f}s! "
                        f"Gran mejora en esta sección."
                    )
        
        return recommendations
    
    def _find_zones(self, telemetry: List[Dict], field: str, threshold: float) -> List[List[Dict]]:
        """Find zones where a field exceeds a threshold"""
        zones = []
        current_zone = []
        
        for point in telemetry:
            if point.get(field, 0) > threshold:
                current_zone.append(point)
            else:
                if current_zone:
                    zones.append(current_zone)
                    current_zone = []
        
        if current_zone:
            zones.append(current_zone)
        
        return zones
    
    def _identify_corners(self, telemetry: List[Dict]) -> List[List[Dict]]:
        """Identify corner sections"""
        corners = []
        current_corner = []
        
        for point in telemetry:
            # Corner: high steering angle (>0.2) and lower speed
            if abs(point.get('steering', 0)) > 0.2 and point.get('speed', 0) < 200:
                current_corner.append(point)
            else:
                if len(current_corner) > 10:  # Minimum 10 points to be a corner
                    corners.append(current_corner)
                current_corner = []
        
        if len(current_corner) > 10:
            corners.append(current_corner)
        
        return corners
    
    def _calculate_ideal_line(self, telemetry: List[Dict]) -> Dict[str, Any]:
        """Calculate ideal racing line from best lap"""
        if not telemetry:
            return {}
        
        # Extract position and speed data
        positions = [(p['pos_x'], p['pos_z']) for p in telemetry]
        speeds = [p['speed'] for p in telemetry]
        
        return {
            'positions': positions,
            'speeds': speeds,
            'total_points': len(positions)
        }
    
    def _identify_braking_points(self, telemetry: List[Dict]) -> Dict[str, Any]:
        """Identify key braking points"""
        braking_zones = self._find_zones(telemetry, 'brake', threshold=0.5)
        
        braking_points = []
        for i, zone in enumerate(braking_zones):
            if zone:
                braking_points.append({
                    'zone_id': i + 1,
                    'start_position': (zone[0]['pos_x'], zone[0]['pos_z']),
                    'max_brake_pressure': max([p['brake'] for p in zone]),
                    'duration': zone[-1]['timestamp'] - zone[0]['timestamp']
                })
        
        return {'points': braking_points}
    
    def _identify_acceleration_points(self, telemetry: List[Dict]) -> Dict[str, Any]:
        """Identify key acceleration points"""
        accel_zones = self._find_zones(telemetry, 'throttle', threshold=0.8)
        
        accel_points = []
        for i, zone in enumerate(accel_zones):
            if zone:
                accel_points.append({
                    'zone_id': i + 1,
                    'start_position': (zone[0]['pos_x'], zone[0]['pos_z']),
                    'full_throttle_time': zone[-1]['timestamp'] - zone[0]['timestamp']
                })
        
        return {'points': accel_points}
    
    def _extract_track_layout(self, telemetry: List[Dict]) -> Dict[str, Any]:
        """Extract and normalize track coordinates for visualization"""
        if not telemetry:
            return {}
        
        # Extract all position coordinates
        positions = [(p['pos_x'], p['pos_z']) for p in telemetry]
        
        if not positions:
            return {}
        
        # Find bounds for normalization
        x_coords = [p[0] for p in positions]
        z_coords = [p[1] for p in positions]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_z, max_z = min(z_coords), max(z_coords)
        
        # Calculate scale to fit in canvas (with padding)
        x_range = max_x - min_x
        z_range = max_z - min_z
        
        # Normalize to 0-1 range
        normalized_positions = []
        for x, z in positions:
            norm_x = (x - min_x) / x_range if x_range > 0 else 0.5
            norm_z = (z - min_z) / z_range if z_range > 0 else 0.5
            normalized_positions.append([norm_x, norm_z])
        
        # Extract speed data for color coding
        speeds = [p['speed'] for p in telemetry]
        
        return {
            'positions': normalized_positions,
            'speeds': speeds,
            'bounds': {
                'min_x': min_x,
                'max_x': max_x,
                'min_z': min_z,
                'max_z': max_z
            },
            'total_points': len(positions)
        }
    
    def _detect_track_sections(self, telemetry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect straight and corner sections based on telemetry
        Returns list of section objects
        """
        if not telemetry:
            return []
            
        # DEBUG: Check max values in telemetry to ensure we have valid data
        max_g_lat = max([abs(p.get('g_force_lat', 0)) for p in telemetry]) if telemetry else 0
        max_steering = max([abs(p.get('steering', 0)) for p in telemetry]) if telemetry else 0
        logger.info(f"📊 DEBUG SECTION DETECTION: Max G-Lat: {max_g_lat:.4f}, Max Steering: {max_steering:.4f}")
        logger.info(f"📊 DEBUG: Thresholds used: G-Lat > 0.15, Steering > 5.0")

        sections = []
        current_section = {'type': None, 'start_idx': 0, 'points': []}
        current_direction = None # 'left' or 'right'

        for i, point in enumerate(telemetry):
            # Get raw values for direction detection
            raw_g_lat = point.get('g_force_lat', 0)
            raw_steering_rad = point.get('steering', 0)
            
            # Convert steering from Radians to Degrees
            # AC uses radians, so ~0.9 rad is ~51 degrees
            steering_deg_abs = abs(raw_steering_rad * (180 / math.pi))
            
            g_lat = abs(raw_g_lat)
            
            # Determine if it's a corner or straight
            # Adjusted Thresholds: 5.0 degrees steering OR 0.15G Lateral
            # Lowered to detect corners more reliably across different tracks/wheels
            if g_lat > 0.15 or steering_deg_abs > 5.0:
                point_type = 'corner'
                # Determine direction: new_direction
                new_direction = 'right' if raw_g_lat > 0 else 'left'
            else:
                point_type = 'straight'
                new_direction = None
            
            # Check if we need to start a new section
            if current_section['type'] is None:
                # First section
                current_section['type'] = point_type
                current_section['start_idx'] = i
                current_section['points'].append(point)
                current_section['direction'] = new_direction # Store direction
                current_direction = new_direction
                
            elif current_section['type'] == point_type:
                # Same type
                
                # Check for direction change in corners
                if point_type == 'corner' and new_direction != current_direction and new_direction is not None and current_direction is not None:
                    # Direction changed! Save current curve and start new one
                    # Removed length restriction to capture short corners
                    if len(current_section['points']) >= 1: 
                        sections.append({
                            'type': current_section['type'],
                            'start_idx': current_section['start_idx'],
                            'end_idx': i - 1,
                            'points': current_section['points'],
                            'direction': current_section.get('direction') # Store direction
                        })
                    
                    # Start new corner section
                    current_section = {
                        'type': point_type,
                        'start_idx': i,
                        'points': [point],
                        'direction': new_direction # Store direction
                    }
                    current_direction = new_direction
                else:
                    # Continue current section
                    current_section['points'].append(point)
                    
            else:
                # Type changed (Straight <-> Corner)
                # MINIMUM LENGTH CHECK: Reduce noise by ignoring short glitches (< 5 points)
                if len(current_section['points']) >= 5: 
                    sections.append({
                        'type': current_section['type'],
                        'start_idx': current_section['start_idx'],
                        'end_idx': i - 1,
                        'points': current_section['points'],
                        'direction': current_section.get('direction') # Store direction
                    })
                    
                    # Start new section
                    current_section = {
                        'type': point_type,
                        'start_idx': i,
                        'points': [point],
                        'direction': new_direction # Store direction
                    }
                    current_direction = new_direction
                else:
                    # Section too short! Treat as noise and merge into current valid 'current_section' somehow?
                    # Actually, if we are here, it means 'current_section' (the one ending) was too short.
                    # We should probably merge it into the PREVIOUS valid section if possible, 
                    # OR just change its type to match the new 'point_type' effectively extending the new section backwards?
                    # Simplest robust approach:
                    # If the ending section (`current_section`) is too short, we treat its points as part of the NEW section.
                    # e.g. Straight -> short Corner -> Straight. The short Corner becomes part of the Straight.
                    
                    # However, here we are starting a NEW section of a DIFFERENT type.
                    # If we discard the old one, we must add its points to... something.
                    
                    # Strategy: If previous section exists in `sections`, append to it.
                    if sections:
                        previous_section = sections[-1]
                        # Append points to previous section and update end_idx
                        previous_section['points'].extend(current_section['points'])
                        previous_section['end_idx'] = i - 1
                    
                    # Now start the new section as normal
                    current_section = {
                        'type': point_type,
                        'start_idx': i,
                        'points': [point]
                    }
                    current_direction = new_direction

        # Add the last section
        if len(current_section['points']) >= 5:
            sections.append({
                'type': current_section['type'],
                'start_idx': current_section['start_idx'],
                'end_idx': len(telemetry) - 1,
                'points': current_section['points'],
                'direction': current_section.get('direction') # Store direction
            })
        elif sections:
             # Merge tail into previous
             sections[-1]['points'].extend(current_section['points'])
             sections[-1]['end_idx'] = len(telemetry) - 1
        
        # Merge split sections (Smart Merging)
        merged_sections = self._merge_track_sections(sections)
        
        logger.info(f"📊 DEBUG: Found {len(merged_sections)} total sections after merging")
        return merged_sections
    
    def _merge_track_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Robust Clustering of track sections.
        Merges ANY sequence of broken sections into a single logical block.
        Example: Corner(Right) -> Short Straight -> Corner(Right) -> Short Str... -> Corner(Right)
        Becomes: One long Corner(Right)
        """
        if not sections:
            return []
            
        merged = []
        
        # Start the first cluster
        current_cluster = sections[0].copy()
        
        for i in range(1, len(sections)):
            next_section = sections[i]
            
            # Logic: Can we merge 'next_section' into 'current_cluster'?
            should_merge = False
            
            # 1. Same Type and Same Direction (Basic merge)
            if (next_section['type'] == current_cluster['type'] and 
                next_section.get('direction') == current_cluster.get('direction')):
                should_merge = True
                
            # 2. Interruption Handling (The "Pumping Wheel" fix)
            # If we are in a CORNER, and the next thing is a SHORT STRAIGHT
            elif current_cluster['type'] == 'corner' and next_section['type'] == 'straight':
                # Check if it's a short interruption (< 15 points / ~1.5s)
                if len(next_section['points']) < 15:
                    # Look ahead! Is the thing AFTER this straight a curve of the SAME direction?
                    # Or is this straight just the end of the curve?
                    # If we blindly merge the straight, we turn it into a corner.
                    # We should only merge if it CONTINUES as a corner afterwards.
                    
                    # Check if there is a next_next section
                    if i + 1 < len(sections):
                        next_next = sections[i+1]
                        if (next_next['type'] == 'corner' and 
                            next_next.get('direction') == current_cluster.get('direction')):
                            # Yes! Corner -> Short Straight -> Corner (Same Dir)
                            should_merge = True
            
            # 3. Straight Handling
            # If we are in a STRAIGHT, and next is a SHORT CORNER (noise)
            elif current_cluster['type'] == 'straight' and next_section['type'] == 'corner':
                if len(next_section['points']) < 10: # < 1s noise
                     # Check if it returns to straight
                     if i + 1 < len(sections):
                        next_next = sections[i+1]
                        if next_next['type'] == 'straight':
                            should_merge = True

            if should_merge:
                # Merge logic
                current_cluster['points'].extend(next_section['points'])
                current_cluster['end_idx'] = next_section['end_idx']
                # Keep the type/direction of the CLUSTER (dominating type)
            else:
                # Cannot merge, close current cluster and start new one
                merged.append(current_cluster)
                current_cluster = next_section.copy()
        
        # Append the final cluster
        merged.append(current_cluster)
            
        return merged

    def _map_telemetry_to_sections(self, telemetry: List[Dict[str, Any]], map_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map telemetry points to map-defined sections using nearest neighbor search.
        """
        if not telemetry or not map_sections:
            return []
            
        try:
            from scipy.spatial import KDTree
        except ImportError:
            logger.warning("Scipy not available for KDTree, falling back to heuristic")
            return self._detect_track_sections(telemetry)

        # 1. Build Index of Map Points
        # Flatten map sections into points with section_id
        map_points = []
        point_to_section_map = [] # index -> section_index_in_list
        
        for idx, section in enumerate(map_sections):
            for pt in section['points']:
                # pt is {'world_x': ..., 'world_z': ...}
                map_points.append([pt['world_x'], pt['world_z']])
                point_to_section_map.append(idx)
                
        if not map_points:
            return []
            
        kdtree = KDTree(map_points)
        
        # 2. Query for each telemetry point
        telemetry_coords = [[p['pos_x'], p['pos_z']] for p in telemetry]
        _, nearest_indices = kdtree.query(telemetry_coords)
        
        # 3. Group telemetry points by assigned section
        matched_sections = []
        current_section_idx = -1
        current_telemetry_points = []
        current_map_section_idx = -1
        
        for i, map_point_idx in enumerate(nearest_indices):
            # Which map section does this point belong to?
            assigned_section_idx = point_to_section_map[map_point_idx]
            point = telemetry[i]
            
            if assigned_section_idx != current_map_section_idx:
                # Section change
                if current_telemetry_points:
                    # Save previous section
                    map_sec = map_sections[current_map_section_idx]
                    matched_sections.append({
                        'type': map_sec['type'],
                        'start_idx': current_telemetry_points[0]['_idx'], # We need original index?
                        'end_idx': current_telemetry_points[-1]['_idx'],
                        'points': current_telemetry_points,
                        'direction': None # Could derive from map or telemetry
                    })
                
                # Start new section
                current_map_section_idx = assigned_section_idx
                current_telemetry_points = []
                
            # Add point to current section (temporarily store index for reconstruction)
            point['_idx'] = i
            current_telemetry_points.append(point)
            
        # Add final section
        if current_telemetry_points:
            map_sec = map_sections[current_map_section_idx]
            matched_sections.append({
                'type': map_sec['type'],
                'start_idx': current_telemetry_points[0]['_idx'],
                'end_idx': current_telemetry_points[-1]['_idx'],
                'points': current_telemetry_points,
                'direction': None
            })
            
        return matched_sections
    
    def _analyze_track_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate performance metrics for each track section"""
        analyzed_sections = []
        
        for i, section in enumerate(sections):
            points = section['points']
            
            if not points:
                continue
            
            # Helper for mean calculation
            def safe_mean(values):
                if not values: return 0
                # Assuming numpy is imported as np at the module level
                try:
                    import numpy as np
                    return np.mean(values)
                except (ImportError, NameError):
                    return sum(values) / len(values)

            # Calculate metrics
            speeds = [p['speed'] for p in points]
            avg_speed = safe_mean(speeds)
            min_speed = min(speeds) if speeds else 0
            max_speed = max(speeds) if speeds else 0
            entry_speed = speeds[0] if speeds else 0
            exit_speed = speeds[-1] if speeds else 0
            
            # Time spent in section
            time_in_section = points[-1]['timestamp'] - points[0]['timestamp'] if len(points) >= 2 else 0
            
            # G-forces
            g_lat = [abs(p.get('g_force_lat', 0)) for p in points]
            g_long = [abs(p.get('g_force_long', 0)) for p in points]
            avg_g_lat = safe_mean(g_lat)
            avg_g_long = safe_mean(g_long)
            max_g_lat = max(g_lat) if g_lat else 0
            max_g_long = max(g_long) if g_long else 0
            
            # Pedal Inputs
            brakes = [p['brake'] for p in points]
            throttles = [p['throttle'] for p in points]
            max_brake = max(brakes) if brakes else 0
            avg_brake = safe_mean(brakes)
            max_throttle = max(throttles) if throttles else 0
            avg_throttle = safe_mean(throttles)
            full_throttle_pct = (sum(1 for t in throttles if t > 0.95) / len(throttles) * 100) if throttles else 0
            
            # Start and end positions (normalized indices)
            start_position = section['start_idx']
            end_position = section['end_idx']
            
            # Check validity (Off-track)
            # A section is invalid if any point has n_tires_out > 2 (3 or 4 tires out)
            max_tires_out = max([p.get('n_tires_out', 0) for p in points]) if points else 0
            is_valid = max_tires_out <= 2
            
            recommendation = None
            recommended_speed = None
            
            if not is_valid and section['type'] == 'corner':
                # Generate recommendation for off-track corners
                entry_speed = speeds[0] if speeds else 0
                
                # Better speed calculation based on corner characteristics
                # Use the minimum speed (apex) from the corner as a reference
                min_corner_speed = min(speeds) if speeds else 0
                
                # Calculate recommended entry speed:
                # If we have a valid min speed, use it as reference
                # Otherwise, use 85% of entry speed (more conservative than 90%)
                if min_corner_speed > 0 and min_corner_speed < entry_speed:
                    # Recommended entry should allow reaching the apex speed
                    # Add a safety margin: apex speed + 15%
                    recommended_speed = round(min_corner_speed * 1.15, 1)
                else:
                    # Fallback: reduce entry speed by 15%
                    recommended_speed = round(entry_speed * 0.85, 1)
                
                # Ensure recommended speed is not higher than entry speed
                if recommended_speed >= entry_speed:
                    recommended_speed = round(entry_speed * 0.85, 1)
                
                recommendation = "Saliste de pista"
            
            analyzed_sections.append({
                'section_id': i + 1,
                'type': section['type'],
                'direction': section.get('direction'),  # 'left' or 'right'
                'start_idx': start_position,
                'end_idx': end_position,
                'entry_speed': round(speeds[0], 2) if speeds else 0,
                'exit_speed': round(speeds[-1], 2) if speeds else 0,
                'avg_speed': round(avg_speed, 2),
                'min_speed': round(min_speed, 2),
                'max_speed': round(max_speed, 2),
                'time': round(time_in_section, 3),
                'avg_g_lateral': round(avg_g_lat, 2),
                'avg_g_longitudinal': round(avg_g_long, 2),
                'max_g_lateral': round(max_g_lat, 2),
                'max_g_longitudinal': round(max_g_long, 2),
                'max_brake': round(max_brake, 1),
                'avg_brake': round(avg_brake, 1),
                'max_throttle': round(max_throttle, 1),
                'avg_throttle': round(avg_throttle, 1),
                'full_throttle_pct': round(full_throttle_pct, 1),
                'is_valid': is_valid,
                'recommendation': recommendation,
                'recommended_speed': recommended_speed
            })
        
        return analyzed_sections
    
    def _load_track_map(self, track_name: str) -> Optional[str]:
        """
        Load official track map from Assetto Corsa installation.
        Returns base64 encoded PNG image or None if not found.
        AC tracks can store maps at:
          - ui/outline.png          (single-layout tracks)
          - ui/{layout}/outline.png (multi-layout tracks)
          - ui/{layout}/map.png     (some tracks use map.png)
        """
        try:
            clean_track_name = track_name.split('@')[0]
            ac_install_path = AC_CONFIG.get('install_path', '')
            if not ac_install_path:
                logger.warning("AC install path not configured")
                return None

            track_ui_dir = Path(ac_install_path) / "content" / "tracks" / clean_track_name / "ui"
            logger.info(f"Searching track map for '{clean_track_name}' in {track_ui_dir}")

            if not track_ui_dir.exists():
                logger.warning(f"Track UI dir not found: {track_ui_dir}")
                return None

            # Build list of candidate paths to try (in priority order)
            # Build list of candidate paths to try (in priority order)
            candidates = []
            
            # 1. Specific layout if available
            layout_name = track_name.split('@')[1] if '@' in track_name else None
            
            if layout_name:
                layout_dir = track_ui_dir / layout_name
                # Check specific layout files
                candidates.append(layout_dir / "outline.png")
                candidates.append(layout_dir / "map.png")
                # Also check if layout has its OWN ui folder
                candidates.append(layout_dir / "ui" / "outline.png")
                candidates.append(layout_dir / "ui" / "map.png")
            
            # 2. Root/Default files (Fallback or Single Layout)
            candidates.append(track_ui_dir / "outline.png")
            candidates.append(track_ui_dir / "map.png")
            
            # 3. Only search subdirectories if NO layout specified and we failed to find Root map?
            # Or if we want to be "smart" but risky?
            # Given user complaint "map doesn't correspond", we remove the blind iteration.
            # If layout is specified, we check it. If not, we check root.
            # We do NOT iterate random subdirectories anymore.

            for path in candidates:
                if path.exists():
                    with open(path, 'rb') as f:
                        encoded = base64.b64encode(f.read()).decode('utf-8')
                    logger.info(f"✓ Track map loaded from: {path}")
                    return encoded

            logger.warning(f"No track map found for '{clean_track_name}' (searched {len(candidates)} paths)")
            return None

        except Exception as e:
            logger.error(f"Error loading track map: {e}")
            return None

    def build_single_session_lap_table(self, session_id: int) -> Dict[str, Any]:
        """
        Build the lap comparison table for a single session.
        Returns the same structure as lap_comparison_table in analyze_last_3_races.
        """
        session_laps = self.db.get_session_laps(session_id)
        if not session_laps:
            return {'lap_comparison_table': [], 'race_pace_telemetry': []}

        valid_laps = [l for l in session_laps if l['lap_time'] > 0]
        best_lap_time_in_session = min((l['lap_time'] for l in valid_laps), default=None)

        raw_rows = []
        # Sort by ID to ensure chronological order
        sorted_laps = sorted(session_laps, key=lambda x: x['id'])
        display_lap_number = 0

        for lap in sorted_laps:
            if lap['lap_time'] <= 0:
                continue
            
            display_lap_number += 1
            tel = self.db.get_lap_telemetry_stats(lap['id'])

            def _r(v, d=1): return round(v, d) if v else None
            def _avg4(a, b, c, d): return round((a+b+c+d)/4, 1) if all(x for x in [a, b, c, d]) else None

            avg_tire_temp = _avg4(
                tel.get('avg_tire_temp_fl') or 0, tel.get('avg_tire_temp_fr') or 0,
                tel.get('avg_tire_temp_rl') or 0, tel.get('avg_tire_temp_rr') or 0
            )
            max_tire_temp = max(
                tel.get('max_tire_temp_fl') or 0, tel.get('max_tire_temp_fr') or 0,
                tel.get('max_tire_temp_rl') or 0, tel.get('max_tire_temp_rr') or 0
            ) or None
            avg_brake_temp = _avg4(
                tel.get('avg_brake_temp_fl') or 0, tel.get('avg_brake_temp_fr') or 0,
                tel.get('avg_brake_temp_rl') or 0, tel.get('avg_brake_temp_rr') or 0
            )
            max_brake_temp = max(
                tel.get('max_brake_temp_fl') or 0, tel.get('max_brake_temp_fr') or 0,
                tel.get('max_brake_temp_rl') or 0, tel.get('max_brake_temp_rr') or 0
            ) or None
            tire_wear_delta = _r(tel.get('max_tire_temp_delta'), 1)

            raw_rows.append({
                'id':            lap['id'],
                'lap_number':    display_lap_number,
                'lap_time':      round(lap['lap_time'], 3),
                'sector_1':      round(lap['sector_1_time'], 3) if lap.get('sector_1_time') else None,
                'sector_2':      round(lap['sector_2_time'], 3) if lap.get('sector_2_time') else None,
                'sector_3':      round(lap['sector_3_time'], 3) if lap.get('sector_3_time') else None,
                'max_speed':     round(tel.get('max_speed_tel') or lap.get('max_speed') or 0, 1),
                'avg_speed':     round(tel.get('avg_speed_tel') or lap.get('avg_speed') or 0, 1),
                'hard_brakes':   int(tel.get('hard_brakes') or 0),
                'off_track':     int(tel.get('off_track_events') or 0),
                'avg_throttle':  _r(tel.get('avg_throttle'), 2),
                'avg_brake':     _r(tel.get('avg_brake'), 2),
                'max_g_lat':     _r(tel.get('max_g_lat'), 2),
                'max_g_long':    _r(tel.get('max_g_long'), 2),
                'tire_temp_fl':  _r(tel.get('avg_tire_temp_fl'), 1),
                'tire_temp_fr':  _r(tel.get('avg_tire_temp_fr'), 1),
                'tire_temp_rl':  _r(tel.get('avg_tire_temp_rl'), 1),
                'tire_temp_rr':  _r(tel.get('avg_tire_temp_rr'), 1),
                'avg_tire_temp': avg_tire_temp,
                'max_tire_temp': _r(max_tire_temp, 1),
                'tire_wear_delta': tire_wear_delta,
                'tire_pres_fl':  _r(tel.get('avg_tire_pres_fl'), 2),
                'tire_pres_fr':  _r(tel.get('avg_tire_pres_fr'), 2),
                'tire_pres_rl':  _r(tel.get('avg_tire_pres_rl'), 2),
                'tire_pres_rr':  _r(tel.get('avg_tire_pres_rr'), 2),
                'brake_temp_fl': _r(tel.get('avg_brake_temp_fl'), 1),
                'brake_temp_fr': _r(tel.get('avg_brake_temp_fr'), 1),
                'brake_temp_rl': _r(tel.get('avg_brake_temp_rl'), 1),
                'brake_temp_rr': _r(tel.get('avg_brake_temp_rr'), 1),
                'avg_brake_temp': avg_brake_temp,
                'max_brake_temp': _r(max_brake_temp, 1),
                'is_valid':      bool(lap.get('is_valid', 1)),
                'is_best':       False,
                'score':         None,
            })

        # Composite score
        if raw_rows:
            times      = [r['lap_time'] for r in raw_rows]
            off_tracks = [r['off_track'] for r in raw_rows]
            wears      = [r['tire_wear_delta'] or 0 for r in raw_rows]
            brakes     = [r['hard_brakes'] for r in raw_rows]

            def _norm(vals):
                mn, mx = min(vals), max(vals)
                return [0.0 if mx == mn else (v - mn) / (mx - mn) for v in vals]

            n_time  = _norm(times)
            n_off   = _norm(off_tracks)
            n_wear  = _norm(wears)
            n_brake = _norm(brakes)

            best_idx, best_val = None, float('inf')
            for i, row in enumerate(raw_rows):
                score = 0.50*n_time[i] + 0.20*n_off[i] + 0.15*n_wear[i] + 0.15*n_brake[i]
                row['score'] = round(score * 100, 1)
                if score < best_val:
                    best_val = score
                    best_idx = i
            if best_idx is not None:
                raw_rows[best_idx]['is_best'] = True

        # Build race_pace_telemetry
        race_pace_telemetry = []
        for lap_row in raw_rows:
            orig_lap_id = lap_row.get('id')
            if not orig_lap_id:
                continue
            
            tel_pts = self.db.get_lap_telemetry(orig_lap_id)
            if not tel_pts:
                continue
            step = max(1, len(tel_pts) // 200)
            pts = [
                {'x': round(p.get('normalized_position', i / max(len(tel_pts), 1)), 4),
                 'y': round(p['speed'], 1)}
                for i, p in enumerate(tel_pts[::step])
            ]
            race_pace_telemetry.append({
                'label': f"V{lap_row['lap_number']} ({lap_row['lap_time']:.3f}s)",
                'lap_number': lap_row['lap_number'],
                'lap_time': lap_row['lap_time'],
                'is_valid': lap_row['is_valid'],
                'is_best': lap_row['is_best'],
                'data': pts,
            })

        return {
            'lap_comparison_table': raw_rows,
            'race_pace_telemetry': race_pace_telemetry,
        }

    def analyze_last_3_races(self, track_name: str, car_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the last 3 races on a specific track.
        Returns data formatted for charts and historical comparison.
        """
        # Get last 20 sessions to ensure we find enough valid races (>= 3 laps)
        raw_sessions = self.db.get_last_n_sessions_by_track(track_name, n=20)
        
        # Filter for sessions (min 1 lap)
        races = [s for s in raw_sessions if s['total_laps'] >= 1]
        
        # Take the last 3 races
        sessions = races[-3:] if len(races) > 3 else races
        
        if not sessions:
            return {
                'available': False,
                'message': "No hay carreras registradas en este circuito (min. 3 vueltas)."
            }
            
        # Format data for charts
        labels = []
        best_laps = []
        dates = []
        speed_comparison_data = []  # List of {label: str, data: [{x: pos, y: speed}]}
        race_pace_data = [] # New: Race Pace Comparison
        session_stats = [] # Initialize stats collection

        for session_idx, session in enumerate(sessions):
            # Format date: DD/MM/YYYY
            date_obj = datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S.%f') if isinstance(session['start_time'], str) else session['start_time']
            date_str = date_obj.strftime('%d/%m/%Y')
            
            labels.append(f"Sesión {session['id']} ({date_str})")
            dates.append(date_str)
            best_laps.append(session['best_lap_time'] if session['best_lap_time'] else 0)

            # Get session laps to calculate stats and race pace
            session_laps = self.db.get_session_laps(session['id'])
            
            # --- Race Pace Data Construction ---
            pace_points = []
            if session_laps:
                 # Sort by lap number
                sorted_laps = sorted(session_laps, key=lambda x: x['lap_number'])
                for lap in sorted_laps:
                   # Include all complete laps for pace chart
                   if lap['lap_time'] > 0: 
                       pace_points.append({
                           'x': lap['lap_number'] + 1, # 1-based index for display
                           'y': lap['lap_time']
                       })
            
            race_pace_data.append({
                'label': f"Sesión {date_str} (S{session['id']})",
                'data': pace_points,
                'session_id': session['id'],
                'color_idx': session_idx
            })

            # --- Extended Stats Logic ---
            avg_speed_session = 0
            off_track_count = 0
            valid_laps_count = 0
            
            if session_laps:
                valid_laps = [l for l in session_laps if l.get('is_valid', 1)]
                valid_laps_count = len(valid_laps)
                off_track_count = len(session_laps) - valid_laps_count
                
                # Calculate average speed across all valid laps (if available in lap data)
                speeds = [l['avg_speed'] for l in session_laps if l.get('avg_speed')]
                if speeds:
                    avg_speed_session = sum(speeds) / len(speeds)
            
            stat_entry = {
                'id': session['id'],
                'date': date_str,
                'avg_speed': round(avg_speed_session, 1),
                'off_tracks': off_track_count,
                'best_lap': session['best_lap_time'] if session['best_lap_time'] else 999999,
                'total_laps': session['total_laps']
            }
            session_stats.append(stat_entry)

            # Fetch telemetry for best lap if available
            try:
                if session_laps:
                    # Filter for valid laps with time > 0
                    valid_laps_for_telem = [l for l in session_laps if l['lap_time'] > 0 and l.get('is_valid', 1)]
                    
                    if not valid_laps_for_telem:
                        # Fallback to any complete lap
                        valid_laps_for_telem = [l for l in session_laps if l['lap_time'] > 0]
                        
                    if valid_laps_for_telem:
                        best_lap = min(valid_laps_for_telem, key=lambda x: x['lap_time'])
                        telemetry = self.db.get_lap_telemetry(best_lap['id'])
                        
                        if telemetry:
                            # Resample to 21 equidistant points (20 segments) based on distance
                            resampled = self._resample_telemetry_uniform(telemetry, num_points=21)
                            
                            points = []
                            for p in resampled:
                                points.append({
                                    'x': p['point_index'] + 1, # 1-based segment index
                                    'y': p['speed'],
                                    'meta': p # include other stats like gear/throttle
                                })
                            
                            speed_comparison_data.append({
                                'label': f"Sesión {date_str} (Best: {best_lap['lap_time']:.3f}s)",
                                'data': points,
                                'session_id': session['id'],
                                'color_idx': session_idx
                            })
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error fetching telemetry for session {session['id']}: {e}")

        # Determine Best Session (lowest valid best lap time)
        best_session = None
        if session_stats:
            # Sort by best lap time (ascending)
            sorted_stats = sorted([s for s in session_stats if s['best_lap'] < 999999], key=lambda x: x['best_lap'])
            if sorted_stats:
                best_session = sorted_stats[0]

        # --- Lap Comparison Table (all laps of best session, with telemetry stats) ---
        lap_comparison_table = []
        race_pace_telemetry = []  # Per-lap speed traces for the race pace chart
        if sessions:
            # Prefer sessions with a stored best_lap_time, but fallback to computing from laps
            def _get_session_best_lap(s):
                if s.get('best_lap_time') and s['best_lap_time'] > 0:
                    return s['best_lap_time']
                # Fallback: compute from laps
                laps_fallback = self.db.get_session_laps(s['id'])
                valid = [l['lap_time'] for l in laps_fallback if l['lap_time'] > 0]
                return min(valid) if valid else None

            sessions_with_best = [(s, _get_session_best_lap(s)) for s in sessions]
            sessions_with_best = [(s, t) for s, t in sessions_with_best if t is not None]

            if sessions_with_best:
                best_sess, _ = min(sessions_with_best, key=lambda x: x[1])
                best_sess_laps = self.db.get_session_laps(best_sess['id'])
                if best_sess_laps:
                    valid_laps = [l for l in best_sess_laps if l['lap_time'] > 0]
                    best_lap_time_in_session = min((l['lap_time'] for l in valid_laps), default=None)

                    raw_rows = []
                    # Sort by ID for chronological order
                    sorted_best_laps = sorted(best_sess_laps, key=lambda x: x['id'])
                    display_lap_number = 0
                    
                    for lap in sorted_best_laps:
                        if lap['lap_time'] <= 0:
                            continue
                        
                        display_lap_number += 1
                        tel = self.db.get_lap_telemetry_stats(lap['id'])

                        def _r(v, d=1): return round(v, d) if v else None
                        def _avg4(a,b,c,d): return round((a+b+c+d)/4, 1) if all(x for x in [a,b,c,d]) else None

                        avg_tire_temp = _avg4(
                            tel.get('avg_tire_temp_fl') or 0, tel.get('avg_tire_temp_fr') or 0,
                            tel.get('avg_tire_temp_rl') or 0, tel.get('avg_tire_temp_rr') or 0
                        )
                        max_tire_temp = max(
                            tel.get('max_tire_temp_fl') or 0, tel.get('max_tire_temp_fr') or 0,
                            tel.get('max_tire_temp_rl') or 0, tel.get('max_tire_temp_rr') or 0
                        ) or None
                        avg_brake_temp = _avg4(
                            tel.get('avg_brake_temp_fl') or 0, tel.get('avg_brake_temp_fr') or 0,
                            tel.get('avg_brake_temp_rl') or 0, tel.get('avg_brake_temp_rr') or 0
                        )
                        max_brake_temp = max(
                            tel.get('max_brake_temp_fl') or 0, tel.get('max_brake_temp_fr') or 0,
                            tel.get('max_brake_temp_rl') or 0, tel.get('max_brake_temp_rr') or 0
                        ) or None
                        tire_wear_delta = _r(tel.get('max_tire_temp_delta'), 1)

                        raw_rows.append({
                            'id':            lap['id'],  # Added for lookup
                            'lap_number':    display_lap_number, # Synthetic sequential number
                            'lap_time':      round(lap['lap_time'], 3),
                            'sector_1':      round(lap['sector_1_time'], 3) if lap.get('sector_1_time') else None,
                            'sector_2':      round(lap['sector_2_time'], 3) if lap.get('sector_2_time') else None,
                            'sector_3':      round(lap['sector_3_time'], 3) if lap.get('sector_3_time') else None,
                            'max_speed':     round(tel.get('max_speed_tel') or lap.get('max_speed') or 0, 1),
                            'avg_speed':     round(tel.get('avg_speed_tel') or lap.get('avg_speed') or 0, 1),
                            'hard_brakes':   int(tel.get('hard_brakes') or 0),
                            'off_track':     int(tel.get('off_track_events') or 0),
                            'max_g_lat':     round(tel.get('max_g_lat') or 0, 2),
                            'max_g_long':    round(tel.get('max_g_long') or 0, 2),
                            'avg_brake_pct': round((tel.get('avg_brake') or 0) * 100, 1),
                            'avg_throttle_pct': round((tel.get('avg_throttle') or 0) * 100, 1),
                            # Tire data
                            'avg_tire_temp': avg_tire_temp,
                            'max_tire_temp': _r(max_tire_temp, 1),
                            'tire_temp_fl':  _r(tel.get('avg_tire_temp_fl'), 1),
                            'tire_temp_fr':  _r(tel.get('avg_tire_temp_fr'), 1),
                            'tire_temp_rl':  _r(tel.get('avg_tire_temp_rl'), 1),
                            'tire_temp_rr':  _r(tel.get('avg_tire_temp_rr'), 1),
                            'tire_pres_fl':  _r(tel.get('avg_tire_pres_fl'), 1),
                            'tire_pres_fr':  _r(tel.get('avg_tire_pres_fr'), 1),
                            'tire_pres_rl':  _r(tel.get('avg_tire_pres_rl'), 1),
                            'tire_pres_rr':  _r(tel.get('avg_tire_pres_rr'), 1),
                            'tire_wear_delta': tire_wear_delta,  # °C spread = wear proxy
                            # Brake data
                            'avg_brake_temp': avg_brake_temp,
                            'max_brake_temp': _r(max_brake_temp, 1),
                            'brake_temp_fl': _r(tel.get('avg_brake_temp_fl'), 1),
                            'brake_temp_fr': _r(tel.get('avg_brake_temp_fr'), 1),
                            'brake_temp_rl': _r(tel.get('avg_brake_temp_rl'), 1),
                            'brake_temp_rr': _r(tel.get('avg_brake_temp_rr'), 1),
                            'is_valid':      bool(lap.get('is_valid', 1)),
                            'is_best':       False,  # filled below after scoring
                            'score':         None,
                        })

                    # --- Composite Lap Score (lower = better) ---
                    # Weights: time 50%, off-track 20%, tire wear 15%, hard brakes 15%
                    if raw_rows:
                        times      = [r['lap_time'] for r in raw_rows]
                        off_tracks = [r['off_track'] for r in raw_rows]
                        wears      = [r['tire_wear_delta'] or 0 for r in raw_rows]
                        brakes     = [r['hard_brakes'] for r in raw_rows]

                        def _norm(vals):
                            mn, mx = min(vals), max(vals)
                            return [0.0 if mx == mn else (v - mn) / (mx - mn) for v in vals]

                        n_time  = _norm(times)
                        n_off   = _norm(off_tracks)
                        n_wear  = _norm(wears)
                        n_brake = _norm(brakes)

                        best_score_idx = None
                        best_score_val = float('inf')
                        for i, row in enumerate(raw_rows):
                            score = (0.50 * n_time[i] + 0.20 * n_off[i] +
                                     0.15 * n_wear[i] + 0.15 * n_brake[i])
                            row['score'] = round(score * 100, 1)  # 0-100, lower = better
                            if score < best_score_val:
                                best_score_val = score
                                best_score_idx = i

                        if best_score_idx is not None:
                            raw_rows[best_score_idx]['is_best'] = True

                    lap_comparison_table = raw_rows

                    # --- Race Pace Telemetry: per-lap speed traces for the chart ---
                    for lap_row in lap_comparison_table:
                        # Find the original lap using ID
                        orig_lap_id = lap_row.get('id')
                        if not orig_lap_id:
                            continue
                        
                        tel_pts = self.db.get_lap_telemetry(orig_lap_id)
                        if not tel_pts:
                            continue
                        # Downsample to 200 points
                        step = max(1, len(tel_pts) // 200)
                        pts = [
                            {'x': round(p.get('normalized_position', i / max(len(tel_pts), 1)), 4),
                             'y': round(p['speed'], 1)}
                            for i, p in enumerate(tel_pts[::step])
                        ]
                        race_pace_telemetry.append({
                            'label': f"V{lap_row['lap_number']} ({lap_row['lap_time']:.3f}s)",
                            'lap_number': lap_row['lap_number'],
                            'lap_time': lap_row['lap_time'],
                            'is_valid': lap_row['is_valid'],
                            'is_best': lap_row['is_best'],
                            'data': pts,
                        })

        race_comparison_table = []
        if sessions:
            raw_sess_rows = []
            for session in sessions:
                tel = self.db.get_session_telemetry_stats(session['id'])
                sess_laps = self.db.get_session_laps(session['id'])
                valid_laps_count = sum(1 for l in sess_laps if l.get('is_valid', 1) and l['lap_time'] > 0)
                try:
                    date_obj = datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S.%f') if isinstance(session['start_time'], str) else session['start_time']
                    date_str = date_obj.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    date_str = str(session['start_time'])

                def _r(v, d=1): return round(v, d) if v else None
                def _avg4s(a,b,c,d): return round((a+b+c+d)/4, 1) if all(x for x in [a,b,c,d]) else None

                avg_tire_temp = _avg4s(
                    tel.get('avg_tire_temp_fl') or 0, tel.get('avg_tire_temp_fr') or 0,
                    tel.get('avg_tire_temp_rl') or 0, tel.get('avg_tire_temp_rr') or 0
                )
                max_tire_temp = max(
                    tel.get('max_tire_temp_fl') or 0, tel.get('max_tire_temp_fr') or 0,
                    tel.get('max_tire_temp_rl') or 0, tel.get('max_tire_temp_rr') or 0
                ) or None
                avg_brake_temp = _avg4s(
                    tel.get('avg_brake_temp_fl') or 0, tel.get('avg_brake_temp_fr') or 0,
                    tel.get('avg_brake_temp_rl') or 0, tel.get('avg_brake_temp_rr') or 0
                )
                max_brake_temp = max(
                    tel.get('max_brake_temp_fl') or 0, tel.get('max_brake_temp_fr') or 0,
                    tel.get('max_brake_temp_rl') or 0, tel.get('max_brake_temp_rr') or 0
                ) or None

                raw_sess_rows.append({
                    'session_id':    session['id'],
                    'date':          date_str,
                    'car':           session.get('car_name', ''),
                    'total_laps':    session.get('total_laps', 0),
                    'valid_laps':    valid_laps_count,
                    'best_lap':      round(session['best_lap_time'], 3) if session.get('best_lap_time') else None,
                    'max_speed':     round(tel.get('max_speed_tel') or 0, 1),
                    'avg_speed':     round(tel.get('avg_speed_tel') or 0, 1),
                    'hard_brakes':   int(tel.get('hard_brakes') or 0),
                    'off_track':     int(tel.get('off_track_events') or 0),
                    'max_g_lat':     round(tel.get('max_g_lat') or 0, 2),
                    'max_g_long':    round(tel.get('max_g_long') or 0, 2),
                    # Tire data
                    'avg_tire_temp': avg_tire_temp,
                    'max_tire_temp': _r(max_tire_temp, 1),
                    'tire_wear_delta': _r(tel.get('max_tire_temp_delta'), 1),
                    'avg_brake_temp': avg_brake_temp,
                    'max_brake_temp': _r(max_brake_temp, 1),
                    'avg_tire_pres_fl': _r(tel.get('avg_tire_pres_fl'), 1),
                    'avg_tire_pres_fr': _r(tel.get('avg_tire_pres_fr'), 1),
                    'avg_tire_pres_rl': _r(tel.get('avg_tire_pres_rl'), 1),
                    'avg_tire_pres_rr': _r(tel.get('avg_tire_pres_rr'), 1),
                    'is_best': False,
                    'score': None,
                })

            # --- Composite Session Score (lower = better) ---
            # Weights: best_lap 50%, off-track 20%, tire wear 15%, hard brakes 15%
            if raw_sess_rows:
                best_laps_s  = [r['best_lap'] or 999 for r in raw_sess_rows]
                off_tracks_s = [r['off_track'] for r in raw_sess_rows]
                wears_s      = [r['tire_wear_delta'] or 0 for r in raw_sess_rows]
                brakes_s     = [r['hard_brakes'] for r in raw_sess_rows]

                def _norm_s(vals):
                    mn, mx = min(vals), max(vals)
                    return [0.0 if mx == mn else (v - mn) / (mx - mn) for v in vals]

                n_time_s  = _norm_s(best_laps_s)
                n_off_s   = _norm_s(off_tracks_s)
                n_wear_s  = _norm_s(wears_s)
                n_brake_s = _norm_s(brakes_s)

                best_score_idx_s = None
                best_score_val_s = float('inf')
                for i, row in enumerate(raw_sess_rows):
                    score = (0.50 * n_time_s[i] + 0.20 * n_off_s[i] +
                             0.15 * n_wear_s[i] + 0.15 * n_brake_s[i])
                    row['score'] = round(score * 100, 1)
                    if score < best_score_val_s:
                        best_score_val_s = score
                        best_score_idx_s = i

                if best_score_idx_s is not None:
                    raw_sess_rows[best_score_idx_s]['is_best'] = True

            race_comparison_table = raw_sess_rows

        # Derive best_session_laps for the bar chart (used by renderRacePaceChart)
        best_session_laps = [
            {
                'label': f"Vuelta {l['lap_number']} ({l['lap_time']:.3f}s)",
                'lap_number': l['lap_number'],
                'lap_time': l['lap_time'],
                'is_valid': l['is_valid'],
            }
            for l in lap_comparison_table
        ]

        # ── Reduce speed_comparison to exactly 2 lines ──────────────────────
        # Entry in speed_comparison_data are in the same order as `sessions`
        # (chronological / as provided by the DB query).
        # We want: 1) Session with best overall lap time, 2) Most recent session.
        if len(speed_comparison_data) > 1:
            # Find index of best session by best_lap_time
            best_idx = None
            best_time = float('inf')
            for idx, entry in enumerate(speed_comparison_data):
                # Match entry to session by session_id
                sid = entry.get('session_id')
                matching_stat = next((s for s in session_stats if s['id'] == sid), None)
                if matching_stat and matching_stat.get('best_lap', 999999) < best_time:
                    best_time = matching_stat['best_lap']
                    best_idx = idx

            # Last session is always the last entry (latest in time)
            last_idx = len(speed_comparison_data) - 1

            two_line_comparison = []
            if best_idx is not None:
                entry = speed_comparison_data[best_idx].copy()
                entry['label'] = f"🏆 Mejor Carrera ({entry['label']})"
                two_line_comparison.append(entry)
            if last_idx != best_idx:
                entry = speed_comparison_data[last_idx].copy()
                entry['label'] = f"🔄 Última Carrera ({entry['label']})"
                two_line_comparison.append(entry)

            speed_comparison_data = two_line_comparison
        elif len(speed_comparison_data) == 1:
            speed_comparison_data[0]['label'] = f"🏆 Mejor/Última Carrera ({speed_comparison_data[0]['label']})"

        return {
            'available': True,
            'track_name': track_name,
            'sessions_count': len(sessions),
            'labels': labels,
            'dates': dates,
            'best_laps': best_laps,
            'raw_data': sessions,
            'speed_comparison': speed_comparison_data,
            'race_pace_data': race_pace_data,
            'session_stats': session_stats,
            'best_session': best_session,
            'best_session_laps': best_session_laps,
            'lap_comparison_table': lap_comparison_table,
            'race_comparison_table': race_comparison_table,
            'race_pace_telemetry': race_pace_telemetry,
        }


    def _extract_visual_route_from_image(self, track_name: str, n_points: int = 20, start_world_pos: Tuple[float, float] = None, map_params: Dict = None) -> List[List[float]]:
        """
        Extracts N equidistant normalized coordinates [x, y] from the track map image using OpenCV.
        Syncs index 0 to start_world_pos if provided.
        """
        try:
            import cv2
            import numpy as np
            
            # Locate image
            clean_name = track_name.replace('@', '_')
            project_root = Path(__file__).parent.parent.parent.parent
            img_path = project_root / "frontend" / "assets" / "tracks" / f"{clean_name}.png"
            
            if not img_path.exists():
                return []

            # Load
            img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
            if img is None: return []

            # Extract Mask
            if img.shape[2] == 4:
                # Use Alpha if present and not fully opaque
                _, _, _, a = cv2.split(img)
                if cv2.countNonZero(a) < (a.size * 0.99): # If not fully opaque square
                    _, mask = cv2.threshold(a, 10, 255, cv2.THRESH_BINARY)
                else:
                    # Fallback to color detection if alpha is useless (solid bg)
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
                    
                    # Detect RED lines (Hue 0-10 and 160-180)
                    # Adjust limits based on "dark red" observation
                    lower_red1 = np.array([0, 50, 50])
                    upper_red1 = np.array([10, 255, 255])
                    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                    
                    lower_red2 = np.array([160, 50, 50])
                    upper_red2 = np.array([180, 255, 255])
                    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                    
                    mask = cv2.add(mask1, mask2)
            else:
                # RGB Image - Detect RED
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                lower_red1 = np.array([0, 50, 50])
                upper_red1 = np.array([10, 255, 255])
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                
                lower_red2 = np.array([160, 50, 50])
                upper_red2 = np.array([180, 255, 255])
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                
                mask = cv2.add(mask1, mask2)

            # Morphology to clean noise
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Find Contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not contours: return []
            
            cnt = max(contours, key=cv2.contourArea)
            points = cnt.reshape(-1, 2) # Raw points (px)
            
            # 1. Reverse direction (Anti-Clockwise preference from User)
            # Doing this BEFORE rolling to maintain flow direction
            points = points[::-1]

            # 2. Sync Start Point if params available
            start_shift = 0
            if start_world_pos and map_params:
                try:
                    # Project World -> Pixel using Map Params
                    # Standard: Pixel = (World + Offset) / Scale
                    scale = float(map_params.get('SCALE_FACTOR', 1))
                    off_x = float(map_params.get('X_OFFSET', 0))
                    off_z = float(map_params.get('Z_OFFSET', 0))
                    
                    if scale != 0:
                        start_px = (start_world_pos[0] + off_x) / scale
                        start_py = (start_world_pos[1] + off_z) / scale
                        
                        # Find closest point on contour
                        diffs = points - [start_px, start_py]
                        dists_sq = np.sum(diffs**2, axis=1)
                        best_idx = np.argmin(dists_sq)
                        
                        start_shift = best_idx
                        # logger.info(f"Syncing visual map: Start World({start_world_pos}) -> Px({start_px:.1f},{start_py:.1f}) -> ContourIdx {best_idx}")
                except Exception as e:
                    logger.warning(f"Map sync error: {e}")

            # Roll points so Start is at Index 0
            if start_shift != 0:
                points = np.roll(points, -start_shift, axis=0)

            # 3. Resample equidistant points
            # Close the loop for distance calc
            points_closed = np.vstack([points, points[0]])
            dists = np.sqrt(np.sum(np.diff(points_closed, axis=0)**2, axis=1))
            cum_dist = np.insert(np.cumsum(dists), 0, 0)
            total_len = cum_dist[-1]
            
            visual_points = []
            step = total_len / n_points 
            h, w = img.shape[:2]
            
            for i in range(n_points):
                target_d = (i * step) % total_len
                idx = np.searchsorted(cum_dist, target_d)
                
                if idx == 0:
                    pt = points[0]
                elif idx >= len(cum_dist):
                    pt = points[-1]
                else:
                    d_prev = cum_dist[idx-1]
                    d_next = cum_dist[idx]
                    p_prev = points[idx-1]
                    p_next = points[idx]
                    
                    if d_next == d_prev:
                        pt = p_prev
                    else:
                        ratio = (target_d - d_prev) / (d_next - d_prev)
                        pt = p_prev + (p_next - p_prev) * ratio
                
                nx = round(pt[0] / w, 5)
                ny = round(pt[1] / h, 5)
                visual_points.append([nx, ny])
                
            return visual_points

        except Exception as e:
            logger.error(f"Error extracting visual route: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # ANNOTATED MAP ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────
    def analyze_annotated_map_by_track(self, track_name: str) -> Dict[str, Any]:
        """
        For each session on the given track build an annotated map entry.
        Returns:
          {
            available: bool,
            track_map_image: str | None,  # base64 PNG - same for all sessions
            sessions: [
              {
                session_id, date, total_laps, best_lap_time, car_name,
                track_layout: { positions: [[normX, normZ], ...], speeds: [...],
                                bounds: {min_x, max_x, min_z, max_z} },
                sections: [
                  {
                    section_id, type, direction,
                    start_idx, end_idx,
                    mid_norm: [normX, normZ],   # canvas position for the glob
                    avg_speed, max_speed, min_speed,
                    entry_speed, exit_speed,
                    max_g_lat, avg_throttle_pct, max_brake_pct,
                    time_sec
                  }, ...
                ]
              }, ...
            ]
          }
        """
        # Fetch the last 3 sessions for this track (best lap of each)
        raw_sessions = self.db.get_last_n_sessions_by_track(track_name, n=3)
        if not raw_sessions:
            return {'available': False, 'message': 'No hay sesiones registradas en este circuito.'}

        # Load the track map image once (same for all sessions)
        track_map_image = None
        try:
            track_map_image = self._load_track_map(track_name)
        except Exception as e:
            logger.warning(f'Could not load track map for {track_name}: {e}')

        sessions_data = []

        for session in raw_sessions:
            session_id = session['id']
            try:
                # Format date
                try:
                    date_obj = (
                        datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S.%f')
                        if isinstance(session['start_time'], str)
                        else session['start_time']
                    )
                    date_str = date_obj.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    date_str = str(session['start_time'])

                # Get all completed laps for this session
                session_laps = self.db.get_session_laps(session_id)
                completed = [l for l in (session_laps or []) if l['lap_time'] > 0]
                if not completed:
                    continue

                # Pick the best (fastest valid) lap
                valid = [l for l in completed if l.get('is_valid', 1)] or completed
                best_lap = min(valid, key=lambda l: l['lap_time'])

                # Get full telemetry for that lap
                telemetry = self.db.get_lap_telemetry(best_lap['id'])
                if not telemetry or len(telemetry) < 20:
                    continue

                # ── Track layout (normalized positions + speeds) ─────────────
                track_layout = self._extract_track_layout(telemetry)

                # ── Map Parameters & Normalization ───────────────────────────
                map_params = None
                
                # 1. Try Local Assets (frontend/assets/tracks/[track].ini)
                # This matches the images copied by import_maps.py
                try:
                    # Construct local path relative to backend/domain/analysis
                    # Path: ../../../frontend/assets/tracks/{track_name}.ini
                    # Or absolute path based on project root
                    project_root = Path(__file__).parent.parent.parent.parent
                    
                    # Normalize track name (track@layout -> track_layout) for file lookup
                    clean_track_name = track_name.replace('@', '_')
                    local_ini_path = project_root / "frontend" / "assets" / "tracks" / f"{clean_track_name}.ini"
                    
                    if local_ini_path.exists():
                        import configparser
                        config = configparser.ConfigParser()
                        config.read(local_ini_path)
                        if 'PARAMETERS' in config:
                            map_params = dict(config['PARAMETERS'])
                            logger.info(f"Loaded local map parameters for {track_name}: {map_params}")
                except Exception as e:
                    logger.warning(f"Error loading local map params: {e}")

                # 2. Fallback to Game Folder (MapAnalyzer)
                if not map_params and self.map_analyzer:
                    if track_name not in self.map_analyzer.track_data:
                        self.map_analyzer.load_track_data(track_name)
                    map_params = self.map_analyzer.track_data.get(track_name, {}).get('map_params')
                
                # Define _norm_pt based on map.ini or dynamic bounds
                if map_params:
                    # Parse map.ini (standard AC format)
                    # Coordinates in map.ini are usually:
                    # X_OFFSET, Z_OFFSET: World coordinates of the map's top-left corner (or reference)
                    # SCALE_FACTOR: Meters per pixel (usually)
                    # WIDTH, HEIGHT: Image dimensions
                    
                    try:
                        off_x = float(map_params.get('X_OFFSET', 0))
                        off_z = float(map_params.get('Z_OFFSET', 0))
                        scale = float(map_params.get('SCALE_FACTOR', 1))
                        width = float(map_params.get('WIDTH', 1000))
                        height = float(map_params.get('HEIGHT', 1000))
                        margin = float(map_params.get('MARGIN', 0))
                        
                        # Note: Formula varies by tool. 
                        # Common: pixel = (world - offset) / scale  (if scale is meters/pixel)
                        # or:     pixel = (world + offset) * scale  (if scale is pixels/meter)
                        
                        # MapAnalyzer/TrackMapper standard: pixel = (world - offset) / scale (Assuming meters/pixel scale type)
                        
                        def _norm_pt(px, pz):
                            u = (px + off_x) / scale
                            v = (pz + off_z) / scale
                            
                            # Normalize [0,1]
                            nu = round(u / width, 5) if width else 0
                            nv = round(v / height, 5) if height else 0
                            return [nu, nv]

                        # DEBUG LOG
                        if len(telemetry) > 0:
                            p0 = telemetry[0]
                            n0 = _norm_pt(p0.get('position_x', 0), p0.get('position_z', 0))
                            logger.info(f"DEBUG MAP {track_name}: P0({p0.get('position_x')},{p0.get('position_z')}) -> Norm({n0}) with P(W={width},H={height},OffX={off_x},OffZ={off_z},S={scale})")

                    except Exception:
                        # Fallback if params are bad
                        map_params = None

                if not map_params:
                    # Fallback to dynamic bounds (Heatmap fills canvas)
                    bounds = track_layout.get('bounds', {})
                    min_x = bounds.get('min_x', 0)
                    max_x = bounds.get('max_x', 1)
                    min_z = bounds.get('min_z', 0)
                    max_z = bounds.get('max_z', 1)
                    x_range = max_x - min_x or 1
                    z_range = max_z - min_z or 1

                    def _norm_pt(px, pz):
                        return [
                            round((px - min_x) / x_range, 5),
                            round((pz - min_z) / z_range, 5),
                        ]

                # ── Resample & Recalculate Positions ──────────────────────────
                # We must update track_layout['positions'] to match the new coordinate system (Image or Dynamic)
                new_positions = []
                for p in telemetry:
                     # Some telemetry points might lack x/z if incomplete, but usually fine
                     nx, ny = _norm_pt(p.get('position_x', 0), p.get('position_z', 0))
                     new_positions.append([nx, ny])
                
                track_layout['positions'] = new_positions

                # ── 20 equidistant sample points from TELEMETRY (data) ────────────────────────
                resampled_telemetry = self._resample_telemetry_uniform(telemetry, num_points=20)
                
                # ── 20 equidistant sample points from IMAGE (visual) ──────────────────────────
                # Attempt to sync start point with telemetry
                start_world_pos = None
                for pt in telemetry:
                    # Find first valid point (sometimes first few are empty)
                    if 'position_x' in pt and 'position_z' in pt and pt.get('speed', 0) > 1:
                        start_world_pos = (pt['position_x'], pt['position_z'])
                        break
                
                # This ensures points follow the visual line perfectly and start at the car's start pos
                visual_route = self._extract_visual_route_from_image(track_name, n_points=20, start_world_pos=start_world_pos, map_params=map_params)
                
                # Use visual route if available, otherwise fallback to telemetry positions
                norm_positions_src = visual_route if visual_route else track_layout.get('positions', [])

                points_out = []

                for i, pt in enumerate(resampled_telemetry):
                    # If we have visual route, map 1:1 by index (assuming both are 20 points uniform)
                    if visual_route and i < len(visual_route):
                        mid_norm = visual_route[i]
                    else:
                        # Fallback: Linear interpolation from whatever positions available
                        target_n = pt['normalized_position']
                        
                        # Map 0..1 to index in full telemetry
                        idx_float = target_n * (len(norm_positions_src) - 1)
                        if len(norm_positions_src) > 0:
                            idx_floor = int(idx_float)
                            idx_ceil = min(idx_floor + 1, len(norm_positions_src) - 1)
                            rem = idx_float - idx_floor
                            
                            p1 = norm_positions_src[idx_floor]
                            p2 = norm_positions_src[idx_ceil]
                            
                            mid_norm = [
                                p1[0] + (p2[0] - p1[0]) * rem,
                                p1[1] + (p2[1] - p1[1]) * rem
                            ]
                        else:
                            mid_norm = [0.5, 0.5] # Fail safe


                    points_out.append({
                        'point_num':     i + 1,
                        'label':         f'Seg {i + 1}',
                        'mid_norm':      mid_norm,
                        'norm_pos':      round(pt['normalized_position'], 3),
                        'speed':         round(pt['speed'], 1),
                        'brake_pct':     round(pt['brake'] * 100, 1),
                        'throttle_pct':  round(pt['throttle'] * 100, 1),
                        'is_braking':    pt['brake'] > 0.1,
                        'g_lat':         round(pt['g_force_lat'], 2),
                        # User Request: Show specific point validity (on-track vs off-track)
                        # Usually > 2 tires out means off-track.
                        'lap_is_valid':  pt.get('n_tires_out', 0) <= 2,
                        'gear':          pt['gear'],
                        'rpm':           int(pt['rpm'])
                    })

                sessions_data.append({
                    'session_id':    session_id,
                    'date':          date_str,
                    'total_laps':    session.get('total_laps', len(completed)),
                    'best_lap_time': round(best_lap['lap_time'], 3),
                    'car_name':      session.get('car_name', ''),
                    'track_layout':  track_layout,
                    'sections':      points_out,   # kept as 'sections' for frontend compat
                    'points':        points_out,
                })


            except Exception as ex:
                logger.error(f'annotated_map: error processing session {session_id}: {ex}')
                continue

        return {
            'available':        True,
            'track_name':       track_name,
            'sessions_count':   len(sessions_data),
            'track_map_image':  track_map_image,
            'sessions':         sessions_data,
        }

    def _resample_telemetry_uniform(self, telemetry: List[Dict], num_points: int = 21) -> List[Dict]:
        """
        Resample telemetry into N points equidistant by normalized track position (0.0 to 1.0).
        21 points = 20 segments (0%, 5%, ..., 100%).
        Uses simple linear interpolation for continuous values.
        """
        if not telemetry:
            return []
            
        # Filter for points with normalized_position
        valid_points = [p for p in telemetry if p.get('normalized_position') is not None]
        if not valid_points:
            # Fallback: Create normalized position from index
            total = len(telemetry)
            for i, p in enumerate(telemetry):
                p['normalized_position'] = i / max(total - 1, 1)
            valid_points = telemetry

        # Ensure sorted by position
        valid_points.sort(key=lambda p: float(p['normalized_position']))
        
        # Source arrays
        src_pos = np.array([float(p['normalized_position']) for p in valid_points])
        
        # Target positions (0.05, 0.10 ... 1.0)
        # We want 20 segments. 
        # Option A: Centers (0.025, 0.075...)
        # Option B: Edges (0.05, 0.10...)
        # User said "Divide into 20 equal segments". Usually means end of segment or center.
        # Let's use 20 points evenly spaced from 0 to 1 inclusively? No, that gives 19 segments.
        # Let's use np.linspace(0, 1, num_points+1) maybe?
        # Standard: 20 points representing the STATE at 20 locations.
        # Let's use linspace(0.0, 1.0, num_points)
        target_pos = np.linspace(0.0, 1.0, num_points)
        
        # Fields to interpolate
        fields = ['speed', 'rpm', 'brake', 'throttle', 'g_force_lat', 'g_force_long', 'steering']
        
        interp_results = {}
        for f in fields:
            src_vals = np.array([float(p.get(f, 0)) for p in valid_points])
            interp_results[f] = np.interp(target_pos, src_pos, src_vals)
            
        # Gears & Tires (Nearest Neighbor)
        src_gears = np.array([int(p.get('gear', 0)) for p in valid_points])
        src_tires = np.array([int(p.get('n_tires_out', 0)) for p in valid_points])
        
        # Find indices
        idx = np.searchsorted(src_pos, target_pos)
        idx = np.clip(idx, 0, len(src_pos)-1)
        
        interp_gears = src_gears[idx]
        interp_tires = src_tires[idx]
        
        result = []
        for i in range(num_points):
            row = {
                'point_index': i,
                'normalized_position': float(target_pos[i]),
                'gear': int(interp_gears[i]),
                'n_tires_out': int(interp_tires[i])
            }
            for f in fields:
                row[f] = float(interp_results[f][i])
            result.append(row)
            
        return result

    # ─────────────────────────────────────────────────────────────────────────
    def analyze_last_3_laps(self, session_id: int) -> Dict[str, Any]:

        """
        Analyze laps of a specific session.
        Returns exactly 2 datasets for the speed comparison chart:
          1. Best lap (lowest lap_time among valid laps) - persistent reference
          2. Last lap (most recently completed lap)
        """
        all_laps = self.db.get_last_n_laps_of_session(session_id, n=100)

        # Keep only completed laps
        completed = [l for l in all_laps if l['lap_time'] > 0]

        if not completed:
            return {
                'available': False,
                'message': "No hay vueltas válidas registradas."
            }

        # ── Best lap ──────────────────────────────────────────────────────────
        valid_for_best = [l for l in completed if l.get('is_valid', 1)]
        if not valid_for_best:
            valid_for_best = completed  # fallback: any complete lap
        best_lap = min(valid_for_best, key=lambda x: x['lap_time'])

        # ── Last lap ──────────────────────────────────────────────────────────
        # Sort by DB id to find chronological last
        last_lap = max(completed, key=lambda x: x['id'])

        # ── Stats for consistency (keep all completed laps) ──────────────────
        times = [l['lap_time'] for l in completed]
        import numpy as np
        if len(times) > 1:
            std_dev = float(np.std(times))
            avg_time = float(np.mean(times))
            consistency_score = (1 - (std_dev / avg_time)) * 100 if avg_time > 0 else 0
        else:
            std_dev = 0.0
            avg_time = times[0] if times else 0.0
            consistency_score = 0.0

        # ── Prepare speed comparison data ─────────────────────────────────────
        speed_comparison_data = []
        laps_to_compare = [best_lap, last_lap]

        for i, lap in enumerate(laps_to_compare):
            try:
                telemetry = self.db.get_lap_telemetry(lap['id'])
                if telemetry:
                    # Downsample to ~500 points
                    target_points = 500
                    step = max(1, len(telemetry) // target_points)
                    downsampled_telemetry = telemetry[::step]

                    # Check if normalized_position is valid (varies across the lap)
                    # Handle None values safely (sqlite can return None for REAL columns)
                    norm_pos_values = []
                    for p in downsampled_telemetry:
                        val = p.get('normalized_position')
                        norm_pos_values.append(float(val) if val is not None else 0.0)
                        
                    has_valid_norm_pos = False
                    if norm_pos_values:
                        has_valid_norm_pos = (max(norm_pos_values) - min(norm_pos_values)) > 0.01

                    points = []
                    total_points = len(downsampled_telemetry)
                    
                    for idx, point in enumerate(downsampled_telemetry):
                        # Use normalized_position if valid, otherwise fallback to index ratio
                        if has_valid_norm_pos:
                            val = point.get('normalized_position')
                            x_val = float(val) if val is not None else 0.0
                        else:
                            x_val = idx / max(total_points - 1, 1)
                            
                        points.append({
                            'x': round(x_val, 4),
                            'y': round(point['speed'], 1)
                        })

                    label_prefix = "Mejor Vuelta" if lap['id'] == best_lap['id'] else "Última Vuelta"
                    speed_comparison_data.append({
                        'label': f"{label_prefix} {lap['lap_number']} ({lap['lap_time']:.3f}s)",
                        'data': points,
                        'lap_id': lap['id'],
                        'color_idx': i # 0 for best, 1 for last
                    })
            except Exception as e:
                logger.error(f"Error fetching telemetry for lap {lap['id']}: {e}")

        return {
            'available': True,
            'laps_count': len(completed),
            'best_lap_id': best_lap['id'],
            'best_lap_time': round(best_lap['lap_time'], 3),
            'last_lap_time': round(last_lap['lap_time'], 3),
            'consistency_score': round(consistency_score, 1),
            'std_dev': round(std_dev, 3),
            'avg_lap_time': round(avg_time, 3),
            'speed_comparison': speed_comparison_data,
            'best_lap_data': best_lap,
            'last_lap_data': last_lap,
            # Data for Last Laps Chart (Consistency)
            'times': [round(l['lap_time'], 3) for l in sorted(completed, key=lambda x: x['lap_number'])],
            'labels': [f"V{l['lap_number']}" for l in sorted(completed, key=lambda x: x['lap_number'])],
            # Data for Lap Analysis cards (Last 3)
            'raw_data': completed[-3:] if len(completed) >= 3 else completed
        }
