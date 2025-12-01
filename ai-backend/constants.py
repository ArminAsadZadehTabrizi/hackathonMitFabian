"""
Shared constants for the AI Backend.
Centralizes all configuration values, mappings, and keywords.
"""

# =============================================================================
# VENDOR → CATEGORY MAPPING
# =============================================================================
VENDOR_CATEGORIES = {
    # Electronics stores
    "Saturn": "Electronics",
    "MediaMarkt": "Electronics",
    
    # Online retail
    "Amazon": "Hardware",
    
    # Travel
    "Deutsche Bahn": "Travel",
    "Lufthansa": "Travel",
    
    # Grocery stores
    "Rewe": "Groceries",
    "Aldi": "Groceries",
    
    # Gas stations
    "Shell": "Fuel",
    "Aral": "Fuel",
    
    # Furniture
    "IKEA": "Office Supplies",
    
    # Restaurants/Bars
    "Pub Express": "Meals",
    "Restaurant": "Meals",
}

# =============================================================================
# CATEGORY TRANSLATIONS (German ↔ English)
# =============================================================================
CATEGORY_TRANSLATIONS = {
    # German → English
    "elektronik": "Electronics",
    "reise": "Travel",
    "reisen": "Travel",
    "essen": "Meals",
    "mahlzeiten": "Meals",
    "büro": "Office Supplies",
    "buero": "Office Supplies",
    "bürobedarf": "Office Supplies",
    "hardware": "Hardware",
    "software": "Software",
    "lebensmittel": "Groceries",
    "einkauf": "Groceries",
    "kraftstoff": "Fuel",
    "tanken": "Fuel",
    "benzin": "Fuel",
    "sprit": "Fuel",
    # English (exact matches)
    "electronics": "Electronics",
    "travel": "Travel",
    "meals": "Meals",
    "office supplies": "Office Supplies",
    "office": "Office Supplies",
    "groceries": "Groceries",
    "fuel": "Fuel",
    "gas": "Fuel",
}

# =============================================================================
# LANGUAGE DETECTION KEYWORDS
# =============================================================================
GERMAN_KEYWORDS = [
    'wie', 'viel', 'zeig', 'alle', 'quittungen', 'ausgaben', 'habe', 'ich',
    'und', 'von', 'für', 'der', 'die', 'das', 'ein', 'eine', 'über', 'unter',
    'euro', 'insgesamt', 'welche', 'wann', 'wo', 'wer', 'warum', 'gib', 'mir',
    'finde', 'suche'
]

ENGLISH_KEYWORDS = [
    'how', 'what', 'which', 'show', 'find', 'spent', 'much', 'many',
    'receipts', 'the', 'did', 'does', 'have', 'has', 'where', 'when',
    'who', 'why', 'total', 'from', 'all'
]

# =============================================================================
# AUDIT DETECTION KEYWORDS
# =============================================================================
SUSPICIOUS_ITEMS = [
    "Beer", "Wine", "Vodka", "Whiskey", "Cigarettes",
    "Tobacco", "Rum", "Champagne", "Gin", "Tequila",
    "Bier", "Wein", "Schnaps", "Zigaretten", "Tabak"
]

AUDIT_KEYWORDS = {
    "duplicate": ['duplicate', 'duplikat', 'doppelt'],
    "suspicious": ['suspicious', 'verdächtig', 'verdaechtig', 'alkohol', 'alcohol', 'tabak', 'tobacco'],
    "missing_vat": ['missing vat', 'fehlende mwst', 'ohne mwst', 'no vat', 'keine mwst'],
    "math_error": ['math error', 'rechenfehler', 'mismatch', 'falsch berechnet'],
    "all_issues": ['problem', 'issue', 'fehler', 'flag', 'audit']
}

# =============================================================================
# DATE FILTER KEYWORDS
# =============================================================================
DATE_KEYWORDS = {
    "week": ['letzte woche', 'letzten woche', 'last week', 'this week'],
    "month": ['letzter monat', 'letzten monat', 'last month', 'this month'],
    "year": ['letztes jahr', 'last year', 'this year']
}

# =============================================================================
# AMOUNT FILTER PATTERNS (Regex)
# =============================================================================
AMOUNT_PATTERNS = {
    "under": r'(?:unter|below|less than)\s+(\d+(?:[.,]\d+)?)',
    "over": r'(?:über|ueber|above|over|more than|greater than)\s+(\d+(?:[.,]\d+)?)',
    "between": r'(?:zwischen|between)\s+(\d+(?:[.,]\d+)?)\s+(?:und|and)\s+(\d+(?:[.,]\d+)?)'
}

# =============================================================================
# OLLAMA LLM SETTINGS
# =============================================================================
LLM_OPTIONS = {
    "temperature": 0.1,
    "num_predict": 1200,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_ctx": 4096
}

VISION_OPTIONS = {
    "temperature": 0.1,
    "num_predict": 2000
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_category_for_vendor(vendor: str) -> str:
    """Returns the correct category for a vendor."""
    return VENDOR_CATEGORIES.get(vendor, "Office Supplies")


def detect_language(text: str) -> str:
    """Detects if text is German or English based on keyword frequency."""
    text_lower = text.lower()
    german_count = sum(1 for word in GERMAN_KEYWORDS if word in text_lower)
    english_count = sum(1 for word in ENGLISH_KEYWORDS if word in text_lower)
    return "en" if english_count > german_count else "de"


def find_category_in_query(query: str) -> str | None:
    """Finds a category keyword in the query and returns the English category name."""
    query_lower = query.lower()
    for keyword, category in CATEGORY_TRANSLATIONS.items():
        if keyword in query_lower:
            return category
    return None

