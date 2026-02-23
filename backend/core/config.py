"""
Configuration management for Assetto Corsa Telemetry System
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# 1. Try local .env (priority)
if os.path.exists('.env'):
    load_dotenv('.env')
# 2. Try bundled .env if running as executable
elif hasattr(sys, '_MEIPASS'):
    bundle_env = os.path.join(sys._MEIPASS, '.env')
    if os.path.exists(bundle_env):
        load_dotenv(bundle_env)
else:
    load_dotenv()

# Database Configuration (SQLite)
DB_CONFIG = {
    'database_path': os.getenv('DB_PATH', './data/assetto_corsa.db')
}

# Server Configuration
SERVER_CONFIG = {
    'host': os.getenv('SERVER_HOST', '0.0.0.0'),
    'port': int(os.getenv('SERVER_PORT', 8080))
}

# Assetto Corsa Configuration
AC_CONFIG = {
    'install_path': os.getenv('AC_INSTALL_PATH', r'C:\Program Files (x86)\Steam\steamapps\common\assettocorsa'),
    'physics_memory': 'Local\\acpmf_physics',
    'graphics_memory': 'Local\\acpmf_graphics',
    'static_memory': 'Local\\acpmf_static'
}

# Telemetry Settings
TELEMETRY_CONFIG = {
    'sample_rate_ms': int(os.getenv('TELEMETRY_SAMPLE_RATE', 100)),
    'corner_detection_threshold': float(os.getenv('CORNER_DETECTION_THRESHOLD', 0.3)),
    'braking_threshold': float(os.getenv('BRAKING_THRESHOLD', -0.5))
}

# Analysis Settings
ANALYSIS_CONFIG = {
    'min_laps_for_analysis': 1,
    'optimal_tire_temp_range': (75, 95),  # Celsius
    'optimal_brake_temp_range': (200, 400),  # Celsius
    'tire_pressure_warning_threshold': 2.0  # PSI deviation
}
