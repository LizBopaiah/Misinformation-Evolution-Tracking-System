import re
from datetime import datetime, timezone

def format_timestamp(dt):
    """Safely format standard datetime objects into ISO format strings"""
    if not dt:
        return None
    if dt.tzinfo is None:
        # Assume UTC if timezone is naive
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def validate_email(email):
    """Simple regex evaluation of email format validity"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def parse_iso_datetime(iso_str):
    """Safely parse standard ISO datetime strings"""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        return None
