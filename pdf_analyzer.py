"""
PDF evidence analyzer.

What it does
------------
1. Reads the text of every page (up to MAX_PAGES).
2. Finds the real address behind every clickable link.
3. Checks the PDF structure for active content
   (JavaScript, launch actions, embedded files).
4. For scanned pages that contain no text, runs OCR on the page
   image (same OCR engine as the image analyzer).
5. Runs the same explainable text risk engine as the email and
   image analyzers, plus PDF-specific factors.

Library: pypdf  ->  pip install pypdf
"""

import os
import re
import tempfile


MAX_PAGES = 25            # pages whose text is read
MAX_OCR_PAGES = 3         # scanned pages sent to OCR
MIN_TEXT_PER_PAGE = 25    # fewer characters than this = "no text layer"
MAX_FILE_BYTES = 25 * 1024 * 1024


class PDFReadError(ValueError):
    """The file is not a readable PDF."""


# ============================================================
# IMPORT HELPERS (work with `python backend/app.py` and with
# `import backend.pdf_analyzer`)
# ============================================================

def _image_tools():

    try:
        import image_analyzer as module
    except ImportError:
        from backend import image_analyzer as module

    return module


# ============================================================
# STRUCTURE CHECKS
# ============================================================

def _scan_structure(reader, raw_bytes):
    """
    Looks for active content. Uses the PDF object model first and
    a plain byte scan as a second check.
    """

    found = {
        "javascript": False,
        "launch": False,
        "embedded_files": False,
        "open_action": False
    }

    # ---- byte scan (works on uncompressed object markers) ----

    for pattern, key in (
        (rb"/JavaScript\b", "javascript"),
        (rb"/JS[\s(<]", "javascript"),
        (rb"/Launch\b", "launch"),
        (rb"/EmbeddedFile\b", "embedded_files"),
        (rb"/OpenAction\b", "open_action"),
    ):

        if re.search(pattern, raw_bytes):
            found[key] = True

    # ---- object model ----

    try:

        root = reader.trailer["/Root"]

        if "/OpenAction" in root:
            found["open_action"] = True

        if "/AA" in root:
            found["javascript"] = True

        names = root.get("/Names")

        if names is not None:

            names = names.get_object()

            if "/JavaScript" in names:
                found["javascript"] = True

            if "/EmbeddedFiles" in names:
                found["embedded_files"] = True

    except Exception:
        pass

    return found


def _link_actions(reader, pages_limit):
    """
    Returns (uris, found_launch, found_javascript) from link
    annotations of the first pages.
    """

    uris = []
    launch = False
    javascript = False

    for index in range(min(len(reader.pages), pages_limit)):

        try:
            annotations = reader.pages[index].get("/Annots") or []
        except Exception:
            continue

        for annotation in annotations:

            try:

                obj = annotation.get_object()

                action = obj.get("/A")

                if action is None:
                    continue

                action = action.get_object()

                kind = str(action.get("/S", ""))

                if kind == "/URI":

                    uri = str(action.get("/URI", "")).strip()

                    if uri:
                        uris.append(uri)

                elif kind == "/Launch":
                    launch = True

                elif kind == "/JavaScript":
                    javascript = True

            except Exception:
                continue

    return uris, launch, javascript


# ============================================================
# OCR FOR SCANNED PAGES
# ============================================================

def _ocr_page_images(page, tools, warnings):
    """
    OCR on the images embedded in one page. Returns (text, confidence)
    or ("", None) when nothing could be read.
    """

    texts = []
    confidences = []

    try:
        images = list(page.images)
    except Exception:
        return "", None

    for image in images[:2]:

        suffix = os.path.splitext(image.name or "")[1] or ".png"

        handle = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False
        )

        try:

            with handle:
                handle.write(image.data)

            result = tools.extract_text_from_image(handle.name)

            if result["text"]:

                texts.append(result["text"])
                confidences.append(result["confidence"])

        except tools.OCRNotAvailableError as error:

            warnings.append(str(error))

            return "", None

        except Exception:
            continue

        finally:

            try:
                os.remove(handle.name)
            except OSError:
                pass

    if not texts:
        return "", None

    return (
        "\n".join(texts),
        sum(confidences) / len(confidences)
    )


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_pdf(pdf_path, ml_predictor=None):
    """
    Returns a dictionary shaped like the image analyzer's result,
    plus a "pdf_info" section.

    Raises FileNotFoundError or PDFReadError for problems the caller
    should report.
    """

    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError(
            "The pypdf package is not installed. "
            "Run: pip install pypdf"
        )

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if os.path.getsize(pdf_path) > MAX_FILE_BYTES:
        raise PDFReadError("The PDF is larger than 25 MB.")

    with open(pdf_path, "rb") as handle:
        raw_bytes = handle.read()

    if b"%PDF" not in raw_bytes[:1024]:
        raise PDFReadError("This file is not a valid PDF.")

    tools = _image_tools()

    warnings = []

    try:
        reader = PdfReader(pdf_path, strict=False)
    except Exception as error:
        raise PDFReadError(f"The PDF could not be opened ({error}).")

    # ---- encryption ----

    encrypted = bool(reader.is_encrypted)

    if encrypted:

        try:
            opened = reader.decrypt("")
        except Exception:
            opened = 0

        if not opened:
            raise PDFReadError(
                "The PDF is password protected, so it cannot be analyzed."
            )

        warnings.append(
            "The PDF was encrypted but opened without a password."
        )

    try:
        page_count = len(reader.pages)
    except Exception as error:
        raise PDFReadError(f"The PDF pages could not be read ({error}).")

    pages_read = min(page_count, MAX_PAGES)

    if page_count > MAX_PAGES:
        warnings.append(
            f"Only the first {MAX_PAGES} of {page_count} pages were analyzed."
        )

    # ---- metadata ----

    metadata = {}

    try:

        raw_meta = reader.metadata

        if raw_meta:

            for label, key in (
                ("title", "/Title"),
                ("author", "/Author"),
                ("creator", "/Creator"),
                ("producer", "/Producer"),
                ("created", "/CreationDate"),
            ):

                value = raw_meta.get(key)

                if value:
                    metadata[label] = str(value)[:120]

    except Exception:
        pass

    # ---- text of each page, OCR for pages without text ----

    page_texts = []
    ocr_confidences = []
    ocr_pages = 0
    pages_without_text = 0

    for index in range(pages_read):

        page = reader.pages[index]

        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""

        if len(text) < MIN_TEXT_PER_PAGE:

            pages_without_text += 1

            if ocr_pages < MAX_OCR_PAGES:

                ocr_pages += 1

                ocr_text, confidence = _ocr_page_images(
                    page,
                    tools,
                    warnings
                )

                if ocr_text:

                    text = (text + "\n" + ocr_text).strip()

                    ocr_confidences.append(confidence)

        page_texts.append(text)

    full_text = "\n\n".join(t for t in page_texts if t).strip()

    if pages_without_text and not ocr_confidences:

        warnings.append(
            f"{pages_without_text} page(s) had no readable text layer."
        )

    if ocr_confidences:

        warnings.append(
            f"{len(ocr_confidences)} scanned page(s) were read with OCR; "
            "OCR text can contain mistakes."
        )

    # ---- links and structure ----

    link_uris, launch_in_links, js_in_links = _link_actions(
        reader,
        pages_read
    )

    structure = _scan_structure(reader, raw_bytes)

    if launch_in_links:
        structure["launch"] = True

    if js_in_links:
        structure["javascript"] = True

    # ---- text analysis (same engine as the other analyzers) ----

    word_count = len(full_text.split())

    text_urls = tools._find_urls(full_text) if full_text else []

    web_links = [
        uri for uri in link_uris
        if re.match(r"^(https?|ftp)://", uri, re.IGNORECASE)
    ]

    all_urls = []

    for url in text_urls + web_links:

        if url not in all_urls:
            all_urls.append(url)

    hidden_links = [
        uri for uri in web_links
        if uri not in text_urls
    ]

    keywords = []
    subject = ""
    credential = payment = urgent = False

    if full_text:

        analysis = {}

        try:

            analyze_email = tools._load_email_analyzer()

            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                errors="ignore",
                suffix=".txt",
                delete=False
            )

            try:

                with handle:
                    handle.write(full_text)

                analysis = analyze_email(handle.name)

            finally:

                try:
                    os.remove(handle.name)
                except OSError:
                    pass

        except Exception as error:

            analysis = {}

            warnings.append(
                "The email analyzer could not be used, so basic text "
                f"rules were applied instead ({error})."
            )

        keywords = (
            tools._as_list(analysis.get("suspicious_keywords"))
            or tools._find_keywords(full_text)
        )

        if analysis:

            credential = bool(analysis.get("credential_request", False))
            payment = bool(analysis.get("payment_request", False))
            urgent = bool(analysis.get("urgent_request", False))

        else:

            credential = bool(tools.CREDENTIAL_PATTERN.search(full_text))
            payment = bool(tools.PAYMENT_PATTERN.search(full_text))
            urgent = bool(tools.URGENT_PATTERN.search(full_text))

        first_line = next(
            (line.strip() for line in full_text.splitlines() if line.strip()),
            ""
        )

        subject = analysis.get("subject") or first_line[:100]

    ml_prediction = "unknown"

    if ml_predictor is not None and full_text:

        try:
            ml_prediction = ml_predictor(full_text)
        except Exception as error:
            warnings.append(f"ML prediction failed: {error}")

    risk = tools.calculate_text_risk(
        all_urls,
        keywords,
        credential,
        payment,
        urgent,
        ml_prediction
    )

    # ---- PDF-specific factors ----

    factors = list(risk["risk_factors"])

    def add_factor(name, points):
        factors.append({"factor": name, "points": points})

    if structure["javascript"]:
        add_factor("PDF contains JavaScript", 15)

    if structure["launch"]:
        add_factor("PDF contains a launch action (can start programs)", 15)

    if structure["embedded_files"]:
        add_factor("PDF contains embedded files", 5)

    if hidden_links:
        add_factor(
            f"{len(hidden_links)} link(s) point to addresses "
            "that are not shown in the text",
            5
        )

    score = min(sum(item["points"] for item in factors), 100)

    structural_flags = (
        structure["javascript"]
        or structure["launch"]
        or structure["embedded_files"]
        or bool(web_links)
    )

    if word_count == 0 and not structural_flags:

        warnings.append(
            "No readable text was found in this PDF. "
            "A text-based risk score cannot be calculated."
        )

        level = "UNKNOWN"
        classification = "Insufficient text for analysis"
        score = 0

    elif score >= 60:

        level = "HIGH"
        classification = "High Risk / Potential Phishing"

    elif score >= 30:

        level = "MEDIUM"
        classification = "Suspicious / Needs Investigation"

    else:

        level = "LOW"
        classification = "Legitimate / Low Risk"

    return {
        "extracted_text": full_text,
        "text_length": len(full_text),
        "word_count": word_count,
        "ocr_confidence": (
            round(sum(ocr_confidences) / len(ocr_confidences), 1)
            if ocr_confidences else None
        ),
        "subject": subject,
        "ml_prediction": ml_prediction,
        "suspicious_keywords": keywords,
        "urls": all_urls,
        "credential_request": credential,
        "payment_request": payment,
        "urgent_request": urgent,
        "risk_score": score,
        "risk_level": level,
        "classification": classification,
        "risk_factors": factors,
        "warnings": warnings,
        "pdf_info": {
            "pages": page_count,
            "pages_analyzed": pages_read,
            "encrypted": encrypted,
            "metadata": metadata,
            "has_javascript": structure["javascript"],
            "has_launch_action": structure["launch"],
            "has_embedded_files": structure["embedded_files"],
            "has_open_action": structure["open_action"],
            "link_count": len(link_uris),
            "hidden_links": hidden_links,
            "ocr_pages": len(ocr_confidences)
        }
    }


# ============================================================
# TEST FROM THE COMMAND LINE
#   python backend/pdf_analyzer.py path/to/file.pdf
# ============================================================

if __name__ == "__main__":

    import json
    import sys

    if len(sys.argv) < 2:

        print("Usage: python pdf_analyzer.py <pdf file>")

        sys.exit(1)

    print(
        json.dumps(
            analyze_pdf(sys.argv[1]),
            indent=4,
            ensure_ascii=False
        )
    )