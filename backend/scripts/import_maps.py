
import os
import shutil
import configparser
from pathlib import Path

# Configuration
AC_TRACKS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa\content\tracks"
DEST_PATH = Path(r"c:\Users\Det-Pc\Documents\SEMESTRE5\INFRA II\AssetoCorsaF\frontend\assets\tracks")

def import_maps():
    if not os.path.exists(AC_TRACKS_PATH):
        print(f"❌ AC Tracks contents not found at: {AC_TRACKS_PATH}")
        return

    # Ensure destination exists
    DEST_PATH.mkdir(parents=True, exist_ok=True)
    
    count_map = 0
    count_ini = 0
    
    # Iterate over all track folders
    for track_name in os.listdir(AC_TRACKS_PATH):
        track_dir = Path(AC_TRACKS_PATH) / track_name
        if not track_dir.is_dir():
            continue
            
        # Check for layouts (subdirectories with map.png)
        # Strategy: Look for map.png in root, and in immediate subfolders
        
        # 1. Check Root (e.g. monza/map.png)
        root_map = track_dir / "map.png"
        if root_map.exists():
            dest_name_base = f"{track_name}"
            # Copy PNG
            shutil.copy2(root_map, DEST_PATH / f"{dest_name_base}.png")
            count_map += 1
            
            # Look for map.ini (root/data/map.ini or root/map.ini)
            map_ini = track_dir / "data" / "map.ini"
            if not map_ini.exists(): map_ini = track_dir / "map.ini"
            
            if map_ini.exists():
                shutil.copy2(map_ini, DEST_PATH / f"{dest_name_base}.ini")
                count_ini += 1
            
        # 2. Check Subfolders (layouts)
        # We assume any subfolder that has a map.png is a layout
        for item in track_dir.iterdir():
            if item.is_dir():
                layout_map = item / "map.png"
                if layout_map.exists():
                    # Naming convention: track_layout.png
                    dest_name_base = f"{track_name}_{item.name}"
                    
                    # Copy PNG
                    shutil.copy2(layout_map, DEST_PATH / f"{dest_name_base}.png")
                    count_map += 1
                    
                    # Look for map.ini
                    map_ini = item / "data" / "map.ini"
                    if not map_ini.exists(): map_ini = item / "map.ini"
                    
                    if map_ini.exists():
                        shutil.copy2(map_ini, DEST_PATH / f"{dest_name_base}.ini")
                        count_ini += 1
                else:
                    # Sometimes map is in ui/layout/map.png or similar, but standard is root or layout root.
                    pass

    print(f"\n🎉 Finished! Imported {count_map} maps and {count_ini} configuration files to {DEST_PATH}")

if __name__ == "__main__":
    import_maps()
