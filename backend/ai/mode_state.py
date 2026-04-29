from backend.config import settings

# Initialised from the env-var at import time; overridable at runtime without
# restarting the server. Resets to the env-var value on next restart.
_current_mode: str = "cloud" if settings.cloud_mode else "local"


def get_mode() -> str:
    return _current_mode


def is_cloud() -> bool:
    return _current_mode == "cloud"


def set_mode(mode: str) -> None:
    global _current_mode
    if mode not in ("cloud", "local"):
        raise ValueError(f"Invalid mode: {mode!r}")
    _current_mode = mode
