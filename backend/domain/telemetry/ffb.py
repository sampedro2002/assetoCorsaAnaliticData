import numpy as np
import time

class FFBAnalyzer:
    def __init__(self):
        self.history_window = 50  # Muestras para suavizado
        
        # --- GRUPO 3: Historiales para cálculos avanzados ---
        self.ffb_history = []      # Para calcular RMS (último 1s)
        self.peak_timestamps = []  # Para contar picos (últimos 10s)
        self.is_peaking = False    # Estado para detectar flanco de subida
        # ----------------------------------------------------
        
        self.last_update = time.time()

    def analyze_realtime(self, snapshot):
        """
        Analiza el snapshot de telemetría y genera datos para el Grupo 3.
        Si faltan datos crudos de física, los estima usando G-Force y Speed
        para que el dashboard no se quede congelado.
        """
        current_time = time.time()
        
        # 1. Extraer datos básicos (que sabemos que sí funcionan)
        speed = snapshot.get('speed', 0)
        steer = snapshot.get('steering', 0) # -1 a 1 (o en grados)
        g_lat = snapshot.get('g_force_lat', 0)
        g_long = snapshot.get('g_force_long', 0)
        
        # --- CÁLCULO DE FUERZA FFB (Simulado si no hay real) ---
        raw_ffb = snapshot.get('steerTorque', 0)
        
        if raw_ffb == 0:
            # Estimación: Más velocidad + Más giro = Más fuerza
            calculated_ffb = (abs(steer) * 0.5) + (abs(g_lat) * 0.3)
            # Añadir vibración por velocidad (efecto carretera)
            road_noise = np.random.normal(0, 0.02) * (speed / 100.0)
            final_ffb = min(calculated_ffb + abs(road_noise), 1.0)
        else:
            final_ffb = raw_ffb / 100.0 # Normalizar si viene en escala grande

        # --- GRUPO 3: CÁLCULOS AVANZADOS (RMS y PICOS) ---
        
        # 1. Cálculo RMS (Root Mean Square) - Intensidad promedio vibración
        self.ffb_history.append((current_time, final_ffb))
        # Mantener solo último 1 segundo de datos
        self.ffb_history = [x for x in self.ffb_history if x[0] > current_time - 1.0]
        
        if self.ffb_history:
            values = [x[1] for x in self.ffb_history]
            # Fórmula RMS: Raíz cuadrada de la media de los cuadrados
            rms_val = np.sqrt(np.mean(np.square(values)))
        else:
            rms_val = 0.0

        # 2. Detección de Picos (Clipping > 95%)
        # Contamos "eventos", no "frames". Solo cuenta cuando sube por encima de 0.95
        if final_ffb > 0.95 and not self.is_peaking:
            self.is_peaking = True
            self.peak_timestamps.append(current_time)
        elif final_ffb < 0.90:
            self.is_peaking = False
            
        # Mantener solo picos de los últimos 10 segundos
        self.peak_timestamps = [t for t in self.peak_timestamps if t > current_time - 10.0]
        peak_count = len(self.peak_timestamps)

        # ---------------------------------------------------

        # --- CÁLCULO DE VIBRACIONES (Sección 2) ---
        
        # Vibración Piano (Kerb)
        kerb_vib = 0.0
        if abs(g_lat) > 0.8: 
             kerb_vib = np.random.uniform(0.1, 0.4)
        
        # Vibración Derrape (Slip)
        slip_vib = 0.0
        if abs(g_lat) > 1.2 or (abs(steer) > 0.5 and speed > 50):
            slip_vib = np.random.uniform(0.3, 0.8)

        # Vibración ABS
        abs_vib = 0.0
        if g_long < -0.8:
            abs_vib = np.random.uniform(0.5, 1.0)

        # --- CÁLCULO DE SUSPENSIÓN (Gemelo Digital Visual) ---
        fl = 0.5 
        fr = 0.5
        rl = 0.5
        rr = 0.5
        
        # Efecto frenada/aceleración (Pitch)
        pitch_factor = g_long * 0.15 
        fl += pitch_factor
        fr += pitch_factor
        rl -= pitch_factor
        rr -= pitch_factor
        
        # Efecto giro (Roll)
        roll_factor = g_lat * 0.15
        fl -= roll_factor
        rl -= roll_factor
        fr += roll_factor
        rr += roll_factor
        
        # Ruido carretera
        susp_noise = (speed / 300.0) * 0.05
        fl += np.random.uniform(-susp_noise, susp_noise)
        fr += np.random.uniform(-susp_noise, susp_noise)
        rl += np.random.uniform(-susp_noise, susp_noise)
        rr += np.random.uniform(-susp_noise, susp_noise)

        suspension_travel = [
            np.clip(fl, 0, 1),
            np.clip(fr, 0, 1),
            np.clip(rl, 0, 1),
            np.clip(rr, 0, 1)
        ]

        # Retornar datos (incluyendo los nuevos campos RMS y Picos)
        return {
            "finalFF": float(final_ffb),
            "rmsValue": float(rms_val),       # Nuevo campo
            "peakCount": int(peak_count),     # Nuevo campo
            "kerbVibration": float(kerb_vib),
            "slipVibrations": float(slip_vib),
            "absVibrations": float(abs_vib),
            "suspensionTravel": suspension_travel
        }
