# token_cache.py
from time import time

_cache = {}

def get_token(service):
    data = _cache.get(service)
    if not data or data["expires_at"] <= time():
        return None
    return data["token"]

def set_token(service, token, ttl_secs):
    _cache[service] = {
        "token": token,
        "expires_at": time() + ttl_secs - 60  # buffer to avoid expiry
    }
