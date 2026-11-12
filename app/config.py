import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./uptime.db")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
CHECK_TIMEOUT = float(os.getenv("CHECK_TIMEOUT", "10"))
USER_AGENT = "uptime-monitor/1.0 (+https://github.com/JakubOsuch00/uptime-monitor)"
WORKER_METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "9100"))

# "name=url,name2=url2" - added on startup if they don't exist yet
DEFAULT_TARGETS = os.getenv("DEFAULT_TARGETS", "")
