# 🏎️ Assetto Corsa Telemetry System

Sistema completo de telemetría en tiempo real para Assetto Corsa con análisis post-carrera impulsado por IA.

## ✨ Características

- **Telemetría en tiempo real** - Dashboard completo con todos los datos del coche
- **Análisis con IA** - Recomendaciones específicas para mejorar tus tiempos
- **Comparación de vueltas** - Compara tu última vuelta con tu mejor vuelta
- **Base de datos SQLite** - Sin servidor, portátil y simple
- **Multi-navegador** - Compatible con Chrome, Edge, Firefox, Opera, Brave

## 🚀 Uso del Sistema

### 1. Ejecutar el servidor

```bash
python backend/main.py
```

Esto iniciará el servidor web en el puerto 8000 y podrás acceder al dashboard.

### 2. Iniciar Assetto Corsa

Inicia el juego y comienza una carrera. El sistema detectará automáticamente cuando estés en pista.

### 3. Ver Telemetría

El navegador mostrará:
- **Velocidad y RPM**
- **Marcha actual**
- **G-Forces** (lateral y longitudinal)
- **Tiempos de vuelta** (actual, última, mejor, delta)
- **Inputs del piloto** (throttle, brake, steering, FFB)
- **Combustible**
- **Neumáticos** (temperaturas y presiones)
- **Frenos** (temperaturas)
- **Análisis de FFB y Suspensión**

Después de la carrera verás el análisis detallado.

## 🔧 Requisitos

- Python 3.10+
- Assetto Corsa (Steam)
- Navegador web moderno

## 🗂️ Estructura del Proyecto

```
AssetoCorsa/
├── backend/
│   ├── core/                # Configuración y Logging
│   ├── database/            # Base de datos
│   ├── domain/              # Lógica de Negocio
│   │   ├── telemetry/       # Lectura de datos y FFB
│   │   └── analysis/        # Motor de IA
│   ├── api/                 # WebSocket y API
│   └── main.py              # Punto de entrada
├── frontend/
│   ├── index.html           # Dashboard
│   ├── styles.css           # Estilos
│   ├── app.js               # Lógica
│   └── charts.js            # Gráficos
├── data/
│   └── assetto_corsa.db     # Base de datos SQLite
├── .env                     # Configuración
└── asseto/                  # Ambiente virtual
```

## 📄 Licencia

Uso personal libre.
