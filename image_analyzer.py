import os
import re
import shutil
import tempfile

import cv2
import numpy as np
import pytesseract


# ============================================================
# ERRORS
# ============================================================

class OCRNotAvailableError(RuntimeError):
    """Tesseract OCR is not installed / cannot be found."""


class ImageReadError(ValueError):
    """The file is not a readable image."""


# ============================================================
# TESSERACT LOCATION
# ============================================================

def _find_tesseract():
    """
    Looks for tesseract.exe in this order:
      1. TESSERACT_CMD environment variable
      2. the default Windows install folders
      3. anything already on PATH
    """

    candidates = [
        os.environ.get("TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        shutil.which("tesseract")
    ]

    for candidate in candidates:

        if candidate and os.path.isfile(candidate):
            return candidate

    return None


TESSERACT_PATH = _find_tesseract()

if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ============================================================
# TEXT INDICATOR HELPERS
# ============================================================

URL_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s<>\"')\]]+",
    re.IGNORECASE
)

FALLBACK_KEYWORDS = [
    "login",
    "verify",
    "verification",
    "account",
    "secure",
    "security",
    "update",
    "confirm",
    "password",
    "payment",
    "bank",
    "signin",
    "credential"
]

CREDENTIAL_PATTERN = re.compile(
    r"password|passcode|username|\bpin\b|\botp\b|sign[\s-]?in|log[\s-]?in|credential",
    re.IGNORECASE
)

PAYMENT_PATTERN = re.compile(
    r"payment|credit card|debit card|card number|\bcvv\b|bank account|"
    r"account number|\bupi\b|billing|refund",
    re.IGNORECASE
)

URGENT_PATTERN = re.compile(
    r"urgent|immediate|immediately|within 24|suspended|expire|"
    r"final notice|act now|as soon as possible",
    re.IGNORECASE
)


def _as_list(value):

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return []


def _find_urls(text):
    """
    OCR often inserts spaces inside links ("http: // site.com"),
    so those are repaired before searching.
    """

    repaired = re.sub(
        r"(https?)\s*:\s*/\s*/\s*",
        r"\1://",
        text,
        flags=re.IGNORECASE
    )

    found = []

    for match in URL_PATTERN.findall(repaired):

        cleaned = match.rstrip(".,;:!?")

        if cleaned and cleaned not in found:
            found.append(cleaned)

    return found


def _find_keywords(text):

    lowered = text.lower()

    return [
        keyword
        for keyword in FALLBACK_KEYWORDS
        if keyword in lowered
    ]


def _load_email_analyzer():
    """
    Imports the existing email analyzer. Works both when the
    server runs from the backend folder and when this file is
    imported as backend.image_analyzer.
    """

    try:

        from email_analyzer import analyze_email

    except ImportError:

        from backend.email_analyzer import analyze_email

    return analyze_email


# ============================================================
# EXPLAINABLE RISK SCORE (same weights as the live analyzer)
# ============================================================

def calculate_text_risk(
    urls,
    keywords,
    credential_request,
    payment_request,
    urgent_request,
    ml_prediction="unknown"
):

    factors = []

    def add_factor(name, points):

        if points > 0:

            factors.append({
                "factor": name,
                "points": points
            })

    add_factor(
        f"{len(keywords)} suspicious keyword(s)",
        min(len(keywords) * 3, 15)
    )

    add_factor(
        f"{len(urls)} URL(s) found",
        min(len(urls) * 10, 20)
    )

    if credential_request:
        add_factor("Credential request", 15)

    if payment_request:
        add_factor("Payment / financial information request", 15)

    if urgent_request:
        add_factor("Urgent language", 5)

    if ml_prediction == "spam":
        add_factor("ML model flagged text as spam", 5)

    score = min(
        sum(item["points"] for item in factors),
        100
    )

    if score >= 60:

        level = "HIGH"
        classification = "High Risk / Potential Phishing"

    elif score >= 30:

        level = "MEDIUM"
        classification = "Suspicious / Needs Investigation"

    else:

        level = "LOW"
        classification = "Legitimate / Low Risk"

    return {
        "risk_score": score,
        "risk_level": level,
        "classification": classification,
        "risk_factors": factors
    }


# ============================================================
# IMAGE LOADING
# ============================================================

def _load_image(image_path):

    if not os.path.isfile(image_path):

        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    # np.fromfile + imdecode also works for Windows paths that
    # contain spaces or non-English characters.

    data = np.fromfile(
        image_path,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        data,
        cv2.IMREAD_UNCHANGED
    )

    if image is None:

        raise ImageReadError(
            "The file could not be read as an image "
            "(it may be corrupted or not a real image)."
        )

    if image.dtype != np.uint8:

        image = cv2.normalize(
            image,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        ).astype(np.uint8)

    # Transparent PNG: place it on a white background.

    if image.ndim == 3 and image.shape[2] == 4:

        alpha = image[:, :, 3:4].astype(np.float32) / 255.0

        color = image[:, :, :3].astype(np.float32)

        image = (
            color * alpha + 255.0 * (1.0 - alpha)
        ).astype(np.uint8)

    return image


# ============================================================
# PREPROCESSING
# ============================================================

def _preprocess_variants(image):
    """
    Returns a few cleaned-up versions of the image.
    The best-reading one is chosen after OCR.
    """

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    height, width = gray.shape

    # Small screenshots need enlarging; huge ones shrinking.

    if width < 1200:

        scale = min(3.0, 1200.0 / width)

        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    elif width > 3000:

        scale = 3000.0 / width

        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    # Dark-mode screenshots (light text on dark background)
    # are inverted so Tesseract sees dark text on light.

    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)

    blurred = cv2.medianBlur(gray, 3)

    _, otsu = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    adaptive = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15
    )

    return [
        ("grayscale", gray),
        ("otsu-threshold", otsu),
        ("adaptive-threshold", adaptive)
    ]


# ============================================================
# OCR
# ============================================================

def _run_ocr(image_array):
    """
    Returns (text, mean_confidence, confident_word_mass).
    """

    try:

        data = pytesseract.image_to_data(
            image_array,
            config="--oem 3 --psm 3",
            output_type=pytesseract.Output.DICT,
            timeout=60
        )

    except pytesseract.TesseractNotFoundError:

        raise OCRNotAvailableError(
            "Tesseract OCR was not found. Install it from "
            "https://github.com/UB-Mannheim/tesseract/wiki "
            "(default folder: C:\\Program Files\\Tesseract-OCR) "
            "or set the TESSERACT_CMD environment variable."
        )

    lines = {}
    confidences = []

    for index, raw_word in enumerate(data["text"]):

        word = str(raw_word).strip()

        if not word:
            continue

        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0

        if confidence < 0:
            continue

        key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index]
        )

        lines.setdefault(key, []).append(word)

        confidences.append(confidence)

    text = "\n".join(
        " ".join(words)
        for words in lines.values()
    )

    mean_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0.0
    )

    confident_mass = sum(
        value for value in confidences
        if value >= 50
    )

    return text, mean_confidence, confident_mass


def extract_text_from_image(image_path):
    """
    Loads the image, tries several preprocessing methods and
    returns the best OCR result.
    """

    image = _load_image(image_path)

    best = {
        "text": "",
        "confidence": 0.0,
        "method": "none",
        "mass": -1.0
    }

    for method, variant in _preprocess_variants(image):

        text, confidence, mass = _run_ocr(variant)

        if mass > best["mass"]:

            best = {
                "text": text,
                "confidence": confidence,
                "method": method,
                "mass": mass
            }

        # Good enough: stop early to keep the dashboard fast.

        if confidence >= 90 and len(text.split()) >= 10:
            break

    height, width = image.shape[:2]

    return {
        "text": best["text"].strip(),
        "confidence": best["confidence"],
        "method": best["method"],
        "width": int(width),
        "height": int(height)
    }


# ============================================================
# MAIN IMAGE ANALYZER
# ============================================================

def analyze_image(image_path, ml_predictor=None):
    """
    OCR + text analysis of an image (screenshot / photo).

    ml_predictor (optional): a function that takes text and returns
    "spam", "ham" or "unknown" - the trained email model.

    Returns a dictionary; raises FileNotFoundError, ImageReadError
    or OCRNotAvailableError for problems the caller should report.
    """

    warnings = []

    ocr = extract_text_from_image(image_path)

    text = ocr["text"]

    word_count = len(text.split())

    result = {
        "ocr_available": True,
        "extracted_text": text,
        "text_length": len(text),
        "word_count": word_count,
        "ocr_confidence": round(ocr["confidence"], 1),
        "ocr_method": ocr["method"],
        "image_info": {
            "width": ocr["width"],
            "height": ocr["height"]
        },
        "subject": "",
        "ml_prediction": "unknown",
        "suspicious_keywords": [],
        "urls": [],
        "credential_request": False,
        "payment_request": False,
        "urgent_request": False,
        "warnings": warnings
    }

    # ----------------------------------------------------
    # No readable text
    # ----------------------------------------------------

    if word_count == 0:

        warnings.append(
            "No readable text was found in this image. "
            "A text-based risk score cannot be calculated."
        )

        result.update({
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "classification": "Insufficient text for analysis",
            "risk_factors": []
        })

        return result

    if ocr["confidence"] < 60:

        warnings.append(
            "OCR confidence is low. The extracted text may "
            "contain mistakes, so treat the result with caution."
        )

    # ----------------------------------------------------
    # Existing email / text analyzer
    # ----------------------------------------------------

    analysis = {}

    try:

        analyze_email = _load_email_analyzer()

        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            errors="ignore",
            suffix=".txt",
            delete=False
        )

        try:

            with handle:
                handle.write(text)

            analysis = analyze_email(handle.name)

        finally:

            try:
                os.remove(handle.name)
            except OSError:
                pass

    except Exception as error:

        analysis = {}

        warnings.append(
            "The email analyzer could not be used, so basic "
            f"text rules were applied instead ({error})."
        )

    analyzer_used = bool(analysis)

    keywords = (
        _as_list(analysis.get("suspicious_keywords"))
        or _find_keywords(text)
    )

    urls = _find_urls(text) or _as_list(analysis.get("urls"))

    if analyzer_used:

        credential = bool(analysis.get("credential_request", False))
        payment = bool(analysis.get("payment_request", False))
        urgent = bool(analysis.get("urgent_request", False))

    else:

        credential = bool(CREDENTIAL_PATTERN.search(text))
        payment = bool(PAYMENT_PATTERN.search(text))
        urgent = bool(URGENT_PATTERN.search(text))

    # ----------------------------------------------------
    # Trained model (optional)
    # ----------------------------------------------------

    ml_prediction = "unknown"

    if ml_predictor is not None:

        try:
            ml_prediction = ml_predictor(text)
        except Exception as error:
            warnings.append(f"ML prediction failed: {error}")

    # ----------------------------------------------------
    # Risk
    # ----------------------------------------------------

    risk = calculate_text_risk(
        urls,
        keywords,
        credential,
        payment,
        urgent,
        ml_prediction
    )

    first_line = next(
        (line.strip() for line in text.splitlines() if line.strip()),
        ""
    )

    result.update(risk)

    result.update({
        "subject": analysis.get("subject") or first_line[:100],
        "ml_prediction": ml_prediction,
        "suspicious_keywords": keywords,
        "urls": urls,
        "credential_request": credential,
        "payment_request": payment,
        "urgent_request": urgent
    })

    return result


# ============================================================
# TEST FROM THE COMMAND LINE
#   python backend/image_analyzer.py path/to/screenshot.png
# ============================================================

if __name__ == "__main__":

    import json
    import sys

    if len(sys.argv) < 2:

        print("Usage: python image_analyzer.py <image file>")

        sys.exit(1)

    print(
        json.dumps(
            analyze_image(sys.argv[1]),
            indent=4,
            ensure_ascii=False
        )
    )
