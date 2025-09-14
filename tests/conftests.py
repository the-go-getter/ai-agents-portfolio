import os, sys, pathlib

# Put repo root on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force offline mode for tests (no real API calls)
os.environ.setdefault("OPENAI_OFFLINE", "1")
