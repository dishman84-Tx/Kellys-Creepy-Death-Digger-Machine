import json
import os
from utils.logger import logger

SETTINGS_FILE = os.path.join(os.getenv("APPDATA"), "KellysCreepyDeathDiggerMachine", "settings.json")

DEFAULT_SETTINGS = {
    "default_export_dir": os.path.join(os.path.expanduser("~"), "Documents"),
    "request_delay": 2,
    "enabled_sources": [
        "Legacy.com", "SSDI (FamilySearch)", "FindAGrave", "Google News"
    ]
}

def load_settings():
    """Loads settings from disk or returns defaults."""
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_SETTINGS, **settings}
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    """Saves settings to disk."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
