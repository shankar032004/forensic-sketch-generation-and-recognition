"""
Prompt Builder — constructs structured forensic sketch prompts.
"""

# ── Default forensic prefix & suffix ──────────────────────────────────
_PREFIX = (
    "Forensic police composite sketch, front facing, head and shoulders shot, "
    "centered, neutral expression, high detail, black and white pencil sketch, "
    "criminal investigation drawing"
)

_NEGATIVE_PROMPT = (
    "color, cartoon, anime, blurry, smiling, extra face, distorted, "
    "watermark, text, low quality, deformed, ugly, duplicate, "
    "cropped, out of frame, head cut off, top of head missing"
)


def build_forensic_prompt(attributes: dict) -> str:
    """
    Build a full forensic prompt from structured attributes.

    Parameters
    ----------
    attributes : dict
        Keys like gender, age, nose, eyes, jaw, hair, lips, skin,
        beard, expression, etc.  Values are descriptive strings.

    Returns
    -------
    str
        A comma-separated prompt string with forensic styling.

    Example
    -------
    >>> build_forensic_prompt({"gender": "male", "age": "30", "nose": "long sharp"})
    'Forensic police composite sketch, ... male, age 30, long sharp nose, ...'
    """
    parts: list[str] = [_PREFIX]

    # ── Map attribute keys to natural-language fragments ──────────────
    key_templates = {
        "gender":       "{value}",
        "age":          "age {value}",
        "eyes":         "{value} eyes",
        "nose":         "{value} nose",
        "lips":         "{value} lips",
        "jaw":          "{value} jawline",
        "hair":         "{value} hair",
        "skin":         "{value} skin tone",
        "beard":        "{value} beard",
        "mustache":     "{value} mustache",
        "eyebrows":     "{value} eyebrows",
        "forehead":     "{value} forehead",
        "face_shape":   "{value} face shape",
        "expression":   "{value} expression",
        "scars":        "{value}",
        "accessories":  "wearing {value}",
    }

    for key, value in attributes.items():
        if not value or str(value).strip() == "":
            continue
        value = str(value).strip()
        template = key_templates.get(key, "{value}")
        parts.append(template.replace("{value}", value))

    return ", ".join(parts)


def build_natural_prompt(description: str) -> str:
    """
    Build a forensic prompt using the full natural language description.
    Emphasizes gender if detected to avoid model bias issues.
    """
    if not description:
        return _PREFIX
    
    desc_lower = description.lower().strip()
    
    # Simple gender re-ordering to ensure it's at the front of the description part
    # which gives it more weight in SD 1.5
    if "male" in desc_lower and "female" not in desc_lower:
        # Ensure 'male' is at the start if not already
        if not desc_lower.startswith("male"):
            description = f"male, {description}"
    elif "female" in desc_lower:
        if not desc_lower.startswith("female"):
            description = f"female, {description}"
            
    return f"{_PREFIX}, {description.strip()}"


def get_negative_prompt() -> str:
    """Return the default negative prompt."""
    return _NEGATIVE_PROMPT


# ── Readable region labels for prompt construction ────────────────────
_REGION_LABELS = {
    "hair": "hair",
    "eyes": "eyes",
    "left_eye": "left eye",
    "right_eye": "right eye",
    "nose": "nose",
    "mouth": "mouth",
    "jaw": "jaw",
    "forehead": "forehead",
    "eyebrows": "eyebrows",
}


def build_inpainting_prompt(region: str, modification: str) -> str:
    """
    Build a prompt for inpainting a specific face region.
    The prompt focuses on describing what should fill the masked area,
    with emphatic detail to ensure the model follows through.

    If the modification text does not already mention the region,
    the region name is appended so the model knows what to change.
    e.g. region="hair", modification="curly" → "curly hair"
    """
    mod_lower = modification.lower().strip()
    region_label = _REGION_LABELS.get(region, region)

    # If the user's modification doesn't already mention the region(s),
    # append the region name so the prompt is explicit.
    if region_label not in mod_lower:
        modification = f"{modification.strip()} {region_label}"

    # Amplify the modification with region-specific detail
    _REGION_AMPLIFIERS = {
        "hair": "detailed hair strands, realistic hair texture",
        "eyes": "detailed realistic eyes, expressive",
        "left_eye": "detailed realistic eye, expressive",
        "right_eye": "detailed realistic eye, expressive",
        "nose": "detailed realistic nose, well-defined",
        "mouth": "detailed realistic mouth, well-defined lips",
        "jaw": "detailed jawline, well-defined bone structure",
        "forehead": "detailed forehead, realistic skin texture",
    }

    # If multiple regions, combine amplifiers
    amps = []
    for r in region.split(","):
        r = r.strip()
        if r in _REGION_AMPLIFIERS:
            amps.append(_REGION_AMPLIFIERS[r])
    
    amplifier = ", ".join(amps) if amps else "detailed, realistic"

    return (
        f"{modification}, {amplifier}, "
        f"forensic pencil sketch, high detail, black and white, "
        f"professional police composite sketch"
    )


# ── Auto-detect region from user text ─────────────────────────────────

_REGION_KEYWORDS = {
    "hair":     ["hair", "hairs", "hairstyle", "bald", "curly hair", "straight hair",
                 "long hair", "short hair", "afro", "ponytail", "bangs",
                 "curly", "wavy", "frizzy", "braided", "spiky", "messy",
                 "slicked", "mohawk", "bob cut", "buzz cut", "dreadlocks",
                 "receding", "thinning", "thick hair", "parted"],
    "eyes":     ["eye", "eyes", "eyelash", "eyelid", "pupils"],
    "left_eye": ["left eye"],
    "right_eye":["right eye"],
    "nose":     ["nose", "nostril", "nostrils", "bridge of nose"],
    "mouth":    ["mouth", "lips", "lip", "teeth", "smile"],
    "jaw":      ["jaw", "jawline", "chin", "mandible"],
    "forehead": ["forehead", "brow", "wrinkles on forehead"],
    "eyebrows": ["eyebrow", "eyebrows", "brow", "brows"],
}


def auto_detect_regions(modification: str) -> list[str]:
    """
    Detect all likely face regions from the user's modification text.

    Returns a list of region names detected.
    """
    mod_lower = modification.lower().strip()
    detected = set()

    for region, keywords in _REGION_KEYWORDS.items():
        for kw in keywords:
            if kw in mod_lower:
                detected.add(region)
                break

    return list(detected)
