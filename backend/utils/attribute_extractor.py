"""
Attribute Extractor — parse free-text witness descriptions into structured JSON.
Rule-based keyword extraction (no extra ML model needed).
"""
import re


# ── Keyword dictionaries ──────────────────────────────────────────────

_GENDER_KEYWORDS = {
    "male": ["male", "man", "boy", "gentleman", "he", "his"],
    "female": ["female", "woman", "girl", "lady", "she", "her"],
}

_HAIR_KEYWORDS = [
    "bald", "short", "long", "curly", "straight", "wavy", "afro",
    "braided", "ponytail", "buzz cut", "mohawk", "spiky", "slicked back",
    "black hair", "brown hair", "blonde hair", "red hair", "gray hair",
    "white hair",
]

_EYE_KEYWORDS = [
    "small", "big", "large", "narrow", "wide", "deep set", "round",
    "almond", "hooded", "droopy", "close set", "wide set",
]

_NOSE_KEYWORDS = [
    "long", "short", "wide", "narrow", "pointed", "flat", "hooked",
    "button", "roman", "bulbous", "snub", "sharp", "broad", "crooked",
]

_LIP_KEYWORDS = [
    "thin", "thick", "full", "wide", "narrow", "small", "large",
    "heart shaped", "cupid bow",
]

_JAW_KEYWORDS = [
    "sharp", "round", "square", "pointed", "wide", "narrow",
    "strong", "weak", "angular", "soft", "prominent", "chiseled",
]

_SKIN_KEYWORDS = [
    "light", "fair", "dark", "brown", "tan", "pale", "olive",
    "medium", "ebony",
]

_FACIAL_HAIR = [
    "beard", "mustache", "goatee", "stubble", "clean shaven",
    "full beard", "thin mustache", "thick beard", "sideburns",
]


def extract_attributes(text: str) -> dict:
    """
    Extract structured facial attributes from a free-text description.

    Parameters
    ----------
    text : str
        Witness description, e.g.
        "male, about 30 years old, sharp jawline, small eyes, long nose"

    Returns
    -------
    dict
        Structured attributes with keys: gender, age, eyes, nose, lips,
        jaw, hair, skin, beard, face_shape, scars, accessories.
    """
    text_lower = text.lower().strip()
    attrs: dict = {
        "gender": "",
        "age": "",
        "eyes": "",
        "nose": "",
        "lips": "",
        "jaw": "",
        "hair": "",
        "skin": "",
        "beard": "",
        "face_shape": "",
        "scars": "",
        "accessories": "",
    }

    # ── Gender ────────────────────────────────────────────────────────
    for gender, keywords in _GENDER_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            attrs["gender"] = gender
            break

    # ── Age ───────────────────────────────────────────────────────────
    age_match = re.search(r"age\s*(\d{1,3})", text_lower)
    if not age_match:
        age_match = re.search(r"(\d{1,3})\s*(?:years?\s*old|yo|yrs)", text_lower)
    if not age_match:
        age_match = re.search(r"about\s*(\d{1,3})", text_lower)
    if age_match:
        attrs["age"] = age_match.group(1)

    # ── Eyes ──────────────────────────────────────────────────────────
    attrs["eyes"] = _match_keywords(text_lower, _EYE_KEYWORDS)

    # ── Nose ──────────────────────────────────────────────────────────
    attrs["nose"] = _match_keywords(text_lower, _NOSE_KEYWORDS)

    # ── Lips ──────────────────────────────────────────────────────────
    attrs["lips"] = _match_keywords(text_lower, _LIP_KEYWORDS)

    # ── Jaw ───────────────────────────────────────────────────────────
    attrs["jaw"] = _match_keywords(text_lower, _JAW_KEYWORDS)

    # ── Hair ──────────────────────────────────────────────────────────
    attrs["hair"] = _match_keywords(text_lower, _HAIR_KEYWORDS)

    # ── Skin ──────────────────────────────────────────────────────────
    attrs["skin"] = _match_keywords(text_lower, _SKIN_KEYWORDS)

    # ── Facial hair ───────────────────────────────────────────────────
    attrs["beard"] = _match_keywords(text_lower, _FACIAL_HAIR)

    # ── Scars / marks ─────────────────────────────────────────────────
    scar_match = re.search(r"scar\w*\s+(?:on\s+)?(?:the\s+)?([\w\s]+?)(?:,|$)", text_lower)
    if scar_match:
        attrs["scars"] = f"scar on {scar_match.group(1).strip()}"

    # ── Accessories ───────────────────────────────────────────────────
    accessory_words = ["glasses", "earring", "tattoo", "hat", "cap", "bandana", "mask"]
    found = [w for w in accessory_words if w in text_lower]
    if found:
        attrs["accessories"] = ", ".join(found)

    return attrs


def _match_keywords(text: str, keywords: list[str]) -> str:
    """Return space-separated matched keywords found in text."""
    found = [kw for kw in keywords if kw in text]
    return " ".join(found) if found else ""
