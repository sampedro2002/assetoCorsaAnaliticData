import time
import json
import logging
from collections import deque
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de archivos
BASE_DIR = "data"
SESIONES_DIR = os.path.join(BASE_DIR, "pedal_analysis")

os.makedirs(SESIONES_DIR, exist_ok=True)

class PedalAnalyzer:
    def __init__(self):
        # Identificador único de sesión
        self.resetear_sesion()
        
        # Estado analítico
        self.activo = True
        
        # Buffer de alertas recientes para mostrar en UI
        self.recent_alerts = []

        logger.info(f"🏁 Pedal Analyzer Initialized")

    def resetear_sesion(self):
        """Resetea todas las variables para una nueva sesión"""
        self.id_sesion = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.nombre_sesion = f"Sesion_{self.id_sesion}"
        
        self.prev_brake = 0
        self.prev_throttle = 0
        self.prev_time = time.time()
        self.ultima_velocidad_valida = 0
        self.tiempo_detenido = 0
        self.ultimo_tiempo_detenido = None
        self.brake_start_time = None
        self.throttle_start_time = None
        self.curva_start_time = None
        self.curva_actual = None
        
        self.max_throttle = 0
        self.max_brake = 0
        self.max_speed = 0
        self.max_rpm = 0
        self.max_aceleracion = 0
        self.max_desaceleracion = 0
        self.max_derivada_freno = 0
        self.max_derivada_acelerador = 0
        
        self.frenadas_totales = 0
        self.frenadas_bruscas = 0
        self.frenadas_progresivas = 0
        self.frenadas_tardias = 0
        self.aceleraciones_anticipadas = 0
        self.aceleraciones_tardias = 0
        self.uso_incorrecto_curva = 0
        self.tc_activaciones = 0
        self.abs_activaciones = 0
        self.curvas_totales = 0
        self.curvas_excelentes = 0
        self.curvas_mejorables = 0
        
        self.tiempos_transicion = []
        self.tiempos_frenado = []
        self.tiempos_reaccion = []
        self.presiones_freno = []
        self.presiones_acelerador = []
        
        self.buffer_presion_freno = deque(maxlen=50)
        self.buffer_presion_acelerador = deque(maxlen=50)
        self.buffer_velocidad = deque(maxlen=50)
        self.buffer_steer = deque(maxlen=50)
        self.buffer_derivada_freno = deque(maxlen=20)
        
        self.serie_temporal = {
            "tiempo": [], "velocidad": [], "freno": [], "acelerador": [],
            "steering": [], "rpm": [], "marcha": [], "derivada_freno": [],
            "derivada_acelerador": []
        }
        
        self.curvas_detectadas = []
        self.recent_alerts = []
        
        logger.info(f"  🔄 Pedal Analyzer Reset - Ready for new session")

    def registrar_alerta(self, mensaje, tipo="info"):
        """Registra una alerta para ser consumida por el frontend"""
        alerta = {
            "mensaje": mensaje,
            "tipo": tipo, # info, warning, critical, success
            "timestamp": time.time()
        }
        self.recent_alerts.append(alerta)
        # Mantener solo las últimas 5
        if len(self.recent_alerts) > 5:
            self.recent_alerts.pop(0)

    def resetear_sensores_por_detencion(self, speed_kmh, throttle, brake, current_time):
        if speed_kmh < 0.1:
            if self.ultimo_tiempo_detenido is None:
                self.ultimo_tiempo_detenido = current_time
                self.tiempo_detenido = 0
            else:
                self.tiempo_detenido = current_time - self.ultimo_tiempo_detenido

            if self.tiempo_detenido > 0.5:
                if throttle > 1 or brake > 1:
                    # Resetear si estamos parados
                    logger.info(f"  🔄 RESET - Auto detenido | Acel: {throttle:.0f}%→0% | Freno: {brake:.0f}%→0%")
                    throttle = 0
                    brake = 0
                    self.throttle_start_time = None
                    self.brake_start_time = None
                    self.curva_actual = None
                    self.prev_throttle = 0
                    self.prev_brake = 0
                    self.buffer_presion_acelerador.clear()
                    self.buffer_presion_freno.clear()
                    self.buffer_presion_acelerador.append(0)
                    self.buffer_presion_freno.append(0)
                    self.buffer_derivada_freno.clear()
                    if self.serie_temporal["tiempo"]:
                        self.serie_temporal["acelerador"][-1] = 0
                        self.serie_temporal["freno"][-1] = 0
        else:
            self.ultimo_tiempo_detenido = None
            self.tiempo_detenido = 0
        return throttle, brake

    def calcular_derivada(self, valor_actual, valor_anterior, delta_t):
        if delta_t > 0 and valor_anterior is not None:
            return (valor_actual - valor_anterior) / delta_t
        return 0

    def detectar_curva(self, steer_angle, speed, brake, throttle, current_time):
        """Detecta inicio, desarrollo y fin de curvas"""
        if abs(steer_angle) > 5 and speed > 20:
            if self.curva_actual is None:
                self.curva_actual = {
                    "inicio": current_time,
                    "angulo_max": 0,
                    "freno_max": 0,
                    "freno_promedio": 0,
                    "velocidad_entrada": speed,
                    "velocidad_minima": speed,
                    "velocidad_salida": 0,
                    "acelerador_min": 100,
                    "acelerador_promedio": 0,
                    "muestras": 0,
                    "suma_freno": 0,
                    "suma_acelerador": 0,
                    "freno_incorrecto": False
                }
                self.curvas_totales += 1

            # Actualizar métricas
            self.curva_actual["angulo_max"] = max(self.curva_actual["angulo_max"], abs(steer_angle))
            self.curva_actual["freno_max"] = max(self.curva_actual["freno_max"], brake)
            self.curva_actual["velocidad_minima"] = min(self.curva_actual["velocidad_minima"], speed)
            self.curva_actual["acelerador_min"] = min(self.curva_actual["acelerador_min"], throttle)
            self.curva_actual["suma_freno"] += brake
            self.curva_actual["suma_acelerador"] += throttle
            self.curva_actual["muestras"] += 1

            # Uso incorrecto del freno en curva
            if abs(steer_angle) > 12 and brake > 25 and not self.curva_actual["freno_incorrecto"]:
                self.curva_actual["freno_incorrecto"] = True
                self.uso_incorrecto_curva += 1
                logger.info(f"  ⚠️ FRENO EN CURVA detectado - Ángulo: {steer_angle:.1f}°, Freno: {brake:.0f}%")
                self.registrar_alerta(f"⚠️ FRENO EN CURVA ({brake:.0f}%)", "warning")

        else:
            if self.curva_actual is not None:
                # Calcular promedios
                if self.curva_actual["muestras"] > 0:
                    self.curva_actual["freno_promedio"] = self.curva_actual["suma_freno"] / self.curva_actual["muestras"]
                    self.curva_actual["acelerador_promedio"] = self.curva_actual["suma_acelerador"] / self.curva_actual["muestras"]

                # Fin de curva
                self.curva_actual["fin"] = current_time
                self.curva_actual["duracion"] = self.curva_actual["fin"] - self.curva_actual["inicio"]
                self.curva_actual["velocidad_salida"] = speed
                self.curva_actual["perdida_velocidad"] = self.curva_actual["velocidad_entrada"] - self.curva_actual["velocidad_minima"]
                
                # Clasificar calidad de la curva al terminar
                calidad = "NORMAL"
                if self.curva_actual["freno_max"] < 30 and self.curva_actual["acelerador_min"] < 20:
                    calidad = "EXCELENTE"
                    self.curvas_excelentes += 1
                    self.registrar_alerta("⭐ Curva Excelente", "success")
                elif self.curva_actual["freno_max"] < 50:
                    calidad = "BUENA"
                elif self.curva_actual["freno_max"] > 70 and self.curva_actual["angulo_max"] > 15:
                    calidad = "MEJORABLE"
                    self.curvas_mejorables += 1
                
                self.curva_actual["calidad"] = calidad
                self.curvas_detectadas.append(self.curva_actual)
                self.curva_actual = None

    def procesar_muestra(self, snapshot):
        """Procesa una muestra de telemetría (dict)"""
        if not self.activo or not snapshot:
            return {}

        try:
            # Extraer datos del snapshot
            speed_kmh = snapshot.get('speed', 0)
            rpm = snapshot.get('rpm', 0)
            # Normalizar inputs (0-1 -> 0-100) si vienen en rango 0-1, si no, asumir 0-100 o ajustar
            # En reader.py vimos que throttle/brake vienen directos de AC physics, que son 0-1
            throttle = max(0, min(100, snapshot.get('throttle', 0) * 100))
            brake = max(0, min(100, snapshot.get('brake', 0) * 100))
            steer_angle = snapshot.get('steering', 0)
            gear = snapshot.get('gear', 0)
            # Estos campos nuevos los añadimos en reader.py
            abs_active = 1 if snapshot.get('abs', 0) > 0 else 0 
            tc_active = 1 if snapshot.get('tc', 0) > 0 else 0
            
            # CORRECCIÓN: Limitar velocidad máxima realista
            if speed_kmh > 400:
                 speed_kmh = self.ultima_velocidad_valida if self.ultima_velocidad_valida > 0 else 0

            current_time = time.time()
            delta_t = current_time - self.prev_time if self.prev_time > 0 else 0.016

            throttle, brake = self.resetear_sensores_por_detencion(
                speed_kmh, throttle, brake, current_time
            )

            # Actualizar Máximos
            if speed_kmh < 400:
                self.max_speed = max(self.max_speed, speed_kmh)
            self.max_throttle = max(self.max_throttle, throttle)
            self.max_brake = max(self.max_brake, brake)
            self.max_rpm = max(self.max_rpm, rpm)

            if abs_active: self.abs_activaciones += 1
            if tc_active: self.tc_activaciones += 1

            # Derivadas
            derivada_freno = self.calcular_derivada(brake, self.prev_brake, delta_t)
            derivada_acelerador = self.calcular_derivada(throttle, self.prev_throttle, delta_t)

            self.max_derivada_freno = max(self.max_derivada_freno, abs(derivada_freno))
            self.max_derivada_acelerador = max(self.max_derivada_acelerador, abs(derivada_acelerador))
            
            # Buffers
            self.buffer_derivada_freno.append(derivada_freno)
            self.buffer_presion_freno.append(brake)
            self.buffer_presion_acelerador.append(throttle)
            self.buffer_velocidad.append(speed_kmh)
            self.buffer_steer.append(steer_angle)
            
            # Listas para promedios
            self.presiones_freno.append(brake)
            self.presiones_acelerador.append(throttle)

            # Serie Temporal Completa
            self.serie_temporal["tiempo"].append(current_time)
            self.serie_temporal["velocidad"].append(speed_kmh)
            self.serie_temporal["freno"].append(brake)
            self.serie_temporal["acelerador"].append(throttle)
            self.serie_temporal["steering"].append(steer_angle)
            self.serie_temporal["rpm"].append(rpm)
            self.serie_temporal["marcha"].append(gear)
            self.serie_temporal["derivada_freno"].append(derivada_freno)
            self.serie_temporal["derivada_acelerador"].append(derivada_acelerador)
            
            # Limitar tamaño de serie temporal en memoria
            if len(self.serie_temporal["tiempo"]) > 5000:
                for key in self.serie_temporal:
                    self.serie_temporal[key] = self.serie_temporal[key][-5000:]

            # Cálculo de aceleración
            if delta_t > 0 and len(self.buffer_velocidad) > 1:
                aceleracion = (speed_kmh - self.buffer_velocidad[-2]) / delta_t
                if aceleracion > 0:
                    self.max_aceleracion = max(self.max_aceleracion, aceleracion)
                else:
                    self.max_desaceleracion = max(self.max_desaceleracion, abs(aceleracion))

            # Análisis Acelerador
            # Transición 0-100%
            if throttle > 3 and self.throttle_start_time is None and self.prev_throttle < 3:
                self.throttle_start_time = current_time

            if throttle >= 90 and self.throttle_start_time is not None:
                tiempo_transicion = current_time - self.throttle_start_time
                if 0.05 < tiempo_transicion < 2.0:
                    self.tiempos_transicion.append(tiempo_transicion)
                    logger.info(f"  ✅ Transición 0-100%: {tiempo_transicion:.3f}s")
                    self.registrar_alerta(f"✅ Transición 0-100%: {tiempo_transicion:.2f}s", "success")
                self.throttle_start_time = None
            elif throttle < 1:
                self.throttle_start_time = None
                
            # Aceleración anticipada
            if speed_kmh < 80 and throttle > 80 and abs(steer_angle) > 8:
                self.aceleraciones_anticipadas += 1
                logger.info(f"  🏎️ Aceleración ANTICIPADA en curva")
            
            # Aceleración tardía
            if speed_kmh > 180 and throttle < 30 and brake < 5 and abs(steer_angle) < 3:
                self.aceleraciones_tardias += 1
                logger.info(f"  ⚠️ Aceleración TARDÍA en recta")

            # Análisis Freno
            if brake > 5 and self.prev_brake <= 5:
                self.frenadas_totales += 1
                self.brake_start_time = current_time
                logger.info(f"  🛑 Inicio frenada #{self.frenadas_totales} - Vel: {speed_kmh:.0f} km/h")
            
            if brake > 10:
                if derivada_freno > 40: # Un poco menos sensible que el original
                    self.frenadas_bruscas += 1
                    logger.info(f"  ⚠️ Frenada BRUSCA - Derivada: {derivada_freno:.1f}%/s")
                    self.registrar_alerta(f"⚠️ Frenada BRUSCA", "warning")
                elif derivada_freno < 20 and derivada_freno > 5:
                    self.frenadas_progresivas += 1
                    logger.info(f"  ✅ Frenada PROGRESIVA - Derivada: {derivada_freno:.1f}%/s")

                # Frenada tardía (a alta velocidad)
                if speed_kmh > 170 and derivada_freno > 35:
                    self.frenadas_tardias += 1
                    logger.info(f"  ⚠️ Frenada TARDÍA a alta velocidad!")
                    self.registrar_alerta("⚠️ Frenada TARDÍA", "warning")

            if brake < 3 and self.brake_start_time is not None:
                tiempo_frenado = current_time - self.brake_start_time
                if 0.1 < tiempo_frenado < 8:
                    self.tiempos_frenado.append(tiempo_frenado)
                    logger.info(f"  📊 Tiempo frenado: {tiempo_frenado:.2f}s")
                self.brake_start_time = None

            # Análisis Curvas
            self.detectar_curva(steer_angle, speed_kmh, brake, throttle, current_time)

            # Actualizar previos
            self.prev_brake = brake
            self.prev_throttle = throttle
            self.prev_time = current_time
            if 0.1 < speed_kmh < 400:
                self.ultima_velocidad_valida = speed_kmh

            # Retornar datos "Live" para el dashboard
            return self.get_current_stats()

        except Exception as e:
            logger.error(f"Error en PedalAnalyzer: {e}")
            return {}

    def get_current_stats(self):
        """Retorna estadísticas en tiempo real para el WebSocket"""
        return {
            "pedal_metrics": {
                "frenadas_totales": self.frenadas_totales,
                "frenadas_bruscas": self.frenadas_bruscas,
                "curvas_excelentes": self.curvas_excelentes,
                "curvas_mejorables": self.curvas_mejorables,
                "max_velocidad": round(self.max_speed, 1),
                "uso_incorrecto_curva": self.uso_incorrecto_curva,
                "tiempo_reaccion_media": round(sum(self.tiempos_transicion)/len(self.tiempos_transicion), 2) if self.tiempos_transicion else 0,
                "alerts": list(self.recent_alerts) # Enviar copia
            }
        }

    def calcular_puntuacion(self):
        """Calcula puntuación global del piloto (0-100)"""
        puntuacion = 70  # Puntuación base

        if self.frenadas_totales > 0:
            # Penalización por frenadas bruscas
            pct_bruscas = (self.frenadas_bruscas / self.frenadas_totales * 100)
            if pct_bruscas > 50: puntuacion -= 20
            elif pct_bruscas > 30: puntuacion -= 10
            elif pct_bruscas > 15: puntuacion -= 5

        # Penalización por freno en curva
        if self.curvas_totales > 0:
            pct_curvas_malas = (self.curvas_mejorables / self.curvas_totales * 100)
            if pct_curvas_malas > 30: puntuacion -= 15
            elif pct_curvas_malas > 15: puntuacion -= 8

        # Penalización por uso incorrecto del freno
        puntuacion -= min(15, self.uso_incorrecto_curva * 2)

        # Penalización por activación de ayudas
        puntuacion -= min(10, self.abs_activaciones // 20)
        puntuacion -= min(10, self.tc_activaciones // 20)

        # Bonus por buena transición
        if self.tiempos_transicion:
            promedio_trans = sum(self.tiempos_transicion) / len(self.tiempos_transicion)
            if promedio_trans < 0.4: puntuacion += 15
            elif promedio_trans < 0.6: puntuacion += 8
            elif promedio_trans < 0.8: puntuacion += 3

        # Bonus por curvas excelentes
        if self.curvas_totales > 0:
            pct_excelentes = (self.curvas_excelentes / self.curvas_totales * 100)
            if pct_excelentes > 50: puntuacion += 15
            elif pct_excelentes > 30: puntuacion += 8

        return max(0, min(100, round(puntuacion)))

    def obtener_nivel_piloto(self, puntuacion):
        """Determina el nivel del piloto basado en la puntuación"""
        if puntuacion >= 90: return "🏆 PILOTO ÉLITE"
        elif puntuacion >= 75: return "🚀 PILOTO AVANZADO"
        elif puntuacion >= 60: return "📈 PILOTO INTERMEDIO"
        elif puntuacion >= 40: return "🎓 PILOTO EN ENTRENAMIENTO"
        else: return "🔄 PRINCIPIANTE"

    def generar_conclusion(self):
        """Genera conclusión personalizada del rendimiento"""
        conclusiones = []

        # Análisis de velocidad máxima
        if self.max_speed > 250:
            conclusiones.append(f"🏁 Alcanzaste {self.max_speed:.0f} km/h, buen aprovechamiento de rectas.")
        elif self.max_speed > 200:
            conclusiones.append(f"📊 Velocidad máxima de {self.max_speed:.0f} km/h, puedes mejorar en rectas.")

        # Análisis de frenado
        if self.frenadas_totales > 0:
            pct_bruscas = (self.frenadas_bruscas / self.frenadas_totales * 100)
            if pct_bruscas > 40:
                conclusiones.append(f"❌ Frenas BRUSCO en el {pct_bruscas:.0f}% de las ocasiones.")
            elif pct_bruscas > 20:
                conclusiones.append(f"⚠️ {pct_bruscas:.0f}% de frenadas bruscas.")
            else:
                conclusiones.append("✅ Buen control del freno, frenadas progresivas.")

        # Análisis de curvas
        if self.uso_incorrecto_curva > 5:
            conclusiones.append(f"❌ USO EXCESIVO del freno en curva ({self.uso_incorrecto_curva} veces).")

        if self.curvas_totales > 0:
            pct_excelentes = (self.curvas_excelentes / self.curvas_totales * 100)
            if pct_excelentes > 50:
                conclusiones.append(f"🏆 Excelente precisión en curvas ({pct_excelentes:.0f}% perfectas).")

        return " ".join(conclusiones) or "✅ Sesión registrada."

    def generar_estadisticas(self):
        """Genera JSON COMPLETO con TODOS los resultados de la sesión"""
        
        # Promedios
        promedio_transicion = sum(self.tiempos_transicion) / len(self.tiempos_transicion) if self.tiempos_transicion else 0
        promedio_frenado = sum(self.tiempos_frenado) / len(self.tiempos_frenado) if self.tiempos_frenado else 0
        promedio_reaccion = sum(self.tiempos_reaccion) / len(self.tiempos_reaccion) if self.tiempos_reaccion else 0
        
        presion_promedio_freno = sum(self.presiones_freno) / len(self.presiones_freno) if self.presiones_freno else 0
        presion_promedio_acelerador = sum(self.presiones_acelerador) / len(self.presiones_acelerador) if self.presiones_acelerador else 0
        
        pct_bruscas = (self.frenadas_bruscas / self.frenadas_totales * 100) if self.frenadas_totales > 0 else 0
        pct_progresivas = (self.frenadas_progresivas / self.frenadas_totales * 100) if self.frenadas_totales > 0 else 0
        precision_curvas = (self.curvas_excelentes / self.curvas_totales * 100) if self.curvas_totales > 0 else 0
        
        duracion = 0
        if self.serie_temporal["tiempo"]:
            duracion = self.serie_temporal["tiempo"][-1] - self.serie_temporal["tiempo"][0]
            
        puntuacion = self.calcular_puntuacion()
        nivel = self.obtener_nivel_piloto(puntuacion)
        conclusion = self.generar_conclusion()

        estadisticas = {
            "metadata": {
                "id_sesion": self.id_sesion,
                "nombre": self.nombre_sesion,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duracion_segundos": round(duracion, 1),
                "total_muestras": len(self.serie_temporal["tiempo"])
            },
            "maximos": {
                "velocidad_kmh": round(self.max_speed, 1),
                "acelerador_porcentaje": round(self.max_throttle, 1),
                "freno_porcentaje": round(self.max_brake, 1),
                "rpm": int(self.max_rpm),
                "aceleracion_kmh_s": round(self.max_aceleracion, 2),
                "desaceleracion_kmh_s": round(self.max_desaceleracion, 2),
                "derivada_freno_porcentaje_s": round(self.max_derivada_freno, 1),
                "derivada_acelerador_porcentaje_s": round(self.max_derivada_acelerador, 1)
            },
            "promedios": {
                "tiempo_transicion_0_100_s": round(promedio_transicion, 3),
                "tiempo_frenado_s": round(promedio_frenado, 3),
                "tiempo_reaccion_s": round(promedio_reaccion, 3),
                "presion_freno_porcentaje": round(presion_promedio_freno, 1),
                "presion_acelerador_porcentaje": round(presion_promedio_acelerador, 1)
            },
            "frenado": {
                "totales": self.frenadas_totales,
                "bruscas": self.frenadas_bruscas,
                "progresivas": self.frenadas_progresivas,
                "tardias": self.frenadas_tardias,
                "porcentaje_bruscas": round(pct_bruscas, 1),
                "porcentaje_progresivas": round(pct_progresivas, 1),
                "tiempos_frenado_lista": [round(t, 3) for t in self.tiempos_frenado[-20:]],
            },
            "aceleracion": {
                "anticipadas": self.aceleraciones_anticipadas,
                "tardias": self.aceleraciones_tardias,
                "tiempos_transicion_lista": [round(t, 3) for t in self.tiempos_transicion[-20:]],
            },
            "curvas": {
                "curvas_totales": self.curvas_totales,
                "curvas_excelentes": self.curvas_excelentes,
                "curvas_mejorables": self.curvas_mejorables,
                "uso_incorrecto_freno": self.uso_incorrecto_curva,
                "precision_porcentaje": round(precision_curvas, 1),
                "detalle_curvas": self.curvas_detectadas[-10:] # Ultimas 10
            },
            "sistemas_ayuda": {
                "abs_activaciones": self.abs_activaciones,
                "tc_activaciones": self.tc_activaciones,
            },
            "resumen": {
                "puntuacion_total": puntuacion,
                "nivel_piloto": nivel,
                "conclusion": conclusion
            },
            "graficos": {
                # Muestreo cada 10 para no saturar JSON
                "tiempo": self.serie_temporal["tiempo"][::10] if self.serie_temporal["tiempo"] else [],
                "velocidad": self.serie_temporal["velocidad"][::10] if self.serie_temporal["velocidad"] else [],
                "freno": self.serie_temporal["freno"][::10] if self.serie_temporal["freno"] else [],
                "acelerador": self.serie_temporal["acelerador"][::10] if self.serie_temporal["acelerador"] else [],
                "steering": self.serie_temporal["steering"][::10] if self.serie_temporal["steering"] else []
            }
        }
        return estadisticas

    def guardar_sesion(self):
        """Guarda la sesión en un archivo JSON"""
        if not self.serie_temporal["tiempo"]:
            return None
            
        stats = self.generar_estadisticas()
        archivo = f"{SESIONES_DIR}/{self.nombre_sesion}.json"
        
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ SESIÓN GUARDADA: {archivo}")
            return archivo
        except Exception as e:
            logger.error(f"Error guardando sesión: {e}")
            return None
