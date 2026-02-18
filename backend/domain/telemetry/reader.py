"""
Assetto Corsa Shared Memory Reader
Reads telemetry data from AC's shared memory regions
"""
import mmap
import struct
import ctypes
import logging
from typing import Optional, Dict, Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import TELEMETRY_CONFIG, AC_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session type mapping
SESSION_TYPES = {
    0: "Practice",
    1: "Qualify",
    2: "Race",
    3: "Hotlap",
    4: "Time Attack",
    5: "Drift",
    6: "Drag"
}


class ACPhysics(ctypes.Structure):
    """AC Physics shared memory structure"""
    _fields_ = [
        ('packetId', ctypes.c_int32),
        ('gas', ctypes.c_float),
        ('brake', ctypes.c_float),
        ('fuel', ctypes.c_float),
        ('gear', ctypes.c_int32),
        ('rpms', ctypes.c_int32),
        ('steerAngle', ctypes.c_float),
        ('speedKmh', ctypes.c_float),
        ('velocity', ctypes.c_float * 3),
        ('accG', ctypes.c_float * 3),
        ('wheelSlip', ctypes.c_float * 4),
        ('wheelLoad', ctypes.c_float * 4),
        ('wheelsPressure', ctypes.c_float * 4),
        ('wheelAngularSpeed', ctypes.c_float * 4),
        ('tyreWear', ctypes.c_float * 4),
        ('tyreDirtyLevel', ctypes.c_float * 4),
        ('tyreCoreTemperature', ctypes.c_float * 4),
        ('camberRAD', ctypes.c_float * 4),
        ('suspensionTravel', ctypes.c_float * 4),
        ('drs', ctypes.c_float),
        ('tc', ctypes.c_float),
        ('heading', ctypes.c_float),
        ('pitch', ctypes.c_float),
        ('roll', ctypes.c_float),
        ('cgHeight', ctypes.c_float),
        ('carDamage', ctypes.c_float * 5),
        ('numberOfTyresOut', ctypes.c_int32),
        ('pitLimiterOn', ctypes.c_int32),
        ('abs', ctypes.c_float),
        ('kersCharge', ctypes.c_float),
        ('kersInput', ctypes.c_float),
        ('autoShifterOn', ctypes.c_int32),
        ('rideHeight', ctypes.c_float * 2),
        ('turboBoost', ctypes.c_float),
        ('ballast', ctypes.c_float),
        ('airDensity', ctypes.c_float),
        ('airTemp', ctypes.c_float),
        ('roadTemp', ctypes.c_float),
        ('localAngularVel', ctypes.c_float * 3),
        ('finalFF', ctypes.c_float),
        ('performanceMeter', ctypes.c_float),
        ('engineBrake', ctypes.c_int32),
        ('ersRecoveryLevel', ctypes.c_int32),
        ('ersPowerLevel', ctypes.c_int32),
        ('ersHeatCharging', ctypes.c_int32),
        ('ersIsCharging', ctypes.c_int32),
        ('kersCurrentKJ', ctypes.c_float),
        ('drsAvailable', ctypes.c_int32),
        ('drsEnabled', ctypes.c_int32),
        ('brakeTemp', ctypes.c_float * 4),
        ('clutch', ctypes.c_float),
        ('tyreTempI', ctypes.c_float * 4),
        ('tyreTempM', ctypes.c_float * 4),
        ('tyreTempO', ctypes.c_float * 4),
        ('isAIControlled', ctypes.c_int32),
        ('tyreContactPoint', ctypes.c_float * 4 * 3),
        ('tyreContactNormal', ctypes.c_float * 4 * 3),
        ('tyreContactHeading', ctypes.c_float * 4 * 3),
        ('brakeBias', ctypes.c_float),
        ('localVelocity', ctypes.c_float * 3),
        ('P2PActivations', ctypes.c_int32),
        ('P2PStatus', ctypes.c_int32),
        ('currentMaxRpm', ctypes.c_int32),
        ('mz', ctypes.c_float * 4),
        ('fx', ctypes.c_float * 4),
        ('fy', ctypes.c_float * 4),
        ('slipRatio', ctypes.c_float * 4),
        ('slipAngle', ctypes.c_float * 4),
        ('tcinAction', ctypes.c_int32),
        ('absInAction', ctypes.c_int32),
        ('suspensionDamage', ctypes.c_float * 4),
        ('tyreTemp', ctypes.c_float * 4),
        ('waterTemp', ctypes.c_float),
        ('brakePressure', ctypes.c_float * 4),
        ('frontBrakeCompound', ctypes.c_int32),
        ('rearBrakeCompound', ctypes.c_int32),
        ('padLife', ctypes.c_float * 4),
        ('discLife', ctypes.c_float * 4),
        ('ignitionOn', ctypes.c_int32),
        ('starterEngineOn', ctypes.c_int32),
        ('isEngineRunning', ctypes.c_int32),
        ('kerbVibration', ctypes.c_float),
        ('slipVibrations', ctypes.c_float),
        ('gVibrations', ctypes.c_float),
        ('absVibrations', ctypes.c_float),
    ]


class ACGraphics(ctypes.Structure):
    """AC Graphics shared memory structure"""
    _fields_ = [
        ('packetId', ctypes.c_int32),
        ('status', ctypes.c_int32),
        ('session', ctypes.c_int32),
        ('currentTime', ctypes.c_wchar * 15),
        ('lastTime', ctypes.c_wchar * 15),
        ('bestTime', ctypes.c_wchar * 15),
        ('split', ctypes.c_wchar * 15),
        ('completedLaps', ctypes.c_int32),
        ('position', ctypes.c_int32),
        ('iCurrentTime', ctypes.c_int32),
        ('iLastTime', ctypes.c_int32),
        ('iBestTime', ctypes.c_int32),
        ('sessionTimeLeft', ctypes.c_float),
        ('distanceTraveled', ctypes.c_float),
        ('isInPit', ctypes.c_int32),
        ('currentSectorIndex', ctypes.c_int32),
        ('lastSectorTime', ctypes.c_int32),
        ('numberOfLaps', ctypes.c_int32),
        ('tyreCompound', ctypes.c_wchar * 33),
        ('replayTimeMultiplier', ctypes.c_float),
        ('normalizedCarPosition', ctypes.c_float),
        ('activeCars', ctypes.c_int32),
        ('carCoordinates', ctypes.c_float * 60 * 3),
        ('carID', ctypes.c_int32 * 60),
        ('playerCarID', ctypes.c_int32),
        ('penaltyTime', ctypes.c_float),
        ('flag', ctypes.c_int32),
        ('penalty', ctypes.c_int32),
        ('idealLineOn', ctypes.c_int32),
        ('isInPitLane', ctypes.c_int32),
        ('surfaceGrip', ctypes.c_float),
        ('mandatoryPitDone', ctypes.c_int32),
        ('windSpeed', ctypes.c_float),
        ('windDirection', ctypes.c_float),
        ('isSetupMenuVisible', ctypes.c_int32),
        ('mainDisplayIndex', ctypes.c_int32),
        ('secondaryDisplayIndex', ctypes.c_int32),
        ('TC', ctypes.c_int32),
        ('TCCut', ctypes.c_int32),
        ('EngineMap', ctypes.c_int32),
        ('ABS', ctypes.c_int32),
        ('fuelXLap', ctypes.c_float),
        ('rainLights', ctypes.c_int32),
        ('flashingLights', ctypes.c_int32),
        ('lightsStage', ctypes.c_int32),
        ('exhaustTemperature', ctypes.c_float),
        ('wiperLV', ctypes.c_int32),
        ('DriverStintTotalTimeLeft', ctypes.c_int32),
        ('DriverStintTimeLeft', ctypes.c_int32),
        ('rainTyres', ctypes.c_int32),
        ('sessionIndex', ctypes.c_int32),
        ('usedFuel', ctypes.c_float),
        ('deltaLapTime', ctypes.c_wchar * 15),
        ('iDeltaLapTime', ctypes.c_int32),
        ('estimatedLapTime', ctypes.c_wchar * 15),
        ('iEstimatedLapTime', ctypes.c_int32),
        ('isDeltaPositive', ctypes.c_int32),
        ('iSplit', ctypes.c_int32),
        ('isValidLap', ctypes.c_int32),
        ('fuelEstimatedLaps', ctypes.c_float),
        ('trackStatus', ctypes.c_wchar * 33),
        ('missingMandatoryPits', ctypes.c_int32),
        ('Clock', ctypes.c_float),
        ('directionLightsLeft', ctypes.c_int32),
        ('directionLightsRight', ctypes.c_int32),
        ('GlobalYellow', ctypes.c_int32),
        ('GlobalYellow1', ctypes.c_int32),
        ('GlobalYellow2', ctypes.c_int32),
        ('GlobalYellow3', ctypes.c_int32),
        ('GlobalWhite', ctypes.c_int32),
        ('GlobalGreen', ctypes.c_int32),
        ('GlobalChequered', ctypes.c_int32),
        ('GlobalRed', ctypes.c_int32),
        ('mfdTyreSet', ctypes.c_int32),
        ('mfdFuelToAdd', ctypes.c_float),
        ('mfdTyrePressureLF', ctypes.c_float),
        ('mfdTyrePressureRF', ctypes.c_float),
        ('mfdTyrePressureLR', ctypes.c_float),
        ('mfdTyrePressureRR', ctypes.c_float),
        ('trackGripStatus', ctypes.c_int32),
        ('rainIntensity', ctypes.c_int32),
        ('rainIntensityIn10min', ctypes.c_int32),
        ('rainIntensityIn30min', ctypes.c_int32),
        ('currentTyreSet', ctypes.c_int32),
        ('strategyTyreSet', ctypes.c_int32),
    ]


class ACStatic(ctypes.Structure):
    """AC Static shared memory structure"""
    _fields_ = [
        ('_smVersion', ctypes.c_wchar * 15),
        ('_acVersion', ctypes.c_wchar * 15),
        ('numberOfSessions', ctypes.c_int32),
        ('numCars', ctypes.c_int32),
        ('carModel', ctypes.c_wchar * 33),
        ('track', ctypes.c_wchar * 33),
        ('playerName', ctypes.c_wchar * 33),
        ('playerSurname', ctypes.c_wchar * 33),
        ('playerNick', ctypes.c_wchar * 33),
        ('sectorCount', ctypes.c_int32),
        ('maxTorque', ctypes.c_float),
        ('maxPower', ctypes.c_float),
        ('maxRpm', ctypes.c_int32),
        ('maxFuel', ctypes.c_float),
        ('suspensionMaxTravel', ctypes.c_float * 4),
        ('tyreRadius', ctypes.c_float * 4),
        ('maxTurboBoost', ctypes.c_float),
        ('deprecated_1', ctypes.c_float),
        ('deprecated_2', ctypes.c_float),
        ('penaltiesEnabled', ctypes.c_int32),
        ('aidFuelRate', ctypes.c_float),
        ('aidTireRate', ctypes.c_float),
        ('aidMechanicalDamage', ctypes.c_float),
        ('aidAllowTyreBlankets', ctypes.c_int32),
        ('aidStability', ctypes.c_float),
        ('aidAutoClutch', ctypes.c_int32),
        ('aidAutoBlip', ctypes.c_int32),
        ('hasDRS', ctypes.c_int32),
        ('hasERS', ctypes.c_int32),
        ('hasKERS', ctypes.c_int32),
        ('kersMaxJ', ctypes.c_float),
        ('engineBrakeSettingsCount', ctypes.c_int32),
        ('ersPowerControllerCount', ctypes.c_int32),
        ('trackSPlineLength', ctypes.c_float),
        ('trackConfiguration', ctypes.c_wchar * 33),
        ('ersMaxJ', ctypes.c_float),
        ('isTimedRace', ctypes.c_int32),
        ('hasExtraLap', ctypes.c_int32),
        ('carSkin', ctypes.c_wchar * 33),
        ('reversedGridPositions', ctypes.c_int32),
        ('PitWindowStart', ctypes.c_int32),
        ('PitWindowEnd', ctypes.c_int32),
        ('isOnline', ctypes.c_int32),
        ('dryTyresName', ctypes.c_wchar * 33),
        ('wetTyresName', ctypes.c_wchar * 33),
    ]


class TelemetryReader:
    """Reads telemetry data from Assetto Corsa shared memory"""
    
    def __init__(self):
        """Initialize shared memory connections"""
        self.physics_mmap: Optional[mmap.mmap] = None
        self.graphics_mmap: Optional[mmap.mmap] = None
        self.static_mmap: Optional[mmap.mmap] = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to AC shared memory"""
        try:
            # Try to open shared memory regions
            self.physics_mmap = mmap.mmap(-1, ctypes.sizeof(ACPhysics), AC_CONFIG['physics_memory'])
            self.graphics_mmap = mmap.mmap(-1, ctypes.sizeof(ACGraphics), AC_CONFIG['graphics_memory'])
            self.static_mmap = mmap.mmap(-1, ctypes.sizeof(ACStatic), AC_CONFIG['static_memory'])
            
            self.connected = True
            logger.info("✓ Connected to Assetto Corsa shared memory")
            return True
        except Exception as e:
            logger.warning(f"Waiting for Assetto Corsa... ({type(e).__name__}: {e})")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from shared memory"""
        if self.physics_mmap:
            self.physics_mmap.close()
        if self.graphics_mmap:
            self.graphics_mmap.close()
        if self.static_mmap:
            self.static_mmap.close()
        self.connected = False
        logger.info("✓ Disconnected from shared memory")
    
    def read_physics(self) -> Optional[ACPhysics]:
        """Read physics data"""
        if not self.connected or not self.physics_mmap:
            return None
        try:
            self.physics_mmap.seek(0)
            return ACPhysics.from_buffer_copy(self.physics_mmap)
        except Exception as e:
            logger.error(f"Error reading physics: {e}")
            return None
    
    def read_graphics(self) -> Optional[ACGraphics]:
        """Read graphics data"""
        if not self.connected or not self.graphics_mmap:
            return None
        try:
            self.graphics_mmap.seek(0)
            return ACGraphics.from_buffer_copy(self.graphics_mmap)
        except Exception as e:
            logger.error(f"Error reading graphics: {e}")
            return None
    
    def read_static(self) -> Optional[ACStatic]:
        """Read static data"""
        if not self.connected or not self.static_mmap:
            return None
        try:
            self.static_mmap.seek(0)
            return ACStatic.from_buffer_copy(self.static_mmap)
        except Exception as e:
            logger.error(f"Error reading static: {e}")
            return None
    
    def get_telemetry_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get a complete telemetry snapshot"""
        physics = self.read_physics()
        graphics = self.read_graphics()
        static = self.read_static()
        
        if not physics or not graphics or not static:
            return None
        
        # Status: 0=off, 1=replay, 2=live, 3=pause
        # Session: 0=practice, 1=qualify, 2=race, 3=hotlap, 4=time attack, 5=drift, 6=drag
        
        return {
            # Session info
            'status': graphics.status,
            'session': graphics.session,
            'session_type': SESSION_TYPES.get(graphics.session, "Unknown"),
            'track_name': static.track,
            'car_name': static.carModel,
            'completed_laps': graphics.completedLaps,
            'current_lap_time': graphics.iCurrentTime,
            'last_lap_time': graphics.iLastTime,
            'best_lap_time': graphics.iBestTime,
            'is_valid_lap': bool(graphics.isValidLap),
            'n_tires_out': physics.numberOfTyresOut,
            
            # Sector data
            'current_sector_index': graphics.currentSectorIndex,
            'last_sector_time': graphics.lastSectorTime,
            
            # Car data
            'speed': physics.speedKmh,
            'rpm': physics.rpms,
            'gear': physics.gear,
            'throttle': physics.gas,
            'brake': physics.brake,
            'steering': physics.steerAngle,
            'clutch': physics.clutch,
            
            # Position
            'pos_x': physics.velocity[0],
            'pos_y': physics.velocity[1],
            'pos_z': physics.velocity[2],
            'normalized_position': graphics.normalizedCarPosition,
            
            # G-forces
            'g_force_lat': physics.accG[0],
            'g_force_long': physics.accG[1],
            'g_force_vert': physics.accG[2],
            
            # Tires
            'tire_temp_fl': physics.tyreCoreTemperature[0],
            'tire_temp_fr': physics.tyreCoreTemperature[1],
            'tire_temp_rl': physics.tyreCoreTemperature[2],
            'tire_temp_rr': physics.tyreCoreTemperature[3],
            'tire_pressure_fl': physics.wheelsPressure[0],
            'tire_pressure_fr': physics.wheelsPressure[1],
            'tire_pressure_rl': physics.wheelsPressure[2],
            'tire_pressure_rr': physics.wheelsPressure[3],
            
            # Brakes
            'brake_temp_fl': physics.brakeTemp[0],
            'brake_temp_fr': physics.brakeTemp[1],
            'brake_temp_rl': physics.brakeTemp[2],
            'brake_temp_rr': physics.brakeTemp[3],
            
            # Fuel
            'fuel': physics.fuel,
            'max_fuel': static.maxFuel,
            
            # Other
            'water_temp': physics.waterTemp,
            'timestamp': graphics.iCurrentTime / 1000.0,  # Convert ms to seconds
            
            # Additional Telemetry (Volante Expanded)
            'force_feedback': physics.finalFF,
            'brake_bias': physics.brakeBias,
            'tc': physics.tc,
            'abs': physics.abs,
            'engine_brake': physics.engineBrake,
            'turbo_boost': physics.turboBoost,
            'kers_charge': physics.kersCharge,
            'kers_input': physics.kersInput,
            'drs': physics.drs,
            'drs_available': physics.drsAvailable,
            'drs_enabled': physics.drsEnabled,
            
            # Expanded Volante/FFB Data (Matching frontend expectations)
            'finalFF': physics.finalFF,  # Matches app.js 'finalFF'
            'force_feedback': physics.finalFF, # Keep for backward compatibility
            
            'kerbVibration': physics.kerbVibration,
            'slipVibrations': physics.slipVibrations,
            'gVibrations': physics.gVibrations,
            'absVibrations': physics.absVibrations,
            
            'suspensionTravel': [physics.suspensionTravel[0], physics.suspensionTravel[1], physics.suspensionTravel[2], physics.suspensionTravel[3]],
            
            # Session Index (Critical for restart detection)
            'session_index': graphics.sessionIndex
        }

        # Calculate steering dynamics if possible (requires previous state)
        # This would typically be done in the main loop or a wrapper, 
        # but for snapshot we return raw values. 
        # The frontend/analyzer can calculate derivatives if needed, 
        # OR we can add state tracking here.
        # Let's rely on the consumer (main.py or frontend) for derivatives 
        # to keep reader stateless/simple, 
        # UNLESS we add 'self.last_steering' state to reader.
        
        # Decision: Add derived metrics in Reader to ensure they are available
        # We need to modify __init__ and update state.

    
    def is_in_race(self) -> bool:
        """Check if currently in an active race"""
        graphics = self.read_graphics()
        if not graphics:
            return False
        
        # Status 2 = live, Status 3 = pause
        # Continue receiving data in both states
        # Include all session types: 0=Practice, 1=Qualify, 2=Race, 3=Hotlap, 4=Time Attack, 5=Drift, 6=Drag
        return graphics.status in [2, 3] and graphics.session in [0, 1, 2, 3, 4, 5, 6]
    
    def is_race_finished(self) -> bool:
        """Check if race just finished"""
        graphics = self.read_graphics()
        if not graphics:
            return False
        
        # Check if we were in a race and now status changed
        return graphics.status != 2
