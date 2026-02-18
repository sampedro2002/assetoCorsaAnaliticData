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
from backend.core.config import ANALYSIS_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Analyzes telemetry data and generates recommendations"""
    
    def __init__(self, database: Database):
        """Initialize analyzer with database connection"""
        self.db = database
    
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
        
        # Detect track sections (straights and corners) using LAST LAP to show user errors
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
    
    def _analyze_track_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate performance metrics for each track section"""
        analyzed_sections = []
        
        for i, section in enumerate(sections):
            points = section['points']
            
            if not points:
                continue
            
            # Calculate metrics
            speeds = [p['speed'] for p in points]
            avg_speed = np.mean(speeds) if speeds else 0
            min_speed = min(speeds) if speeds else 0
            max_speed = max(speeds) if speeds else 0
            
            # Time spent in section
            time_in_section = points[-1]['timestamp'] - points[0]['timestamp'] if len(points) >= 2 else 0
            
            # G-forces
            g_lat = [abs(p.get('g_force_lat', 0)) for p in points]
            g_long = [abs(p.get('g_force_long', 0)) for p in points]
            avg_g_lat = np.mean(g_lat) if g_lat else 0
            avg_g_long = np.mean(g_long) if g_long else 0
            max_g_lat = max(g_lat) if g_lat else 0
            max_g_long = max(g_long) if g_long else 0
            
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
                'is_valid': is_valid,
                'recommendation': recommendation,
                'recommended_speed': recommended_speed
            })
        
        return analyzed_sections
    
    def _load_track_map(self, track_name: str) -> Optional[str]:
        """
        Load official track map from Assetto Corsa installation
        Returns base64 encoded PNG image or None if not found
        """
        try:
            # Clean track name (remove configuration suffix like @layout)
            clean_track_name = track_name.split('@')[0]
            
            # Get AC installation path from environment
            ac_install_path = os.getenv('AC_INSTALL_PATH', '')
            if not ac_install_path:
                logger.warning("AC_INSTALL_PATH not set in environment")
                return None
            
            # Construct path to track outline image
            # Path format: <AC_INSTALL>/content/tracks/<track_name>/ui/outline.png
            track_map_path = Path(ac_install_path) / "content" / "tracks" / clean_track_name / "ui" / "outline.png"
            
            logger.info(f"Searching for track map for '{track_name}' (cleaned: '{clean_track_name}') at {track_map_path}")
            
            if not track_map_path.exists():
                logger.warning(f"Track map not found at: {track_map_path}")
                return None
            
            # Read and encode image as base64
            with open(track_map_path, 'rb') as img_file:
                img_data = img_file.read()
                base64_encoded = base64.b64encode(img_data).decode('utf-8')
                logger.info(f"✓ Successfully loaded track map for {clean_track_name}")
                return base64_encoded
                

        except Exception as e:
            logger.error(f"Error loading track map: {e}")
            return None

    def analyze_last_3_races(self, track_name: str, car_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the last 3 races on a specific track.
        Returns data formatted for charts and historical comparison.
        """
        # Get last 20 sessions to ensure we find enough valid races (>= 3 laps)
        raw_sessions = self.db.get_last_n_sessions_by_track(track_name, n=20)
        
        # Filter for "Race" sessions (min 3 laps)
        races = [s for s in raw_sessions if s['total_laps'] >= 3]
        
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
                            # Downsample to ~500 points
                            target_points = 500
                            step = max(1, len(telemetry) // target_points)
                            downsampled_telemetry = telemetry[::step]
                            
                            points = []
                            for i, point in enumerate(downsampled_telemetry):
                                points.append({
                                    'x': i, 
                                    'y': point['speed']
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
            'best_session': best_session
        }

    def analyze_last_3_laps(self, session_id: int) -> Dict[str, Any]:
        """
        Analyze the last 3 laps of a specific session.
        Returns data for consistency analysis.
        """
        laps = self.db.get_last_n_laps_of_session(session_id, n=10)
        
        # Filter for completed laps (time > 0)
        laps = [l for l in laps if l['lap_time'] > 0]
        
        # Take last 3 completed laps
        laps = laps[:3]
        
        if not laps:
            return {
                'available': False,
                'message': "No hay vueltas válidas registradas."
            }
            
        labels = []
        times = []
        sector1 = []
        sector2 = []
        sector3 = []
        lap_stats = []

        valid_laps_for_best = [l for l in laps if l.get('is_valid', 1) and l['lap_time'] > 0]
        best_lap_time = min([l['lap_time'] for l in valid_laps_for_best]) if valid_laps_for_best else 0
        best_lap_id = min(valid_laps_for_best, key=lambda x: x['lap_time'])['id'] if valid_laps_for_best else None

        for lap in laps:
            labels.append(f"Vuelta {lap['lap_number']}")
            times.append(lap['lap_time'])
            
            # Additional stats per lap
            lap_stat = {
                'lap': lap['lap_number'],
                'time': lap['lap_time'],
                'avg_speed': lap.get('avg_speed', 0),
                'is_valid': lap.get('is_valid', 1),
                'is_best': lap['id'] == best_lap_id if best_lap_id else False
            }
            lap_stats.append(lap_stat)
            times.append(lap['lap_time'])
            sector1.append(lap['sector_1_time'] if lap['sector_1_time'] else 0)
            sector2.append(lap['sector_2_time'] if lap['sector_2_time'] else 0)
            sector3.append(lap['sector_3_time'] if lap['sector_3_time'] else 0)
            
        # Calculate consistency (Standard Deviation of times)
        import numpy as np
        if len(times) > 1:
            std_dev = float(np.std(times))
            avg_time = float(np.mean(times))
            consistency_score = (1 - (std_dev / avg_time)) * 100 if avg_time > 0 else 0
        else:
            std_dev = 0
            consistency_score = 100
            
        return {
            'available': True,
            'laps_count': len(laps),
            'labels': labels,
            'times': times,
            'sector1': sector1,
            'sector2': sector2,
            'sector3': sector3,
            'consistency_score': round(consistency_score, 1),
            'std_dev': round(std_dev, 3),
            'raw_data': laps,
            'lap_stats': lap_stats,
            'best_lap_id': best_lap_id,
            'best_lap_time': best_lap_time
        }
        
        # Add telemetry for speed comparison
        speed_data = []
        for i, lap in enumerate(laps):
            try:
                telemetry = self.db.get_lap_telemetry(lap['id'])
                if telemetry:
                    # Downsample to ~500 points
                    target_points = 500
                    step = max(1, len(telemetry) // target_points)
                    downsampled_telemetry = telemetry[::step]
                    
                    points = []
                    for idx, point in enumerate(downsampled_telemetry):
                        points.append({
                            'x': idx, 
                            'y': point['speed']
                        })
                    
                    speed_data.append({
                        'label': f"Vuelta {lap['lap_number']} ({lap['lap_time']:.3f}s)",
                        'data': points,
                        'lap_id': lap['id'],
                        'color_idx': i
                    })
            except Exception as e:
                logger.error(f"Error fetching telemetry for lap {lap['id']}: {e}")
                
        return {
            'available': True,
            'laps_count': len(laps),
            'labels': labels,
            'times': times,
            'sector1': sector1,
            'sector2': sector2,
            'sector3': sector3,
            'consistency_score': round(consistency_score, 1),
            'std_dev': round(std_dev, 3),
            'raw_data': laps,
            'lap_stats': lap_stats,
            'best_lap_id': best_lap_id,
            'best_lap_time': best_lap_time,
            'speed_comparison': speed_data
        }
