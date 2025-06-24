import json


def clean_json_text(raw_text):
    """Remove control characters before JSON decode"""
    clean_json = ''.join(ch for ch in raw_text if ch in ('\n', '\r') or ord(ch) >= 32)
    return json.loads(clean_json)
