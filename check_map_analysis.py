
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

from backend.domain.analysis.map_analyzer import MapAnalyzer
from backend.domain.analysis.analyzer import DataAnalyzer
from backend.database.database import Database
from backend.core.config import AC_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MapAnalysisCheck")

def check_map_analysis():
    print(f"Checking Map Analysis in {AC_CONFIG['install_path']}")
    
    analyzer = MapAnalyzer(AC_CONFIG['install_path'])
    
    # Try to analyze a dummy track or a known track
    # We don't know which tracks the user has, but we can verify classes load
    
    print("MapAnalyzer initialized.")
    
    try:
        db = Database()
        data_analyzer = DataAnalyzer(db)
        print("DataAnalyzer initialized successfully with MapAnalyzer.")
        
        # Test loading a non-existent track (should return None/False but not crash)
        result = analyzer.analyze_map("deployment_test_track")
        if result is None:
            print("Safe handling of missing track verified.")
        else:
            print("Unexpected result for missing track.")
            
    except Exception as e:
        print(f"Error initializing DataAnalyzer: {e}")
        return False
        
    return True

if __name__ == "__main__":
    check_map_analysis()
