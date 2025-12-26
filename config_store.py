import os
import json

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rodop_run_config.json")


def _load_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_executable(path: str):
    cfg = _load_config()
    cfg["rodeo_executable"] = path
    _save_config(cfg)


def load_executable() -> str:
    cfg = _load_config()
    return cfg.get("rodeo_executable", "").strip()
