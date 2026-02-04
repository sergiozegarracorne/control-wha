import os
import sys
import configparser
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Logic to determine EXEC_DIR (same as config.py to ensure consistency)
# We duplicate it here to avoid importing config.py (which would trigger loading values)
if getattr(sys, 'frozen', False):
    EXEC_DIR = Path(sys.executable).parent
else:
    EXEC_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = EXEC_DIR / "config.ini"

DEFAULT_CONFIG = """[General]
HEADLESS = False
PORT = 8000
# RUC (Identificador único para el servidor)
RUC = 00000000000
# URL del Servidor Socket.IO (Node.js)
SOCKET_URL = http://jsjperu.net:8000

[Browser]
# Opciones: chromium, firefox, webkit
TYPE = chromium

# Channel (Only for chromium): chrome, msedge, or leave empty
CHANNEL = chrome

# Custom Executable Path (Overrides CHANNEL if set)
# Example: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe
# EXECUTABLE_PATH = 
EXECUTABLE_PATH =
"""

def create_default_config():
    """Create config.ini with default values if it doesn't exist."""
    print(f"Creando configuración por defecto en: {CONFIG_PATH}")
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG)

def save_ruc(new_ruc):
    """Update RUC in config.ini."""
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    
    if not config.has_section("General"):
        config.add_section("General")
    
    config.set("General", "RUC", new_ruc)
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        config.write(f)

def run_wizard():
    """Check config and run GUI if needed. Returns True if we should proceed."""
    
    # 1. Ensure config exists
    if not CONFIG_PATH.exists():
        create_default_config()

    # 2. Read Config
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    
    # Check current RUC
    try:
        current_ruc = config.get("General", "RUC", fallback="00000000000")
    except:
        current_ruc = "00000000000"

    # If RUC is valid (not default), just proceed
    if current_ruc != "00000000000":
        return

    # 3. Launch GUI
    root = tk.Tk()
    root.title("Configuración Inicial - Control WHA")
    root.geometry("450x450") # Increased height for disclaimer
    
    # Center window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width/2) - (450/2)
    y = (screen_height/2) - (450/2)
    root.geometry('+%d+%d' % (x, y))

    if sys.platform == 'win32':
        root.iconbitmap(default='') 

    lbl_title = tk.Label(root, text="¡Bienvenido!", font=("Arial", 16, "bold"))
    lbl_title.pack(pady=(10, 5))

    lbl_instr = tk.Label(root, text="Ingrese el RUC de su negocio:", font=("Arial", 10))
    lbl_instr.pack(pady=2)

    entry_ruc = tk.Entry(root, font=("Arial", 12), justify='center', width=20)
    entry_ruc.insert(0, "")
    entry_ruc.pack(pady=5)

    # --- DISCLAIMER SECTION ---
    disclaimer_frame = tk.Frame(root, borderwidth=1, relief="solid", padx=10, pady=10)
    disclaimer_frame.pack(fill="x", padx=20, pady=15)

    disclaimer_text = (
        "⚠️ AVISO DE RESPONSABILIDAD (BETA)\n\n"
        "1. Este software es una versión BETA de pruebas.\n"
        "2. NO tenemos ninguna alianza, afiliación ni contrato con WhatsApp ni Meta Platforms, Inc.\n"
        "3. El usuario asume toda la responsabilidad por el uso de esta herramienta.\n"
        "4. No nos hacemos responsables por bloqueos temporales o definitivos de su número telefónico por parte de WhatsApp.\n"
        "5. Úselo con precaución y evite el SPAM masivo."
    )

    lbl_disclaimer = tk.Message(disclaimer_frame, text=disclaimer_text, font=("Arial", 8), width=380, justify="left", fg="#D8000C")
    lbl_disclaimer.pack()

    # --- CHECKBOX ---
    chk_var = tk.IntVar()
    
    def toggle_button():
        if chk_var.get() == 1:
            btn_save.config(state="normal", bg="#25D366")
        else:
            btn_save.config(state="disabled", bg="#cccccc")

    chk_agree = tk.Checkbutton(root, text="He leído y acepto los riesgos y condiciones.", variable=chk_var, command=toggle_button, font=("Arial", 9, "bold"))
    chk_agree.pack(pady=5)

    # --- SAVE BUTTON ---
    def on_save():
        val = entry_ruc.get().strip()
        if not val or val == "00000000000" or len(val) < 8:
            messagebox.showerror("Error", "Por favor ingresa un RUC válido.")
            return
        
        save_ruc(val)
        messagebox.showinfo("Éxito", "Configuración guardada.\nEl sistema se iniciará ahora.")
        root.destroy()

    btn_save = tk.Button(root, text="Registrar y Continuar", command=on_save, bg="#cccccc", fg="white", font=("Arial", 11, "bold"), padx=10, pady=5, state="disabled")
    btn_save.pack(pady=10)

    root.mainloop()
