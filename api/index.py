"""Vercel serverless entrypoint.

Vercel's Python runtime imports this module and looks for a module-level
``app`` that speaks WSGI, so this is a thin wrapper around the same
``config.wsgi`` application used by gunicorn or runserver. The project root
is put on ``sys.path`` explicitly because the function is imported as
``api/index.py`` rather than from the repository root.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402

app = application
