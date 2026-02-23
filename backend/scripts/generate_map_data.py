
import sys
import os
import json
import logging
import argparse
from pathlib import Path
import cv2

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.domain.analysis.track_mapper import TrackMapper
from backend.core.config import AC_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MapGenerator")

def main():
    parser = argparse.ArgumentParser(description="Generate Track Map Coordinates")
    parser.add_argument("track_name", help="Track name (e.g., 'ks_monza' or 'ks_silverstone@gp')")
    parser.add_argument("--length", type=float, help="Track length in meters", required=True)
    parser.add_argument("--interval", type=float, default=200.0, help="Interval in meters for markers")
    parser.add_argument("--output", help="Output JSON path", default=None)
    parser.add_argument("--start-pos", nargs=2, type=float, metavar=('X', 'Z'), help="World coordinates (X, Z) of the start line")
    
    args = parser.parse_args()
    
    track_name = args.track_name
    length_m = args.length
    interval = args.interval
    start_pos = tuple(args.start_pos) if args.start_pos else None
    
    logger.info(f"Processing track: {track_name} (Length: {length_m}m, Interval: {interval}m)")
    
    try:
        mapper = TrackMapper(track_name, AC_CONFIG['install_path'])
        
        # Process map
        points, cum_dist = mapper.process_track_map(length_m, start_world_pos=start_pos)
        
        # Generate points
        dist_markers = []
        d = 0
        while d < length_m:
            dist_markers.append(d)
            d += interval
            
        # Get coordinates
        results = mapper.get_interpolated_coordinates(points, cum_dist, dist_markers)
        
        # Draw on image for verification
        img = cv2.imread(str(mapper.image_path))
        for res in results:
            x, y = res['x'], res['y']
            dist = res['dist_m']
            cv2.circle(img, (x, y), 8, (0, 0, 255), -1)
            cv2.putText(img, str(int(dist)), (x+10, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
        # Save output
        output_dir = Path("data/track_maps")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = args.output if args.output else output_dir / f"{track_name}_map.json"
        img_path = output_dir / f"{track_name}_annotated.png"
        
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        cv2.imwrite(str(img_path), img)
        
        logger.info(f"Successfully generated map data: {json_path}")
        logger.info(f"Annotated image saved: {img_path}")
        
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        logger.error(f"Failed to generate map: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
