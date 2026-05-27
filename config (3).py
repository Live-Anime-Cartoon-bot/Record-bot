import os

# Load .env file if present (local development only)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

def _require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            f"Add it to your .env file or Replit Secrets."
        )
    return val

API_ID    = int(_require("API_ID"))
API_HASH  = _require("API_HASH")
BOT_TOKEN = _require("BOT_TOKEN")

AUTH_USERS = list(map(int, os.environ.get("AUTH_USERS", "").split())) if os.environ.get("AUTH_USERS") else []
OWNER_ID   = list(map(int, os.environ.get("OWNER_IDS",  "").split())) if os.environ.get("OWNER_IDS")  else []

DOWNLOAD_DIRECTORY = os.environ.get("DOWNLOAD_DIRECTORY", "./downloads")
DEFAULT_METADATA   = os.environ.get("DEFAULT_METADATA",   "")
DEFAULT_FILENAME   = os.environ.get("DEFAULT_FILENAME",   "LS")
TIMEZONE           = os.environ.get("TIMEZONE",           "Asia/Kolkata")
CHANNEL_NAME       = os.environ.get("CHANNEL_NAME",       "@LittleSinghamChannel")
