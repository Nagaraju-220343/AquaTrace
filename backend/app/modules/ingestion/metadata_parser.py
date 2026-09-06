import json
import csv
from typing import Dict, Any, Optional

def parse_metadata(file_bytes: bytes, filename: str) -> Optional[Dict[str, Any]]:
    """
    Parses CSV or JSON metadata file into a generic dictionary.
    Looks for mapped fields: ping_id, timestamp, range_m, side, latitude, longitude, heading.
    """
    ext = filename.split('.')[-1].lower()
    data = {}
    
    try:
        content = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return None # Invalid encoding

    if ext == 'json':
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
    elif ext == 'csv':
        try:
            reader = csv.DictReader(content.splitlines())
            # Just take the first row for now if it exists
            rows = list(reader)
            if rows:
                data = rows[0]
        except Exception:
            return None
    else:
        return None

    # Normalize keys (lowercase, strip whitespace)
    normalized = {k.strip().lower(): v for k, v in data.items() if isinstance(k, str)}
    
    return {
        "ping_id": normalized.get("ping_id"),
        "timestamp": normalized.get("timestamp"),
        "range_m": normalized.get("range_m"),
        "side": normalized.get("side"),
        "latitude": normalized.get("latitude"),
        "longitude": normalized.get("longitude"),
        "heading": normalized.get("heading")
    }
