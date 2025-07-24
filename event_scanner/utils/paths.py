import sys, pathlib

def get_base_dir():
    return pathlib.Path(sys.executable).parent if getattr(sys, "frozen", False) else pathlib.Path(__file__).resolve().parents[2]

def get_data_dir():
    return get_base_dir() / "data" 