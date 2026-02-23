import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import json
import webbrowser
from pathlib import Path

# Add the project root to sys.path to import backend
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from backend.main import TelemetrySystem
    from backend.core.config import SERVER_CONFIG, AC_CONFIG
except ImportError:
    # Handle paths when running from bundled EXE
    if hasattr(sys, '_MEIPASS'):
        sys.path.insert(0, sys._MEIPASS)
        from backend.main import TelemetrySystem
        from backend.core.config import SERVER_CONFIG, AC_CONFIG
    else:
        raise

class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Assetto Corsa Telemetry - Panel de Control")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")
        
        self.system = None
        self.server_thread = None
        self.is_running = False
        
        # Logs and Config path
        self.data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "launcher_config.json")
        self.log_file = os.path.join(self.data_dir, "launcher_debug.log")
        
        self.load_settings()
        self.setup_ui()

    def setup_ui(self):
        # Estilo oscuro
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", foreground="white", background="#1e1e1e", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 11, "bold"))

        # Header
        header = tk.Label(self.root, text="Telemetría Assetto Corsa", fg="#00ff00", bg="#1e1e1e", font=("Segoe UI", 18, "bold"))
        header.pack(pady=20)

        # Configuración de Carpeta AC
        ac_frame = tk.Frame(self.root, bg="#1e1e1e")
        ac_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(ac_frame, text="Ruta de Assetto Corsa:", fg="white", bg="#1e1e1e").pack(anchor="w")
        self.ac_path_var = tk.StringVar(value=self.settings.get("ac_path", AC_CONFIG['install_path']))
        
        path_entry_frame = tk.Frame(ac_frame, bg="#1e1e1e")
        path_entry_frame.pack(fill="x", pady=5)
        
        self.path_entry = tk.Entry(path_entry_frame, textvariable=self.ac_path_var, bg="#2d2d2d", fg="white", insertbackground="white", relief="flat")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=3)
        
        tk.Button(path_entry_frame, text="...", command=self.browse_ac_path, bg="#444", fg="white", activebackground="#666", relief="flat", width=3).pack(side="right")

        # Selección de Navegador
        browser_frame = tk.Frame(self.root, bg="#1e1e1e")
        browser_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(browser_frame, text="Navegador (Incógnito):", fg="white", bg="#1e1e1e").pack(anchor="w")
        self.browser_var = tk.StringVar(value=self.settings.get("browser", "Chrome"))
        self.browser_menu = ttk.Combobox(browser_frame, textvariable=self.browser_var, values=["Chrome", "Edge", "Brave", "Firefox", "Por Defecto"], state="readonly")
        self.browser_menu.pack(fill="x", pady=5)

        # Estado y Botón
        self.status_label = tk.Label(self.root, text="ESTADO: Servidor Detenido", fg="#ff4444", bg="#1e1e1e", font=("Segoe UI", 11, "bold"))
        self.status_label.pack(pady=20)

        self.action_btn = tk.Button(self.root, text="INICIAR SERVIDOR", command=self.toggle_server, 
                                  bg="#00aa00", fg="white", font=("Segoe UI", 12, "bold"), 
                                  activebackground="#00cc00", relief="flat", pady=10, width=20)
        self.action_btn.pack(pady=10)

        footer = tk.Label(self.root, text="La aplicación web se abrirá automáticamente", fg="#888", bg="#1e1e1e", font=("Segoe UI", 9))
        footer.pack(side="bottom", pady=10)

    def browse_ac_path(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de Assetto Corsa")
        if path:
            self.ac_path_var.set(path)
            self.save_settings()

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
            except:
                self.settings = {}
        else:
            self.settings = {}

    def save_settings(self):
        self.settings["ac_path"] = self.ac_path_var.get()
        self.settings["browser"] = self.browser_var.get()
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f)

    def toggle_server(self):
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        self.save_settings()
        # Update config in memory
        AC_CONFIG['install_path'] = self.ac_path_var.get()
        os.environ['AC_INSTALL_PATH'] = self.ac_path_var.get()
        
        # Selected browser argument for main.py (implicitly through global config if we wanted, 
        # but better to adapt open_browser_incognito to prioritize the choice)
        selected_browser = self.browser_var.get().lower().replace("por defecto", "default")
        
        try:
            self.system = TelemetrySystem()
            # Modify the system to prioritize our selected browser
            # (In a real scenario, we'd pass this to the constructor or a setter)
            self.system.preferred_browser = selected_browser
            
            self.server_thread = threading.Thread(target=self.run_system, daemon=True)
            self.server_thread.start()
            
            self.is_running = True
            self.status_label.config(text="ESTADO: Servidor Corriendo", fg="#00ff00")
            self.action_btn.config(text="DETENER SERVIDOR", bg="#aa0000", activebackground="#cc0000")
            self.path_entry.config(state="disabled")
            self.browser_menu.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el servidor: {e}")

    def run_system(self):
        try:
            # Redirect stdout/stderr to log file for debugging in background
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- INICIO SERVIDOR: {self.ac_path_var.get()} ---\n")
                sys.stdout = f
                sys.stderr = f
                self.system.run()
        except Exception as e:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"ERROR FATAL: {str(e)}\n")

    def stop_server(self):
        if messagebox.askokcancel("Detener", "¿Estás seguro de que quieres detener el servidor? El ejecutable se cerrará."):
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppLauncher(root)
    root.mainloop()
