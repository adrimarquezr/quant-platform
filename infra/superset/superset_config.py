import os

# -----------------------------------------------------------------------------
# Superset Configuration
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change_me_superset_secret")

# Database URI for Superset metadata storage
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_DATABASE_URI",
    "sqlite:////app/superset_home/superset.db",
)

# Allow cross-origin requests & iframe embedding if necessary
WTF_CSRF_ENABLED = False
TALISMAN_ENABLED = False

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ALERT_REPORTS": False,
}

# Webserver settings
SUPERSET_WEBSERVER_TIMEOUT = 120
ROW_LIMIT = 50000
