"""
Language Detection Module for Multilingual Agricultural AI Assistant.
Supports 11 Indian languages including Hinglish and Maithili detection.
"""

import re
from typing import Optional
from langdetect import detect, detect_langs, LangDetectException


# === Language Configuration ===

SUPPORTED_LANGUAGES = {
    "hi": {"name": "Hindi", "native": "हिन्दी", "tts_code": "hi-IN"},
    "en": {"name": "English", "native": "English", "tts_code": "en-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "tts_code": "bn-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "tts_code": "ta-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "tts_code": "te-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "tts_code": "mr-IN"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "tts_code": "gu-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "tts_code": "kn-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "tts_code": "ml-IN"},
    "hi-en": {"name": "Hinglish", "native": "Hinglish", "tts_code": "hi-IN"},
    "mai": {"name": "Maithili", "native": "मैथिली", "tts_code": "hi-IN"},
}

# Common Hinglish patterns: Hindi words written in English script
HINGLISH_MARKERS = [
    r'\bkya\b', r'\bhai\b', r'\bkaise\b', r'\bkab\b', r'\bkaha\b', r'\bkahan\b',
    r'\bmein\b', r'\bkaro\b', r'\bkarna\b', r'\bbata\b', r'\bbatao\b', r'\bkuch\b',
    r'\baur\b', r'\bya\b', r'\bse\b', r'\bko\b', r'\bka\b', r'\bki\b', r'\bke\b',
    r'\bho\b', r'\bhoga\b', r'\bhoti\b', r'\bhota\b', r'\bchalti\b',
    r'\bkhet\b', r'\bfasal\b', r'\bkheti\b', r'\bbijli\b', r'\bpaani\b', r'\bpani\b',
    r'\bmitti\b', r'\bbeej\b', r'\bkisaan\b', r'\bkisan\b', r'\bgaon\b', r'\bsabji\b',
    r'\bdawa\b', r'\brog\b', r'\bkeet\b', r'\bbimari\b', r'\bsarkar\b', r'\byojana\b',
    r'\bsarkari\b', r'\bmandi\b', r'\bbhav\b', r'\bdaam\b', r'\brupaye\b',
    r'\bnahi\b', r'\bnhi\b', r'\bmat\b', r'\bkoi\b', r'\bsab\b',
    r'\bachha\b', r'\btheek\b', r'\bkaam\b', r'\bchal\b',
    r'\baa\b', r'\bgayi\b', r'\bgaya\b', r'\blaga\b', r'\blagi\b',
]

# Maithili-specific keywords/phrases
MAITHILI_MARKERS = [
    r'\bछी\b', r'\bछै\b', r'\bअछि\b', r'\bछल\b', r'\bहमर\b', r'\bअहां\b',
    r'\bतोहर\b', r'\bकेना\b', r'\bकोना\b', r'\bताहि\b', r'\bसँग\b', r'\bगेलै\b',
    r'\bभेलै\b', r'\bकहलक\b', r'\bदेखलक\b', r'\bनै\b', r'\bहेतै\b',
    r'\bभऽ\b', r'\bजे\b', r'\bसे\b', r'\bएहि\b', r'\bओहि\b',
]

# Devanagari Unicode range for Hindi/Maithili detection
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')
# Tamil Unicode range
TAMIL_PATTERN = re.compile(r'[\u0B80-\u0BFF]')
# Bengali Unicode range
BENGALI_PATTERN = re.compile(r'[\u0980-\u09FF]')
# Telugu Unicode range
TELUGU_PATTERN = re.compile(r'[\u0C00-\u0C7F]')
# Kannada Unicode range
KANNADA_PATTERN = re.compile(r'[\u0C80-\u0CFF]')
# Malayalam Unicode range
MALAYALAM_PATTERN = re.compile(r'[\u0D00-\u0D7F]')
# Gujarati Unicode range
GUJARATI_PATTERN = re.compile(r'[\u0A80-\u0AFF]')


class LanguageDetectionResult:
    """Result of language detection."""

    def __init__(self, language_code: str, language_name: str, confidence: float,
                 is_mixed: bool = False, native_name: str = "", tts_code: str = "hi-IN"):
        self.language_code = language_code
        self.language_name = language_name
        self.confidence = confidence
        self.is_mixed = is_mixed
        self.native_name = native_name
        self.tts_code = tts_code

    def to_dict(self):
        return {
            "language_code": self.language_code,
            "language_name": self.language_name,
            "confidence": round(self.confidence, 2),
            "is_mixed": self.is_mixed,
            "native_name": self.native_name,
            "tts_code": self.tts_code,
        }


def _count_script_chars(text: str, pattern: re.Pattern) -> int:
    """Count characters matching a Unicode script pattern."""
    return len(pattern.findall(text))


def _count_hinglish_markers(text: str) -> int:
    """Count Hinglish marker words in text."""
    text_lower = text.lower()
    count = 0
    for pattern in HINGLISH_MARKERS:
        if re.search(pattern, text_lower):
            count += 1
    return count


def _check_maithili(text: str) -> bool:
    """Check if text contains Maithili-specific markers."""
    for pattern in MAITHILI_MARKERS:
        if re.search(pattern, text):
            return True
    return False


def detect_language(text: str, hint: Optional[str] = None) -> LanguageDetectionResult:
    """
    Detect the language of input text.

    Args:
        text: Input text to detect language for
        hint: Optional language code hint from user

    Returns:
        LanguageDetectionResult with detected language info
    """
    if not text or not text.strip():
        return _build_result("en", 0.5)

    text = text.strip()

    # If user provides a language hint and it's valid, trust it with high confidence
    if hint and hint in SUPPORTED_LANGUAGES:
        return _build_result(hint, 0.95)

    # Step 1: Script-based detection (most reliable for non-Latin scripts)
    total_chars = len(text.replace(" ", ""))

    if total_chars > 0:
        # Check each script
        devanagari_count = _count_script_chars(text, DEVANAGARI_PATTERN)
        tamil_count = _count_script_chars(text, TAMIL_PATTERN)
        bengali_count = _count_script_chars(text, BENGALI_PATTERN)
        telugu_count = _count_script_chars(text, TELUGU_PATTERN)
        kannada_count = _count_script_chars(text, KANNADA_PATTERN)
        malayalam_count = _count_script_chars(text, MALAYALAM_PATTERN)
        gujarati_count = _count_script_chars(text, GUJARATI_PATTERN)

        script_ratios = {
            "devanagari": devanagari_count / total_chars,
            "tamil": tamil_count / total_chars,
            "bengali": bengali_count / total_chars,
            "telugu": telugu_count / total_chars,
            "kannada": kannada_count / total_chars,
            "malayalam": malayalam_count / total_chars,
            "gujarati": gujarati_count / total_chars,
        }

        max_script = max(script_ratios, key=script_ratios.get)
        max_ratio = script_ratios[max_script]

        # If strong script presence (>30%), use script-based detection
        if max_ratio > 0.3:
            if max_script == "devanagari":
                # Could be Hindi, Marathi, or Maithili - need further analysis
                if _check_maithili(text):
                    return _build_result("mai", 0.85)

                # Try langdetect for Hindi vs Marathi
                try:
                    lang_results = detect_langs(text)
                    for result in lang_results:
                        if result.lang == "mr" and result.prob > 0.5:
                            return _build_result("mr", float(result.prob))
                except LangDetectException:
                    pass

                return _build_result("hi", max_ratio)

            elif max_script == "tamil":
                return _build_result("ta", max_ratio)
            elif max_script == "bengali":
                return _build_result("bn", max_ratio)
            elif max_script == "telugu":
                return _build_result("te", max_ratio)
            elif max_script == "kannada":
                return _build_result("kn", max_ratio)
            elif max_script == "malayalam":
                return _build_result("ml", max_ratio)
            elif max_script == "gujarati":
                return _build_result("gu", max_ratio)

    # Step 2: Latin script — check for Hinglish
    hinglish_marker_count = _count_hinglish_markers(text)

    if hinglish_marker_count >= 2:
        # Multiple Hindi words in English script = Hinglish
        confidence = min(0.9, 0.5 + hinglish_marker_count * 0.08)
        return _build_result("hi-en", confidence, is_mixed=True)

    # Step 3: Fall back to langdetect library
    try:
        lang_results = detect_langs(text)
        primary = lang_results[0]

        lang_code = primary.lang
        confidence = float(primary.prob)

        # Map langdetect codes to our supported codes
        lang_map = {
            "hi": "hi", "en": "en", "bn": "bn", "ta": "ta",
            "te": "te", "mr": "mr", "gu": "gu", "kn": "kn",
            "ml": "ml",
        }

        if lang_code in lang_map:
            return _build_result(lang_map[lang_code], confidence)

        # If detected language is not directly supported, check for close matches
        # e.g., langdetect might detect Urdu (ur) for Hindi-like text
        if lang_code == "ur":
            return _build_result("hi", confidence * 0.9)

        # Unsupported language → check if there's a single Hinglish marker
        if hinglish_marker_count >= 1:
            return _build_result("hi-en", 0.6, is_mixed=True)

        # Default to English
        return _build_result("en", 0.5)

    except LangDetectException:
        # langdetect failed — use fallback
        if hinglish_marker_count >= 1:
            return _build_result("hi-en", 0.5, is_mixed=True)
        return _build_result("hi", 0.4)  # Default to Hindi for Indian context


def _build_result(lang_code: str, confidence: float, is_mixed: bool = False) -> LanguageDetectionResult:
    """Build a LanguageDetectionResult from a language code."""
    lang_info = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["en"])
    return LanguageDetectionResult(
        language_code=lang_code,
        language_name=lang_info["name"],
        confidence=confidence,
        is_mixed=is_mixed,
        native_name=lang_info["native"],
        tts_code=lang_info["tts_code"],
    )


def get_response_language_instruction(lang_code: str) -> str:
    """
    Get the language instruction for the LLM prompt based on detected language.
    """
    instructions = {
        "hi": "## MANDATORY: आपको पूरा उत्तर हिन्दी में देना है। एक भी वाक्य अंग्रेजी में मत लिखें। सरल हिन्दी का प्रयोग करें जो किसान आसानी से समझ सकें। RESPOND ENTIRELY IN HINDI.",
        "en": "## MANDATORY: Respond entirely in simple English. Use easy words that farmers can understand.",
        "bn": "## MANDATORY: সম্পূর্ণ বাংলায় উত্তর দিন। ইংরেজি ব্যবহার করবেন না। সহজ ভাষা ব্যবহার করুন। RESPOND ENTIRELY IN BENGALI.",
        "ta": "## MANDATORY: முழுமையாக தமிழில் பதிலளிக்கவும். ஆங்கிலம் பயன்படுத்தாதீர்கள். RESPOND ENTIRELY IN TAMIL.",
        "te": "## MANDATORY: పూర్తిగా తెలుగులో సమాధానం ఇవ్వండి. ఆంగ్లం వాడకండి. RESPOND ENTIRELY IN TELUGU.",
        "mr": "## MANDATORY: संपूर्ण उत्तर मराठीत द्या. इंग्रजी वापरू नका. RESPOND ENTIRELY IN MARATHI.",
        "gu": "## MANDATORY: સંપૂર્ણ જવાબ ગુજરાતીમાં આપો. અંગ્રેજી વાપરશો નહીં. RESPOND ENTIRELY IN GUJARATI.",
        "kn": "## MANDATORY: ಸಂಪೂರ್ಣ ಉತ್ತರವನ್ನು ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ. ಇಂಗ್ಲಿಷ್ ಬಳಸಬೇಡಿ. RESPOND ENTIRELY IN KANNADA.",
        "ml": "## MANDATORY: പൂർണ്ണ ഉത്തരം മലയാളത്തിൽ നൽകുക. ഇംഗ്ലീഷ് ഉപയോഗിക്കരുത്. RESPOND ENTIRELY IN MALAYALAM.",
        "hi-en": "## MANDATORY: Respond in Hinglish — Hindi words written in English letters, naturally mixed with English. "
                 "Example style: 'Gehun ki fasal ke liye sabse pehle kheti ki taiyaari karo. 2-3 baar cultivator se jotai karo.' "
                 "Do NOT use Devanagari script. Write Hindi words in English letters only. RESPOND IN HINGLISH.",
        "mai": "## MANDATORY: उत्तर सरल हिन्दी में दें जिसमें थोड़ी मैथिली मिली हो। किसान भाई आसानी से समझ सकें ऐसी भाषा रखें। RESPOND IN HINDI WITH MAITHILI FLAVOR.",
    }
    return instructions.get(lang_code, instructions["en"])
