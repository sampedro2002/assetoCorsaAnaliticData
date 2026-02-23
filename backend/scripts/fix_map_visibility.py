
import cv2
import numpy as np
import os
from pathlib import Path

# Configuration
ASSETS_DIR = Path(r"frontend/assets/tracks")

def fix_map_visibility():
    full_path = Path.cwd() / ASSETS_DIR
    if not full_path.exists():
        print(f"❌ Assets directory not found: {full_path}")
        return

    print(f"🎨 Fixing map visibility in {full_path}...")
    
    count = 0
    for file_path in full_path.glob("*.png"):
        try:
            # Read image with Alpha channel
            img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
            
            if img is None:
                continue

            has_alpha = (len(img.shape) == 3 and img.shape[2] == 4)
            
            if has_alpha:
                # ── SCENARIO 1: Transparent PNG ──
                # Check the color of the visible pixels.
                # If they are dark, make them White/Bright.
                
                b, g, r, a = cv2.split(img)
                
                # Mask of visible pixels (alpha > 10)
                visible_mask = a > 10
                
                if np.count_nonzero(visible_mask) > 0:
                    # Calculate average brightness of visible pixels
                    # We look at the original RGB values where alpha is high
                    # But simpler: Just force everything visible to WHITE 
                    # This guarantees visibility on dark dashboard.
                    
                    # Force White (255, 255, 255) on visible pixels
                    # Keeps the original Alpha channel for antialiasing edges
                    img[:, :, 0][visible_mask] = 255 # B
                    img[:, :, 1][visible_mask] = 255 # G
                    img[:, :, 2][visible_mask] = 255 # R
                    
                    print(f"✅ Enhanced (Transparent): {file_path.name} -> Lines turned White")

            else:
                # ── SCENARIO 2: Solid Image (Likely White BG with Black Lines) ──
                # User said "White Background, Black Lines"
                
                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Invert: Black lines (0) -> become White (255)
                # White background (255) -> becomes Black (0)
                inverted = cv2.bitwise_not(gray)
                
                # Create Alpha Channel
                # We want the Background (now Black/0 from inversion) to be Transparent
                # We want the Lines (now White/255 from inversion) to be Opaque
                
                # Use the inverted image ITSELF as the alpha channel?
                # Yes: Dark areas (original BG) become low alpha (transparent)
                # Bright areas (original lines) become high alpha (opaque)
                
                # New RGBA
                # color: White (255,255,255)
                # alpha: From inverted image
                
                b_ch = np.full_like(gray, 255)
                g_ch = np.full_like(gray, 255)
                r_ch = np.full_like(gray, 255)
                a_ch = inverted # 0=Transparent, 255=Opaque
                
                # Threshold alpha to clean up noise/artifacts?
                # _, a_ch = cv2.threshold(a_ch, 20, 255, cv2.THRESH_BINARY) 
                # Keeping gradient might be nicer for antialiasing if input was good.
                # Let's clean lightly
                # a_ch = np.where(a_ch < 20, 0, a_ch) 
                
                img = cv2.merge([b_ch, g_ch, r_ch, a_ch])
                
                print(f"✅ Converted (Solid): {file_path.name} -> Inverted to White lines on Transparent")

            # Save back
            cv2.imwrite(str(file_path), img)
            count += 1
            
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")

    print(f"\n✨ Finished! Fixed visibility for {count} maps.")

if __name__ == "__main__":
    fix_map_visibility()
