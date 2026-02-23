# Guía de Empaquetado del Ejecutable

## Archivos Necesarios para Distribución

Cuando crees el ejecutable con PyInstaller, necesitarás incluir los siguientes archivos y carpetas:

### Archivos Incluidos Automáticamente por PyInstaller

El archivo `AssettoCorsaAnalytic.spec` ya está configurado para incluir:

- ✅ `frontend/` - Toda la interfaz web (HTML, CSS, JS)
- ✅ `backend/` - Todo el código Python del backend
- ✅ `.env` - Configuración de entorno

### Archivos que se Crean Automáticamente

- ✅ `data/` - Se crea automáticamente al ejecutar, contiene la base de datos SQLite

### Comando para Crear el Ejecutable

```bash
build_exe.bat
```

El ejecutable se generará en la carpeta `dist/`.

### Estructura Final para Distribución

```
analisisAsseto.exe          # Ejecutable principal
```

**Nota**: El ejecutable es completamente autocontenido. PyInstaller empaqueta todo lo necesario dentro del `.exe`.

### Requisitos del Usuario Final

El usuario solo necesita:
1. El archivo `.exe`
2. Assetto Corsa instalado
3. Windows

### Primera Ejecución

Al ejecutar por primera vez:
1. Se iniciará el servidor web en segundo plano
2. Se abrirá automáticamente el navegador (Chrome, Edge, Firefox o Brave) en modo incógnito en `http://localhost:8080`
3. Se creará automáticamente la carpeta `data/`

### Solución de Problemas

Si el ejecutable no funciona:
1. Ejecutar desde la terminal para ver errores.
2. Verificar que el antivirus no lo bloquee.
