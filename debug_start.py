import sys
import traceback

try:
    print("Attempting to import backend.main...")
    import backend.main
    print("Import successful. Attempting to initialize TelemetrySystem...")
    system = backend.main.TelemetrySystem()
    print("Initialization successful.")
except Exception:
    traceback.print_exc()
