from __future__ import annotations

import re

BUSINESS_SUFFIXES = [
    "L.L.C.", "LLC", "INCORPORATED", "INC.", "INC", "P.L.L.C.", "PLLC",
    "CORPORATION", "CORP.", "CORP", "COMPANY", "CO.", "CO", "LTD.", "LTD",
    "LIMITED", "LP", "L.P.", "LLP", "L.L.P.", "PC", "P.C."
]

BUSINESS_HINT_WORDS = {
    "ACADEMY", "ART", "ARTS", "AUTO", "BAR", "BEAUTY", "BOUTIQUE", "CAFE",
    "CARE", "CLEAN", "CLEANING", "CLIMATE", "COFFEE", "CONSULTING", "CONTRACTOR",
    "CONTRACTORS", "CONTROL", "DENTAL", "DESIGN", "DESIGNS", "DETAILING", "DIGITAL",
    "ELECTRIC", "ENTERPRISES", "FLOORING", "FOOD", "GARDEN", "GRAVY", "HEALTH",
    "HOLDINGS", "HOME", "HOMES", "IMPRESSION", "IMPROVEMENTS", "INTERESTS",
    "JANITORIAL", "KOOKIES", "LAB", "LANDSCAPING", "LAWN", "LEDGER", "LOUNGE",
    "MAGIC", "MARKET", "MECHANICAL", "MEDICAL", "MUSIC", "NAIL", "PAINTING",
    "PARLOUR", "PHOTOGRAPHY", "PLUMBING", "PRESS", "PROPERTIES", "PROPERTY",
    "REMODELING", "REPAIR", "RESTAURANT", "RESTORATION", "SALON", "SERVICES",
    "SHOP", "SOLUTIONS", "STEAKS", "STUDIO", "SUP", "THERAPY", "TOUCH",
    "TRANSPORTATION", "TRUCKING", "WINE", "DECKS", "PATHS", "LIVING", "CUP",
    "CRANE", "INTENSIVE", "SPECIALTY", "NICE", "GUYS", "SLICED",
    "COLLABORATING", "FORGE", "KINETIC", "SOCIAL", "VOYAGE", "BARTENDERS"
}

PERSON_NAME_TOKENS = {
    "AKLIN", "JAMARA", "CARTAGENA", "CHARLENE", "FEE", "ROY", "KENNETH",
    "GILLIAM", "KIMSLEY", "TODD", "GOLDSMITH", "JOSEPH", "GRIFFIN",
    "MICHAEL", "HASAN", "SALAAM", "INGRAM", "MARVIN", "JACKSON", "AUDREY",
    "MARIE", "ERICA", "LANDRUM", "CHRISTY", "LASHLEY", "ANITA", "MCSHARRY",
    "JOANNA", "PATTERSON", "JENNIFER", "PRATT", "JESSICA", "RUSSELL",
    "CARLOS", "SHEENE", "BRUCE", "SKINNER", "LE'TIA", "LETIA", "TAYLOR",
    "SHADERICK", "TEMPLE", "KYNGSTON"
}

CATEGORY_SKIP_PATTERNS = [
    r"^\d+\)\s+23-",
    r"^23-\d{3}-\d{3}",
    r"REPAIR, PERSONAL",
    r"RETAIL SALES",
    r"PROFESSIONAL SERVICE",
    r"CONTRACTOR",
    r"TAG",
    r"CERTIFICATION",
    r"CLASSIFICATION OR OWNERSHIP",
    r"DETERMINED NOR VERIFIED",
    r"PENDING",
    r"PEDDLER",
]

UPPERCASE_TOKENS = {
    "BBQ", "DBA", "DPOR", "HVAC", "LLC", "L.L.C", "L.L.C.", "LLP", "L.L.P", "L.L.P.",
    "PLLC", "P.L.L.C", "P.L.L.C.", "INC", "CO", "PC", "LP", "VA", "USA", "N&R"
}

ADDRESS_ABBREVIATIONS = {
    "APT", "AVE", "BLVD", "CIR", "CT", "DR", "LN", "PKWY", "PL", "RD", "STE", "ST",
    "TER", "TRL", "WAY", "UNIT", "PO", "BOX", "NW", "NE", "SW", "SE", "N", "S", "E", "W"
}

ROMAN_NUMERALS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}


def normalize_spacing(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_address(value: str) -> str:
    value = normalize_spacing(value)
    value = value.replace(" ,", ",")
    value = re.sub(r",\s*,", ",", value)
    return value.strip(" ,")


def clean_business_name(name: str) -> str:
    name = normalize_spacing(name)
    name = name.replace("’", "'")
    name = re.sub(r"\s+#\s*\d+\s*$", "", name)

    for suffix in BUSINESS_SUFFIXES:
        pattern = rf"(?:,\s*)?\b{re.escape(suffix)}\b\.?\s*$"
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    name = re.sub(r"\s+", " ", name)
    return title_case_business_name(name.strip(" ,.-"))


def is_category_or_filler(line: str) -> bool:
    upper = line.upper()
    return any(re.search(pattern, upper) for pattern in CATEGORY_SKIP_PATTERNS)


def has_business_hint(name: str) -> bool:
    words = {re.sub(r"[^A-Z0-9']", "", w.upper()) for w in name.split()}
    return bool(words & BUSINESS_HINT_WORDS)


def looks_like_person_name(name: str) -> bool:
    cleaned = clean_business_name(name)
    upper = cleaned.upper()

    if has_business_hint(upper):
        return False

    words = [w for w in re.split(r"\s+", upper) if w]
    alpha_words = [re.sub(r"[^A-Z']", "", w) for w in words]
    alpha_words = [w for w in alpha_words if w]

    if len(alpha_words) < 2 or len(alpha_words) > 3:
        return False

    if all(re.match(r"^[A-Z']+$", w) for w in alpha_words) and any(w in PERSON_NAME_TOKENS for w in alpha_words):
        return True

    return False


def title_case_business_name(value: str) -> str:
    return _smart_title(value, mode="business")


def title_case_address(value: str) -> str:
    value = normalize_spacing(value)
    value = re.sub(r"\bP\s+O\s+BOX\b", "PO Box", value, flags=re.IGNORECASE)
    return _smart_title(value, mode="address")


def title_case_city(value: str) -> str:
    return _smart_title(value, mode="city")


def normalize_state(value: str) -> str:
    return (value or "VA").strip().upper() or "VA"


def _smart_title(value: str, mode: str) -> str:
    value = normalize_spacing(value)
    if not value:
        return ""

    pieces = re.split(r"(\s+|,\s*|-|/|&)", value)
    fixed: list[str] = []
    for piece in pieces:
        if piece == "":
            continue
        if re.fullmatch(r"\s+|,\s*|-|/|&", piece):
            fixed.append(piece)
            continue
        fixed.append(_smart_title_token(piece, mode))

    result = "".join(fixed)
    result = re.sub(r"\s+,", ",", result)
    result = re.sub(r",\s*", ", ", result)
    return result.strip()


def _smart_title_token(token: str, mode: str) -> str:
    raw = token.strip()
    if not raw:
        return raw

    stripped = raw.strip(".,;:()[]{}")
    leading = raw[: len(raw) - len(raw.lstrip(".,;:()[]{}"))]
    trailing = raw[len(raw.rstrip(".,;:()[]{}")) :]
    core = raw[len(leading) : len(raw) - len(trailing) if trailing else len(raw)]
    upper = core.upper()

    if not core:
        return raw
    if upper in UPPERCASE_TOKENS or upper in ROMAN_NUMERALS:
        return leading + upper + trailing
    if mode == "address" and upper in ADDRESS_ABBREVIATIONS:
        return leading + _address_abbrev_case(upper) + trailing
    if re.fullmatch(r"\d+[A-Z]{1,3}", upper):
        return leading + upper + trailing
    if re.fullmatch(r"\d+(ST|ND|RD|TH)", upper):
        return leading + upper.lower() + trailing
    if "'" in core:
        parts = core.split("'")
        titled_parts = [_cap_word(parts[0])]
        for part in parts[1:]:
            if part.lower() in {"s", "t", "re", "ve", "d", "ll", "m"}:
                titled_parts.append(part.lower())
            else:
                titled_parts.append(_cap_word(part))
        return leading + "'".join(titled_parts) + trailing
    return leading + _cap_word(core) + trailing


def _cap_word(word: str) -> str:
    if not word:
        return word
    return word[:1].upper() + word[1:].lower()


def _address_abbrev_case(upper: str) -> str:
    mapping = {
        "APT": "Apt", "AVE": "Ave", "BLVD": "Blvd", "CIR": "Cir", "CT": "Ct", "DR": "Dr",
        "LN": "Ln", "PKWY": "Pkwy", "PL": "Pl", "RD": "Rd", "STE": "Ste", "ST": "St",
        "TER": "Ter", "TRL": "Trl", "WAY": "Way", "UNIT": "Unit", "PO": "PO", "BOX": "Box",
        "N": "N", "S": "S", "E": "E", "W": "W", "NW": "NW", "NE": "NE", "SW": "SW", "SE": "SE",
    }
    return mapping.get(upper, _cap_word(upper))
