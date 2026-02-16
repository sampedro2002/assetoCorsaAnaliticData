import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SteeringAnalyzer:
    """
    Analyzes steering wheel inputs, calculates dynamics (velocity, acceleration),
    and tracks session statistics.
    """
    def __init__(self):
        self.reset_session()

    def reset_session(self):
        """Reset all session-specific tracking variables"""
        self.previous_steering_angle: float = 0.0
        self.previous_angular_velocity: float = 0.0
        self.previous_timestamp: float = 0.0
        
        # Session Stats
        self.max_steering_angle_session: float = 0.0
        self.max_angular_velocity_session: float = 0.0
        self.max_mz_session: float = 0.0
        
        # Buffer for database storage (optional, if we want to handle batching here)
        self.buffer: List[Dict[str, Any]] = []
        
        logger.info("🔄 Steering Analyzer Reset")

    def process_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single telemetry snapshot.
        Calculates derivatives and updates stats.
        Returns a dictionary of new metrics to update the snapshot with.
        """
        if not snapshot:
            return {}

        current_timestamp = snapshot.get('timestamp', 0)
        current_steering = snapshot.get('steering', 0)
        
        # Initialize derivatives
        angular_velocity = 0.0
        angular_acceleration = 0.0
        sample_frequency = 0.0

        # Calculate time delta
        if self.previous_timestamp > 0:
            delta_time = current_timestamp - self.previous_timestamp
            
            if delta_time > 0:
                # Calculate angular velocity (degrees per second)
                angular_velocity = (current_steering - self.previous_steering_angle) / delta_time
                
                # Calculate angular acceleration (degrees per second squared)
                angular_acceleration = (angular_velocity - self.previous_angular_velocity) / delta_time
                
                # Calculate sample frequency (Hz)
                sample_frequency = 1.0 / delta_time
                
                # Update Session Stats
                self.max_steering_angle_session = max(self.max_steering_angle_session, abs(current_steering))
                self.max_angular_velocity_session = max(self.max_angular_velocity_session, abs(angular_velocity))
                
                mz_current = max(abs(snapshot.get('mz_fl', 0)), abs(snapshot.get('mz_fr', 0)))
                self.max_mz_session = max(self.max_mz_session, mz_current)
                
                # Update previous values for next iteration
                self.previous_angular_velocity = angular_velocity

        # Update state persistence
        self.previous_steering_angle = current_steering
        self.previous_timestamp = current_timestamp

        # Return the computed metrics to be merged into the snapshot
        return {
            'angular_velocity': angular_velocity,
            'angular_acceleration': angular_acceleration,
            'max_steering_angle_session': self.max_steering_angle_session,
            'max_angular_velocity_session': self.max_angular_velocity_session,
            'max_mz_session': self.max_mz_session,
            'steering_sample_frequency': sample_frequency
        }

    def get_buffer_data(self, lap_id, current_timestamp, snapshot, calculated_metrics):
        """
        Helper to format data for database insertion if needed.
        """
        return {
            'lap_id': lap_id,
            'timestamp': current_timestamp,
            'steering_angle': snapshot.get('steering', 0),
            'angular_velocity': calculated_metrics.get('angular_velocity', 0),
            'angular_acceleration': calculated_metrics.get('angular_acceleration', 0),
            'brake_percentage': snapshot.get('brake', 0) * 100.0,
            'throttle_percentage': snapshot.get('throttle', 0) * 100.0,
            'sample_frequency': calculated_metrics.get('steering_sample_frequency', 0)
        }
