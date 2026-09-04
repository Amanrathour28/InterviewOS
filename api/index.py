import os
import sys

# Ensure apps/api is in the Python module search path for Vercel Serverless Functions
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
api_dir = os.path.join(root_dir, "apps", "api")

if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from app.main import app

# Vercel Python runtime detects ASGI `app` directly
__all__ = ["app"]
