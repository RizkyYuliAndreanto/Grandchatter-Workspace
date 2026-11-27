"""Text normalization: Indonesian raw text -> TTS-friendly spelled-out text.

Rule order is LAW (see tasks/fase-1-teks/T04-normalizer.md and flows/flow-pipeline.md):
abbreviations with dots first (dot = chunker trap), then currency/phone/time/percent
patterns, then generic numbers, then acronyms. normalize() is pure and idempotent.
"""
import re

from num2words import num2words

# ---------------------------------------------------------------------------
# Word lists
# ---------------------------------------------------------------------------

# Abbreviations with trailing dots MUST be expanded before chunking (dot trap).
ABBREVIATIONS = {
    "dll.": "dan lain-lain",
    "dst.": "dan sebagainya",
    "tsb.": "tersebut",
    "spt.": "seperti",
    "dsb.": "dan sebagainya",
    "Bpk.": "Bapak",
    "Ibu.": "Ibu",
    "Dr.": "Dokter",
    "dr.": "dokter",
    "Prof.": "Profesor",
    "Hlm.": "halaman",
    "No.": "nomor",
    "no.": "nomor",
}

# Standalone (no dot) informal abbreviations.
INFORMAL = {
    "yg": "yang",
    "dgn": "dengan",
    "kpd": "kepada",
    "utk": "untuk",
    "krn": "karena",
    "tsb": "tersebut",
    "pd": "pada",
    "dlm": "dalam",
}

# All-caps tokens read as a word, never spelled out.
ACRONYM_WHITELIST = {
    "TTS", "HRD", "AI", "PT", "CV", "UD",
    "UI", "UGM", "ITB", "PAUD", "TK", "SD", "SMP", "SMA", "SMK",
    "SIM", "ATM", "WIFI", "LCD", "LED", "AC", "KBM", "LDR",
}
# NB: WIB/WITA/WIT deliberately NOT whitelisted — spec says spell per letter.

# English words/names the Indonesian fine-tune mispronounces: rewritten to
# Indonesian-friendly phonetic spelling so the TTS articulates them naturally.
# Word-boundary, case-insensitive, applied BEFORE other rules.
ENGLISH_PRONUNCIATION = {
    "content": "konten",
    "content creator": "konten kreator",
    "creator": "kreator",
    "creative": "kreatif",
    "engagement": "engedjmen",
    "influencer": "influenser",
    "buzzer": "baser",
    "streaming": "striming",
    "livestream": "laifstriming",
    "podcast": "podkes",
    "shortvideo": "short video",
    "shorts": "shorts",
    "reels": "rilss",
    "story": "stori",
    "stories": "storis",
    "update": "apdet",
    "download": "daunlod",
    "upload": "aplod",
    "share": "syer",
    "like": "laik",
    "subscribe": "Sabskraib",
    "newsletter": "niuzleter",
    "deadline": "dedlain",
    "feedback": "fidbek",
    "workshop": "worksyop",
    "webinar": "webinar",
    "meeting": "miding",
    "schedule": "skedyul",
    "target": "target",
    "brand": "bren",
    "branding": "brending",
    "marketing": "marketing",
    "digital": "digital",
    "platform": "platform",
    "developer": "diveloper",
    "freelance": "frilens",
    "freelancer": "frilenser",
    "remote": "rimot",
    "offline": "oflain",
    "online": "onlain",
    "login": "login",
    "checkout": "cekaut",
    "spreading": "spreding",
    "startup": "startap",
    "shift": "syip",
    "overtime": "overtaim",
    "approval": "aprufal",
    "attachments": "atecmen",
    "available": "afeilebel",
    "capacity": "kapasiti",
    "entry level": "entry level",
    "linkedin": "linkdin",
    "jobstreet": "jobstrit",
    "youtube": "yutub",
    "tiktok": "tiktok",
    "instagram": "instagrem",
    "facebook": "fesbuk",
    "whatsapp": "watsap",
    "google": "gugel",
    "zoom": "zum",
    "canva": "kanva",
    "excel": "eksel",
    "word": "werd",
    "powerpoint": "pauerpoin",
    "email": "imel",
    "e-commerce": "e-komerse",
    "ecommerce": "ikomerse",
}

# Vowel disambiguation (KBBI-style respelling) for words the model reads with
# the wrong [e] vowel. é = close-mid [e] (taling), è = open-mid [ɛ], ê = schwa
# [ə] (pepet). Only words with a KNOWN wrong reading go here — an unmarked "e"
# is left alone (the fine-tune already handles most words correctly).
# Respell to plain e-forms the model demonstrably reads correctly.
E_VOWEL_FIXES = {
    # schwa [ə] (pepet) — model tends to read these with taling
    "segar": "sêgar", "telur": "têlur", "lemah": "lêmah",
    "terasa": "têrasa", "gelap": "gêlap", "dekat": "dêkat",
    "berat": "bêrat", "serang": "sêrang", "gegap": "gêgap",
    # close-mid [e] (taling) — model tends to read these with pepet
    "sate": "saté", "kafe": "kafé", "espresso": "espresso",
    # open-mid [ɛ] — model tends to read these with pepet/taling
    "bebek": "bèbèk", "copet": "copèt", "cerita": "cèrita",
    "terbalik": "têrbalik",
}

# ---------------------------------------------------------------------------

_WORD = r"[A-Za-z]"
_THOUSANDS = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{3})+)(?!\d)")          # 50.000 / 1.250.000
_DECIMAL = re.compile(r"(?<![\d.])(\d+),(\d+)(?![\d.])")                    # 3,5 (ID decimal comma)
_DECIMAL_DOT = re.compile(r"(?<![\d.])(\d+)\.(\d+)(?!\d)(?!\.\d)")          # 3.5 when not thousands
_PHONE = re.compile(r"(?<!\d)(\+?62|0)([\s-]?\d){8,13}(?!\d)")              # 08xx, +62xx (>=10 digits)
_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")                       # 14:30
_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")                                 # 3.5% / 3,5%
_YEAR_CTX = re.compile(r"\b(tahun|sejak|pada tahun|sampai tahun|di tahun)\s+(\d{4})\b", re.IGNORECASE)
_INT = re.compile(r"(?<![\d.])(\d{1,9})(?![\d.])")
_CURRENCY_RP = re.compile(r"\bRp\.?\s*(\d{1,3}(?:\.\d{3})+|\d+)\b", re.IGNORECASE)
_CURRENCY_IDR = re.compile(r"\bIDR\s*(\d{1,3}(?:\.\d{3})+|\d+)\b", re.IGNORECASE)
_ACRONYM = re.compile(r"\b([A-Z]{2,})\b")
_LEFTOVER_SYMBOLS = {"#": "", "&": " dan ", "@": " at ", "*": "", "_": " "}

_THOUSANDS_SCALE = [(1_000_000_000, "miliar"), (1_000_000, "juta"), (1_000, "ribu")]


def _int_to_words(n: int) -> str:
    """Integer -> Indonesian words. num2words first, manual fallback for gaps."""
    try:
        return num2words(n, lang="id")
    except (ValueError, NotImplementedError, OverflowError):
        pass
    if n < 0:
        return "minus " + _int_to_words(-n)
    for scale, word in _THOUSANDS_SCALE:
        if n >= scale:
            q, r = divmod(n, scale)
            head = num2words(q, lang="id") if q > 1 else ("se" if scale == 1_000 else num2words(q, lang="id"))
            return f"{head}{word if head.startswith('se') else ' ' + word} {r and _int_to_words(r) or ''}".strip()
    return str(n)  # unreachable for n in range


def _thousands_to_words(digits: str) -> str:
    return _int_to_words(int(digits.replace(".", "")))


def _digits_to_words(digits: str) -> str:
    """Digit sequence -> per-digit reading (for phone/account numbers)."""
    names = {"0": "nol", "1": "satu", "2": "dua", "3": "tiga", "4": "empat",
             "5": "lima", "6": "enam", "7": "tujuh", "8": "delapan", "9": "sembilan"}
    return " ".join(names[d] for d in digits if d.isdigit())


def _country_code_to_words(m: re.Match) -> str:
    """Phone: +62 prefix read as 'enam dua', rest per digit."""
    raw = m.group(0)
    digits = re.sub(r"[\s-]", "", raw)
    if digits.startswith("+62"):
        return "plus enam dua " + _digits_to_words(digits[3:])
    if digits.startswith("62"):
        return "enam dua " + _digits_to_words(digits[2:])
    return _digits_to_words(digits)


def _time_to_words(m: re.Match) -> str:
    # Broadcast/digital style: "14:30" -> "empat belas tiga puluh",
    # "07:05" -> "nol tujuh nol lima" (unambiguous, natural for TTS).
    h, mm = int(m.group(1)), int(m.group(2))
    hour = _int_to_words(h) if h >= 10 else f"nol {_int_to_words(h)}"
    if mm == 0:
        minute = "nol nol"
    elif mm < 10:
        minute = f"nol {_int_to_words(mm)}"
    else:
        minute = _int_to_words(mm)
    return f"{hour} {minute}"


# ---------------------------------------------------------------------------

def _expand_english(text: str) -> str:
    """Rewrite English terms to Indonesian-friendly phonetic spelling so the
    fine-tune articulates them naturally (case preserved-ish: replacement is
    lowercase except where the dict entry capitalizes). Longest keys first so
    multi-word phrases win over single words."""
    for term, pron in sorted(ENGLISH_PRONUNCIATION.items(),
                             key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(term)}\b", pron, text, flags=re.IGNORECASE)
    return text


def _fix_e_vowels(text: str) -> str:
    """KBBI-style é/è/ê respelling for words with a known wrong [e] reading.
    Word-boundary, case-sensitive on the lowercase key only."""
    for w, pron in E_VOWEL_FIXES.items():
        text = re.sub(rf"\b{w}\b", pron, text)
    return text


def _expand_abbreviations(text: str) -> str:
    text = _expand_english(text)
    text = _fix_e_vowels(text)
    for abbr, full in ABBREVIATIONS.items():
        text = re.sub(re.escape(abbr) + r"(?=\s|$|[,;)\"])", full, text)
    informal = {k: v for k, v in INFORMAL.items()}
    for abbr, full in informal.items():
        text = re.sub(rf"\b{abbr}\b(?!\.)", full, text, flags=re.IGNORECASE)
    return text


def _currency(m: re.Match, name: str) -> str:
    return f"{_thousands_to_words(m.group(1))} {name}"


def _expand_percent(m: re.Match) -> str:
    num = m.group(1)
    if "," in num:
        whole, frac = num.split(",")
        return f"{_int_to_words(int(whole))} koma {_digits_to_words(frac)} persen"
    if "." in num and len(num.split(".")[1]) != 3:  # decimal dot, not thousands
        whole, frac = num.split(".")
        return f"{_int_to_words(int(whole))} koma {_digits_to_words(frac)} persen"
    return f"{_int_to_words(int(num))} persen"


def _expand_year_ctx(m: re.Match) -> str:
    return f"{m.group(1)} {_int_to_words(int(m.group(2)))}"


def _expand_generic_int(m: re.Match) -> str:
    return _int_to_words(int(m.group(1)))


def _expand_acronyms(text: str) -> str:
    def repl(m: re.Match) -> str:
        token = m.group(1)
        if token in ACRONYM_WHITELIST:
            return token
        return " ".join(token)
    return _ACRONYM.sub(repl, text)


def _clean_symbols(text: str) -> str:
    for sym, repl in _LEFTOVER_SYMBOLS.items():
        text = text.replace(sym, repl)
    text = text.replace("—", ", ").replace("–", " sampai ")
    return re.sub(r"\s{2,}", " ", text)


def normalize(text: str) -> str:
    """Raw Indonesian text -> spelled-out TTS text. Pure; idempotent for clean text."""
    text = _expand_abbreviations(text)

    # Specific patterns BEFORE generic numbers (order = law).
    text = _CURRENCY_RP.sub(lambda m: _currency(m, "rupiah"), text)
    text = _CURRENCY_IDR.sub(lambda m: _currency(m, "rupiah"), text)
    text = _PHONE.sub(_country_code_to_words, text)
    text = _TIME.sub(_time_to_words, text)
    text = _PCT.sub(_expand_percent, text)
    text = _YEAR_CTX.sub(_expand_year_ctx, text)

    # Thousands before decimal-dot: "50.000" is thousands, "3.5" is decimal.
    text = _THOUSANDS.sub(lambda m: _thousands_to_words(m.group(1)), text)
    text = _DECIMAL_DOT.sub(
        lambda m: f"{_int_to_words(int(m.group(1)))} koma {_digits_to_words(m.group(2))}", text)
    text = _DECIMAL.sub(
        lambda m: f"{_int_to_words(int(m.group(1)))} koma {_digits_to_words(m.group(2))}", text)

    text = _INT.sub(_expand_generic_int, text)

    # Acronyms last among word rules (after abbreviation expansion).
    text = _expand_acronyms(text)
    text = _clean_symbols(text)
    return text.strip()
