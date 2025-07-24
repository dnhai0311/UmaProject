import sys, pathlib
from pathlib import Path

def get_base_dir():
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]

def get_data_dir():
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else get_base_dir()
    external = base / "data"
    if external.exists():
        return external
    internal = Path(get_base_dir()) / "data"
    return internal 