"""Keyword-based classification: guess the complaint category from its text.

This is a simple rule system, not AI. Each category has a list of keywords.
We count how many keywords of each category appear in the complaint and
pick the category with the most matches.
"""

import re

from app.constants import TEAM_IT, TEAM_MAINTENANCE

DEFAULT_CATEGORY = "Other"

# Order matters only for ties: the category listed first wins.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Network/Wi-Fi": [
        "wifi", "wi-fi", "wi fi", "internet", "network", "lan", "router",
        "ethernet", "connectivity", "bandwidth", "hotspot",
    ],
    "Projector": ["projector", "hdmi", "vga", "beamer", "projection"],
    "Lab Computer": [
        "computer", "pc", "desktop", "monitor", "keyboard", "mouse",
        "cpu", "software", "workstation",
    ],
    "Printer": [
        "printer", "printing", "print", "toner", "cartridge", "scanner",
        "photocopier", "xerox",
    ],
    "Classroom Equipment": [
        "smart board", "smartboard", "whiteboard", "speaker", "microphone",
        "mic", "podium", "sound system", "audio",
    ],
    "Electrical": [
        "ac", "air conditioner", "air conditioning", "fan", "light", "bulb",
        "tube light", "tubelight", "power", "socket", "switch", "electricity",
        "electric", "wiring", "plug", "voltage",
    ],
    "General Maintenance": [
        "door", "window", "chair", "desk", "bench", "table", "leak", "leaking",
        "water", "tap", "toilet", "washroom", "restroom", "ceiling", "wall",
        "paint", "lock", "cleaning", "dirty", "pipe", "furniture", "glass",
    ],
}

# Which team fixes which category
CATEGORY_TO_TEAM: dict[str, str] = {
    "Network/Wi-Fi": TEAM_IT,
    "Projector": TEAM_IT,
    "Lab Computer": TEAM_IT,
    "Printer": TEAM_IT,
    "Classroom Equipment": TEAM_IT,
    "Electrical": TEAM_MAINTENANCE,
    "General Maintenance": TEAM_MAINTENANCE,
    "Other": TEAM_MAINTENANCE,
}


def contains_keyword(text: str, keyword: str) -> bool:
    """Check if a keyword appears in the text as a whole word (an optional plural 's' is allowed).

    Whole-word matching stops 'ac' from matching inside 'access' or 'lan' inside 'plan'.
    """
    pattern = r"\b" + re.escape(keyword.lower()) + r"s?\b"
    return re.search(pattern, text.lower()) is not None


def count_keyword_matches(text: str, keywords: list[str]) -> int:
    """Count how many different keywords from the list appear in the text."""
    return sum(1 for keyword in keywords if contains_keyword(text, keyword))


def classify_complaint(title: str, description: str) -> str:
    """Return the best matching category for a complaint, or 'Other' if nothing matches."""
    complaint_text = f"{title} {description}"
    best_category = DEFAULT_CATEGORY
    best_match_count = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        match_count = count_keyword_matches(complaint_text, keywords)
        if match_count > best_match_count:
            best_category = category
            best_match_count = match_count

    return best_category


def get_team_for_category(category: str) -> str:
    """Return the team (IT or Maintenance) responsible for a category."""
    return CATEGORY_TO_TEAM.get(category, TEAM_MAINTENANCE)
