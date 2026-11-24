"""
Translator — translates non-English text to English using Google Translate.
Supports Marathi (mr), Hindi (hi), and English (en).
"""
from deep_translator import GoogleTranslator

# Supported language codes
SUPPORTED_LANGUAGES = {
    "en": "english",
    "hi": "hindi",
    "mr": "marathi",
}


def translate_to_english(text: str, source_lang: str = "en") -> tuple[str, str]:
    """
    Translate text to English if it's not already in English.
    If source_lang is 'en' but text contains non-ASCII, it attempts auto-detection.
    """
    if not text or not text.strip():
        return text, source_lang

    # Check if text is likely English (only ASCII)
    is_pure_ascii = all(ord(c) < 128 for c in text)

    # If English selected and pure ASCII, no translation needed
    if source_lang == "en" and is_pure_ascii:
        return text, "en"

    # If it's not ASCII but 'en' was selected, try 'auto'
    current_source = source_lang if source_lang != "en" else "auto"

    try:
        translator = GoogleTranslator(source=current_source, target="en")
        translated = translator.translate(text)
        
        # Determine actual source if we used auto
        detected_lang = current_source
        if current_source == "auto":
            # deep-translator doesn't easily return detected lang without extra calls,
            # but we can log that we translated it.
            detected_lang = "detected"

        print(f"[Translator] {detected_lang.title()}: '{text}'")
        print(f"[Translator] English Result: '{translated}'")
        return translated, detected_lang
    except Exception as e:
        print(f"[Translator] Translation failed: {e}")
        return text, source_lang
