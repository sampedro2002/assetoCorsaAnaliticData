
try:
    import cv2
    print(f"OpenCV loaded: {cv2.__version__}")
except Exception as e:
    print(f"Error loading OpenCV: {e}")
except ImportError as e:
    print(f"ImportError loading OpenCV: {e}")
