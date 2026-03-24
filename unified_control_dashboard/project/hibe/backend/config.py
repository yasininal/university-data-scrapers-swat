"""Configuration and constants for the Grant Dashboard"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/grant_dashboard.db")

# API Configuration
API_V1_PREFIX = "/api/v1"
API_TITLE = "Grant Call Monitoring Dashboard API"

# CORS
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Scraper Configuration
SCRAPER_CONFIG = {
    "eu_funding": {
        "name": "EU Funding & Tenders Portal",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
        "type": "api",
        "enabled": True,
        "timeout": 30,
    },
    "eu_affairs": {
        "name": "AB Bakanlığı Güncel Hibeler",
        "url": "https://www.ab.gov.tr/guncel-hibeler_4.html",
        "type": "html",
        "enabled": True,
        "timeout": 30,
    },
    "yatirima_destek": {
        "name": "Yatırıma Destek Portalı",
        "url": "https://www.yatirimadestek.gov.tr/destek-arama",
        "type": "html",
        "enabled": True,
        "timeout": 30,
    },
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Pagination defaults
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

# ---------------------------------------------------------------------------
# E-posta Bildirim Ayarları
# .env dosyasına veya ortam değişkenlerine ekle:
#   NOTIFY_EMAIL_ENABLED=true
#   NOTIFY_SMTP_HOST=smtp.gmail.com
#   NOTIFY_SMTP_PORT=587
#   NOTIFY_SMTP_USER=kullanici@gmail.com
#   NOTIFY_SMTP_PASSWORD=uygulama_sifresi   (Gmail App Password)
#   NOTIFY_FROM=kullanici@gmail.com
#   NOTIFY_TO=hedef@ornek.com
# ---------------------------------------------------------------------------
NOTIFY_EMAIL_ENABLED: bool = os.getenv("NOTIFY_EMAIL_ENABLED", "false").lower() == "true"
NOTIFY_SMTP_HOST: str = os.getenv("NOTIFY_SMTP_HOST", "smtp.gmail.com")
NOTIFY_SMTP_PORT: int = int(os.getenv("NOTIFY_SMTP_PORT", "587"))
NOTIFY_SMTP_USER: str = os.getenv("NOTIFY_SMTP_USER", "")
NOTIFY_SMTP_PASSWORD: str = os.getenv("NOTIFY_SMTP_PASSWORD", "")
NOTIFY_FROM: str = os.getenv("NOTIFY_FROM", NOTIFY_SMTP_USER)
NOTIFY_TO: str = os.getenv("NOTIFY_TO", "")
