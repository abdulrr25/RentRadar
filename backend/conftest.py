import sys
from pathlib import Path

# main.py's modules (parser, db, alerts_store, ...) use plain top-level imports
# (e.g. "from parser import parse_query"), matching how uvicorn runs this app
# with backend/ as the working directory. Make that true for pytest too,
# regardless of where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent))
