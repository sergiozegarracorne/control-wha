import sys
import os
from pathlib import Path
import configparser

# Base directory for internal assets
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Determine execution directory (where the exe or script is)
if getattr(sys, 'frozen', False):
    EXEC_DIR = Path(sys.executable).parent
else:
    EXEC_DIR = BASE_DIR

print(EXEC_DIR)

# Config Parser
config_file = EXEC_DIR / "config.ini"
ini_config = configparser.ConfigParser()
ini_config.read(config_file)

# Helper to get config safely
def get_config(section, key, default):
    return ini_config.get(section, key, fallback=default)

# User Data Directory (folder) for full browser persistence (Cookies, LocalStorage, IndexedDB)
USER_DATA_DIR = os.path.join(EXEC_DIR, "whatsapp_session")
# Old session file (kept for reference, but we will rely on user_data_dir)
SESSION_FILE = os.path.join(EXEC_DIR, "session.json")

# WhatsApp URL
WHATSAPP_URL = "https://web.whatsapp.com"

# Headless mode
HEADLESS = get_config("General", "HEADLESS", "False").lower() == "true"

# API Port
PORT = int(get_config("General", "PORT", "8000"))

# RUC (Client Identifier)
RUC = get_config("General", "RUC", "10203040500")
# Auth Token
TOKEN = get_config("General", "TOKEN", "no_token")

# Similarity Threshold (0-100). Default 90. 0 = Disabled.
SIMILARITY_THRESHOLD = int(get_config("General", "SIMILARITY_THRESHOLD", "90"))

# Socket URL (Socket Server)
SOCKET_URL = get_config("General", "SOCKET_URL", "http://jsjperu.net:8000")

# Browser Configuration
BROWSER_TYPE = get_config("Browser", "TYPE", "chromium")
BROWSER_CHANNEL = get_config("Browser", "CHANNEL", "chrome")
if BROWSER_CHANNEL == "None" or BROWSER_CHANNEL == "": 
    BROWSER_CHANNEL = None

# Custom Executable Path (e.g., "C:\Program Files\Google\Chrome\Application\chrome.exe")
BROWSER_EXECUTABLE_PATH = get_config("Browser", "EXECUTABLE_PATH", "") 
