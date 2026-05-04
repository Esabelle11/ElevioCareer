"""Map user-facing location strings to Indeed / JobStreet regional sites."""


def _norm(s: str) -> str:
    return s.lower().strip()


def is_singapore_location(location: str) -> bool:
    n = _norm(location)
    return n.startswith("singapore") or "singapore" in n


def indeed_site_base(location: str) -> str:
    return "https://sg.indeed.com" if is_singapore_location(location) else "https://malaysia.indeed.com"


def jobstreet_search_base(location: str) -> str:
    """Base origin for JobStreet list + job pages (MY vs SG)."""
    return "https://sg.jobstreet.com" if is_singapore_location(location) else "https://my.jobstreet.com"
