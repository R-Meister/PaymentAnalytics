import os

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def get(path, params=None):
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()
