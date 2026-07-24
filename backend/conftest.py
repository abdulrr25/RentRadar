import os
import sys
from pathlib import Path

# main.py's modules (parser, db, alerts_store, ...) use plain top-level imports
# (e.g. "from parser import parse_query"), matching how uvicorn runs this app
# with backend/ as the working directory. Make that true for pytest too,
# regardless of where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent))

# main.py calls sentry_sdk.init() at import time if SENTRY_DSN is set — which
# it is, in the local .env used for real dev/deploy. Without this, every local
# test run would silently send real events to the (free-tier, quota-limited)
# GlitchTip project. Set it (not pop it) to an empty string BEFORE any test
# module imports main: main.py's load_dotenv() calls default to override=False,
# so they only fill in keys that don't already exist in os.environ — popping
# would leave the key absent and let load_dotenv() re-populate it from .env.
os.environ["SENTRY_DSN"] = ""
