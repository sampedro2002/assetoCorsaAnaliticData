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
start.bat
```

Esto iniciará el servidor web en el puerto 8080 y abrirá automáticamente tu navegador predeterminado.

### 2. Iniciar Assetto Corsa

Inicia el juego y comienza una carrera. El sistema detectará automáticamente cuando estés en pista.

### 3. Ver Telemetría

El navegador mostrará:
- **Velocidad y RPM**
- **Marcha actual**
- **G-Forces** (lateral y longitudinal)
- **Tiempos de vuelta** (actual, última, mejor, delta)
- **Inputs del piloto** (throttle, brake, steering)
- **Combustible**
- **Neumáticos** (temperaturas y presiones)
- **Frenos** (temperaturas)

Después de la carrera verás el análisis detallado.

## 🔧 Requisitos

- Python 3.10+
- Assetto Corsa (Steam)
- Navegador web moderno

## 🛠️ Solución de Problemas

### El navegador no abre
- Abre manualmente `http://localhost:8080` en tu navegador.

### Error "Ambiente virtual no encontrado"
- Ejecuta `install.bat` en la carpeta `auto`.

### Configuración
El sistema leerá la ruta de instalación de Assetto Corsa desde el archivo `.env`. Si necesitas cambiarla, edita la variable `AC_INSTALL_PATH` en ese archivo.

## 🗂️ Estructura del Proyecto

```
AssetoCorsa/
├── start.bat                # Script de inicio
├── backend/
│   ├── main.py              # Aplicación principal
│   ├── config.py            # Configuración
│   ├── telemetry_reader.py  # Lector de memoria compartida
│   ├── database.py          # Gestor SQLite
│   ├── data_analyzer.py     # Motor de análisis IA
│   └── websocket_server.py  # Servidor FastAPI
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
