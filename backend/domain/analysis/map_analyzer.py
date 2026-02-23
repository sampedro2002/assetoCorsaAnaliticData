
import os
import cv2
import numpy as np
import logging
import configparser
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math

# Configure logging
logger = logging.getLogger(__name__)

class MapAnalyzer:
    """
    Analyzes the official Assetto Corsa track map (outline.png)
    to identify track sections (corners/straights) and map coordinates.
    """

    def __init__(self, ac_install_path: str):
        self.ac_install_path = Path(ac_install_path) if ac_install_path else None
        self.track_data = {}  # Cache for loaded tracks

    def load_track_data(self, track_name: str, track_layout: Optional[str] = None) -> bool:
        """
        Load track map image and configuration (map.ini)
        """
        if not self.ac_install_path or not self.ac_install_path.exists():
            logger.error("Assetto Corsa install path not found")
            return False

        # Handle track layouts (e.g., "ks_silverstone-gp" -> track="ks_silverstone", layout="gp")
        # But usually passing "ks_silverstone@gp" or similar
        
        # Clean track name and layout
        if '@' in track_name:
            track_base, layout = track_name.split('@')
        else:
            track_base = track_name
            layout = track_layout

        track_dir = self.ac_install_path / "content" / "tracks" / track_base
        
        # Path to map.png/outline.png and map.ini
        # If layout exists, check inside layout folder, otherwise fallback to base
        # Layouts usually have their own data/map.ini but map image might be shared or specific
        
        # Strategy:
        # 1. Check if layout folder exists inside track folder
        # 2. Look for map.png/outline.png and data/map.ini there
        
        map_image_path = None
        map_ini_path = None

        if layout:
            layout_dir = track_dir / layout
            if layout_dir.exists():
                # Check for map inside layout
                possible_maps = [layout_dir / "map.png", layout_dir / "outline.png"]
                # Also check ui folder
                possible_maps.extend([layout_dir / "ui" / "map.png", layout_dir / "ui" / "outline.png"])
                
                for p in possible_maps:
                    if p.exists():
                        map_image_path = p
                        break
                
                # Check for data/map.ini
                # Note: data folder implies data.acd is unpacked. If data.acd exists, we can't read map.ini easily without unpacking 
                # BUT, usually map.ini is also in the root of the layout or in the 'data' folder if present.
                # Actually, map.png is used by the app, but map.ini is needed for coordinates.
                # Standard map display apps look for map.ini in the track folder.
                
                possible_inis = [layout_dir / "data" / "map.ini", layout_dir / "map.ini"]
                for p in possible_inis:
                    if p.exists():
                        map_ini_path = p
                        break

        # Fallback to base track folder if not found in layout
        if not map_image_path:
             possible_maps = [
                 track_dir / "map.png", 
                 track_dir / "outline.png",
                 track_dir / "ui" / "map.png",
                 track_dir / "ui" / "outline.png"
             ]
             for p in possible_maps:
                if p.exists():
                    map_image_path = p
                    break
        
        if not map_ini_path:
             possible_inis = [track_dir / "data" / "map.ini", track_dir / "map.ini"]
             for p in possible_inis:
                if p.exists():
                    map_ini_path = p
                    break

        if not map_image_path or not map_image_path.exists():
            logger.warning(f"Map image not found for {track_name}")
            return False
            
        # map.ini is optional but needed for coordinate mapping. 
        # If missing, we can still analyze the shape but not map to world coordinates accurately.
        map_params = {}
        if map_ini_path and map_ini_path.exists():
            try:
                config = configparser.ConfigParser()
                config.read(map_ini_path)
                if 'PARAMETERS' in config:
                    map_params = dict(config['PARAMETERS'])
            except Exception as e:
                logger.error(f"Error reading map.ini: {e}")

        # Load image
        image = cv2.imread(str(map_image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            logger.error(f"Failed to load map image: {map_image_path}")
            return False

        # Store data
        self.track_data[track_name] = {
            'image': image,
            'image_path': str(map_image_path),
            'map_params': map_params
        }
        
        logger.info(f"Loaded track map for {track_name}. Image: {map_image_path}, Params: {bool(map_params)}")
        return True

    
    def analyze_map(self, track_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Analyze the loaded map to find corners and straights.
        Returns a list of reference points with type 'corner' or 'straight'.
        """
        if track_name not in self.track_data:
            if not self.load_track_data(track_name):
                return None
        
        data = self.track_data[track_name]
        image = data['image']
        params = data.get('map_params', {})
        
        # Preprocessing: Convert to binary
        if len(image.shape) > 2:
            if image.shape[2] == 4:
                _, _, _, alpha = cv2.split(image)
                _, binary = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)
            else:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        else:
            _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)

        # Finding contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if not contours:
            return None
            
        # Assume the largest contour is the track
        track_contour = max(contours, key=cv2.contourArea)
        
        # Smooth the contour to reduce pixelation noise
        # This is CRITICAL for curvature calculation
        # approximate standard polygon
        epsilon = 0.002 * cv2.arcLength(track_contour, True) # 0.2% length accuracy
        approx_curve = cv2.approxPolyDP(track_contour, epsilon, True)
        
        points = approx_curve[:, 0, :] # Shape (N, 2)
        n_points = len(points)
        
        if n_points < 10:
            return None
            
        # Calculate curvature at each vertex
        # Angle between (p(i-1) -> p(i)) and (p(i) -> p(i+1))
        
        reference_path = []
        
        for i in range(n_points):
            p_prev = points[(i - 1 + n_points) % n_points]
            p_curr = points[i]
            p_next = points[(i + 1) % n_points]
            
            # Vectors
            v1 = p_curr - p_prev
            v2 = p_next - p_curr
            
            # Calculate angle change (deviation from straight line)
            # Straight = 0 degrees deviation
            # 90 deg turn = 90 degrees deviation
            
            angle_deg = self._calculate_angle_deviation(v1, v2)
            
            # Map pixels to World Coordinates
            world_pos = self._map_to_world(p_curr[0], p_curr[1], params)
            
            # Simple thresholding: 
            # If deviation > threshold, it's part of a curve.
            # But "Straight" sections in a polygon approximation might still have 0 deviation 
            # even if the track is curving gently between widely spaced points? 
            # No, approxPolyDP keeps points where curvature changes.
            
            # Threshold: 5 degrees?
            is_turn = abs(angle_deg) > 5.0
            
            reference_path.append({
                'world_x': world_pos[0],
                'world_z': world_pos[1],
                'pixel_x': int(p_curr[0]),
                'pixel_y': int(p_curr[1]),
                'is_turn': is_turn,
                'angle_deviation': angle_deg
            })
            
        # Now, identifying "Sections" from point types is noisy.
        # We need to group them.
        # Algorithm:
        # 1. Expand "Turn" points to neighbors (smoothing)
        # 2. Group contiguous points
        
        # Determine types based on grouping
        # For now, let's just return the raw points and let the analyzer handle the complex grouping logic 
        # or implement a simple grouping here.
        
        # Let's clean up the 'is_turn' flags into sections
        track_sections = self._segment_path(reference_path)
        
        return track_sections

    def _calculate_angle_deviation(self, v1, v2):
        """
        Calculate the angle deviation between two vectors in degrees.
        0 means straight, 180 means U-turn.
        """
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0
            
        dot_product = np.dot(v1, v2)
        cos_angle = dot_product / (norm_v1 * norm_v2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        return np.degrees(angle_rad)

    def _map_to_world(self, u, v, params):
        """
        Convert image coordinates to world coordinates.
        Standard AC Map Parameters:
        X_OFFSET, Z_OFFSET, ROTATION, SCALE_FACTOR
        WIDTH, HEIGHT, MARGIN usually describe the map generation process, not the transform.
        
        Standard transform:
        World X = (Image_X + X_OFFSET) * SCALE_FACTOR
        World Z = (Image_Y + Z_OFFSET) * SCALE_FACTOR
        
        Wait, I need to check if OFFSET is in pixels or meters?
        Usually it is:
        Start World X = map_min_x
        Start World Z = map_min_z
        Map Size World = map_width_m, map_height_m
        
        Let's look for common implementations.
        Ideally, we find:
        X_OFFSET = World X at Map (0,0) (or Map Margin)
        SCALE_FACTOR = Meters per Pixel
        """
        scale = float(params.get('SCALE_FACTOR', 1.0))
        x_off = float(params.get('X_OFFSET', 0.0))
        z_off = float(params.get('Z_OFFSET', 0.0))
        
        # Assuming standard transformation:
        # World = (Pixel + Offset) * Scale ?? No that's weird.
        # Usually: World = (Pixel * Scale) + World_Offset
        
        x = (u * scale) + x_off
        z = (v * scale) + z_off
        
        return (x, z)
    
    def _segment_path(self, path_points):
        """
        Group points into 'straight' or 'corner' sections
        """
        if not path_points:
            return []
            
        sections = []
        current_type = 'corner' if path_points[0]['is_turn'] else 'straight'
        current_section_points = [path_points[0]]
        
        for i in range(1, len(path_points)):
            pt = path_points[i]
            pt_type = 'corner' if pt['is_turn'] else 'straight'
            
            if pt_type == current_type:
                current_section_points.append(pt)
            else:
                # End of section
                sections.append({
                    'type': current_type,
                    'points': current_section_points
                })
                current_type = pt_type
                current_section_points = [pt]
                
        # Close last section
        sections.append({
            'type': current_type,
            'points': current_section_points
        })
        
        # Merge small sections (noise reduction)
        # TODO: Implement merging if sections are too small
        
        return sections


