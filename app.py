from flask import Flask, send_from_directory, request, jsonify

import os
import re
import sqlite3
import tempfile
from datetime import datetime
import joblib

from werkzeug.utils import secure_filename

from database import initialize_database, get_connection
from email_analyzer import analyze_email
from url_analyzer import analyze_url
from image_analyzer import (
    analyze_image,
    calculate_text_risk,
    ImageReadError,
    OCRNotAvailableError
)
from pdf_analyzer import (
    analyze_pdf,
    PDFReadError
)
from ioc_extractor import build_ioc_table


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(
    __name__,
    static_folder=None
)


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    BASE_DIR
)

FRONTEND_FOLDER = os.path.join(
    PROJECT_DIR,
    "frontend"
)

UPLOAD_FOLDER = os.path.join(
    PROJECT_DIR,
    "uploads"
)

MODELS_FOLDER = os.path.join(
    PROJECT_DIR,
    "models"
)

os.makedirs(FRONTEND_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODELS_FOLDER, exist_ok=True)

REPORTS_FOLDER = os.path.join(
    PROJECT_DIR,
    "reports"
)

os.makedirs(REPORTS_FOLDER, exist_ok=True)


# ============================================================
# FILE CONFIGURATION
# ============================================================

ALLOWED_EXTENSIONS = {
    "txt",
    "eml",
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "csv",
    "json"
}


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()


# ============================================================
# GENERAL HELPERS
# ============================================================

def error_response(message, status_code):
    """
    Same text under "error" and "message" so every part of
    the frontend (which reads either key) can display it.
    """

    return jsonify({
        "success": False,
        "error": message,
        "message": message
    }), status_code


def text_value(source, key):
    """
    Safely read a text field from a dict / form.
    """

    value = source.get(key, "")

    if value is None:
        return ""

    return str(value).strip()


def allowed_file(filename):

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def get_evidence_type(filename):

    extension = filename.rsplit(".", 1)[1].lower()

    if extension in ["txt", "eml"]:
        return "Email"

    if extension == "pdf":
        return "PDF"

    if extension in ["png", "jpg", "jpeg"]:
        return "Image"

    if extension == "csv":
        return "Transaction Data"

    if extension == "json":
        return "JSON Data"

    return "Unknown"


def is_inside_uploads(path):

    upload_root = os.path.abspath(UPLOAD_FOLDER)

    try:

        common = os.path.commonpath([
            os.path.abspath(path),
            upload_root
        ])

    except ValueError:

        return False

    return (
        os.path.normcase(common)
        == os.path.normcase(upload_root)
    )


# ============================================================
# MACHINE LEARNING HELPER
# ============================================================

_ML_MODEL = None
_ML_VECTORIZER = None


def predict_email_with_ml(email_text):
    """
    Uses the saved Linear SVM:

        models/email_model.pkl
        models/email_tfidf_vectorizer.pkl

    Returns: "spam", "ham" or "unknown".
    The model is loaded once and reused.
    """

    global _ML_MODEL
    global _ML_VECTORIZER

    model_path = os.path.join(
        MODELS_FOLDER,
        "email_model.pkl"
    )

    vectorizer_path = os.path.join(
        MODELS_FOLDER,
        "email_tfidf_vectorizer.pkl"
    )

    if not os.path.exists(model_path):

        print("ML model not found:", model_path)

        return "unknown"

    if not os.path.exists(vectorizer_path):

        print("TF-IDF vectorizer not found:", vectorizer_path)

        return "unknown"

    try:

        if _ML_MODEL is None:
            _ML_MODEL = joblib.load(model_path)

        if _ML_VECTORIZER is None:
            _ML_VECTORIZER = joblib.load(vectorizer_path)

        features = _ML_VECTORIZER.transform(
            [email_text]
        )

        prediction = _ML_MODEL.predict(
            features
        )[0]

        # Accept numeric labels (ham=0, spam=1)
        # and text labels ("ham", "spam").

        label = str(prediction).strip().lower()

        if label in ("1", "spam"):
            return "spam"

        if label in ("0", "ham"):
            return "ham"

        return "unknown"

    except Exception as error:

        print("ML prediction error:", error)

        return "unknown"


# ============================================================
# TEXT ANALYSIS FALLBACKS (used only if the existing
# email analyzer does not return lists)
# ============================================================

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+",
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


def as_list(value):

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return []


def find_urls(text):

    return URL_PATTERN.findall(text)


def find_keywords(text):

    lowered = text.lower()

    return [
        keyword
        for keyword in FALLBACK_KEYWORDS
        if keyword in lowered
    ]


# ============================================================
# SERVE FRONTEND
# ============================================================

@app.route("/")
def serve_frontend():

    return send_from_directory(
        FRONTEND_FOLDER,
        "index.html"
    )


@app.route("/<path:filename>")
def serve_frontend_files(filename):

    return send_from_directory(
        FRONTEND_FOLDER,
        filename
    )


# ============================================================
# CASE MANAGEMENT API
# ============================================================

@app.route("/api/cases", methods=["POST"])
def create_case():

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:

        return error_response(
            "No JSON data received",
            400
        )

    title = text_value(data, "title")
    description = text_value(data, "description")
    investigator = text_value(data, "investigator")

    if not title:

        return error_response(
            "Case title is required",
            400
        )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT case_id
            FROM cases
            ORDER BY id DESC
            LIMIT 1
        """)

        last_case = cursor.fetchone()

        next_number = 1

        if last_case:

            try:

                next_number = int(
                    str(last_case[0]).split("-")[1]
                ) + 1

            except (IndexError, ValueError):

                next_number = 1

        case_id = f"CASE-{next_number:03d}"

        cursor.execute("""
            INSERT INTO cases
            (
                case_id,
                title,
                description,
                investigator
            )
            VALUES (?, ?, ?, ?)
        """, (
            case_id,
            title,
            description,
            investigator
        ))

        connection.commit()

        return jsonify({

            "success": True,

            "message": "Case created successfully!",

            # Flat fields (used by the frontend)
            "case_id": case_id,
            "title": title,
            "description": description,
            "investigator": investigator,

            # Nested copy (kept for compatibility)
            "case": {
                "case_id": case_id,
                "title": title,
                "description": description,
                "investigator": investigator
            }

        })

    except sqlite3.IntegrityError:

        connection.rollback()

        return error_response(
            "Case could not be created",
            500
        )

    except Exception as error:

        connection.rollback()

        return error_response(str(error), 500)

    finally:

        connection.close()


@app.route("/api/cases", methods=["GET"])
def get_cases():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                case_id,
                title,
                description,
                investigator,
                created_at
            FROM cases
            ORDER BY id DESC
        """)

        case_rows = cursor.fetchall()

        cases = []

        for row in case_rows:

            cursor.execute("""
                SELECT
                    id,
                    filename,
                    evidence_type,
                    file_path,
                    uploaded_at
                FROM evidence
                WHERE case_id = ?
                ORDER BY id ASC
            """, (row[1],))

            evidence = [
                {
                    "id": item[0],
                    "filename": item[1],
                    "evidence_type": item[2],
                    "file_path": item[3],
                    "uploaded_at": item[4]
                }
                for item in cursor.fetchall()
            ]

            cases.append({
                "id": row[0],
                "case_id": row[1],
                "title": row[2],
                "description": row[3],
                "investigator": row[4],
                "created_at": row[5],
                "evidence": evidence
            })

        return jsonify({
            "success": True,
            "cases": cases
        })

    except Exception as error:

        return error_response(str(error), 500)

    finally:

        connection.close()


# ============================================================
# EVIDENCE UPLOAD API
# ============================================================

@app.route("/api/evidence/upload", methods=["POST"])
def upload_evidence():

    case_id = text_value(request.form, "case_id")

    if not case_id:

        return error_response(
            "Case ID is required",
            400
        )

    if "file" not in request.files:

        return error_response(
            "No file uploaded",
            400
        )

    file = request.files["file"]

    if not file.filename:

        return error_response(
            "No file selected",
            400
        )

    if not allowed_file(file.filename):

        return error_response(
            "File type not allowed",
            400
        )

    safe_filename = secure_filename(
        file.filename
    )

    if not allowed_file(safe_filename):

        return error_response(
            "Invalid file name",
            400
        )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # Case must exist

        cursor.execute("""
            SELECT case_id
            FROM cases
            WHERE case_id = ?
        """, (case_id,))

        if not cursor.fetchone():

            return error_response(
                "Case not found",
                404
            )

        # Duplicate evidence in the same case.
        # The frontend expects success=True + duplicate=True.

        cursor.execute("""
            SELECT id, filename, evidence_type, file_path
            FROM evidence
            WHERE case_id = ?
            AND filename = ?
            ORDER BY id DESC
            LIMIT 1
        """, (
            case_id,
            safe_filename
        ))

        existing = cursor.fetchone()

        if existing:

            return jsonify({
                "success": True,
                "duplicate": True,
                "message": "Evidence already exists for this case.",
                "evidence_id": existing[0],
                "case_id": case_id,
                "filename": existing[1],
                "evidence_type": existing[2],
                "file_path": existing[3]
            })

        file_path = os.path.join(
            UPLOAD_FOLDER,
            safe_filename
        )

        file.save(file_path)

        evidence_type = get_evidence_type(
            safe_filename
        )

        cursor.execute("""
            INSERT INTO evidence
            (
                case_id,
                filename,
                evidence_type,
                file_path
            )
            VALUES (?, ?, ?, ?)
        """, (
            case_id,
            safe_filename,
            evidence_type,
            file_path
        ))

        evidence_id = cursor.lastrowid

        connection.commit()

        return jsonify({

            "success": True,

            "message": "Evidence uploaded successfully",

            # Flat fields (used by the frontend)
            "evidence_id": evidence_id,
            "case_id": case_id,
            "filename": safe_filename,
            "evidence_type": evidence_type,
            "file_path": file_path,

            # Nested copy (kept for compatibility)
            "evidence": {
                "id": evidence_id,
                "case_id": case_id,
                "filename": safe_filename,
                "evidence_type": evidence_type,
                "file_path": file_path
            }

        })

    except Exception as error:

        connection.rollback()

        return error_response(str(error), 500)

    finally:

        connection.close()


# ============================================================
# EVIDENCE FILE LOOKUP
# ============================================================

def locate_evidence_file(
    file_path,
    filename,
    case_id,
    evidence_id
):
    """
    Returns (absolute_path, error_message, status_code).

    Search order:
      1. path sent by the frontend
      2. uploads/<filename>
      3. database row by evidence id
      4. database row by case + filename
    Files outside the uploads folder are never returned.
    """

    candidates = []

    if file_path:
        candidates.append(file_path)

    if filename:
        candidates.append(
            os.path.join(
                UPLOAD_FOLDER,
                os.path.basename(filename)
            )
        )

    rows = []

    if evidence_id or filename:

        connection = get_connection()

        try:

            cursor = connection.cursor()

            if evidence_id:

                cursor.execute("""
                    SELECT file_path, filename
                    FROM evidence
                    WHERE id = ?
                """, (evidence_id,))

                rows.extend(cursor.fetchall())

            if filename:

                if case_id:

                    cursor.execute("""
                        SELECT file_path, filename
                        FROM evidence
                        WHERE case_id = ?
                        AND filename = ?
                        ORDER BY id DESC
                        LIMIT 1
                    """, (case_id, filename))

                else:

                    cursor.execute("""
                        SELECT file_path, filename
                        FROM evidence
                        WHERE filename = ?
                        ORDER BY id DESC
                        LIMIT 1
                    """, (filename,))

                rows.extend(cursor.fetchall())

        finally:

            connection.close()

    for database_path, database_filename in rows:

        if database_path:
            candidates.append(database_path)

        if database_filename:
            candidates.append(
                os.path.join(
                    UPLOAD_FOLDER,
                    os.path.basename(database_filename)
                )
            )

    found_outside_uploads = False

    for candidate in candidates:

        absolute = os.path.abspath(candidate)

        if not os.path.isfile(absolute):
            continue

        if is_inside_uploads(absolute):
            return absolute, None, 200

        found_outside_uploads = True

    if found_outside_uploads:

        return (
            None,
            "Invalid evidence file path.",
            400
        )

    return (
        None,
        "Uploaded email file could not be found "
        "in the uploads folder.",
        404
    )


# ============================================================
# EMAIL ANALYSIS API (uploaded evidence)
# ============================================================

@app.route("/api/analyze/email", methods=["POST"])
def analyze_email_api():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        data = request.form.to_dict()

    absolute_file_path, error, status_code = (
        locate_evidence_file(
            text_value(data, "file_path"),
            text_value(data, "filename"),
            text_value(data, "case_id"),
            data.get("evidence_id")
        )
    )

    if not absolute_file_path:

        return error_response(error, status_code)

    try:

        # Existing NLP / rule-based analysis
        result = analyze_email(
            absolute_file_path
        )

        with open(
            absolute_file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as email_file:

            email_text = email_file.read()

        ml_prediction = predict_email_with_ml(
            email_text
        )

        result["ml_prediction"] = ml_prediction
        result["prediction"] = ml_prediction

        return jsonify({
            "success": True,
            "analysis": result
        })

    except Exception as error:

        print("Email analysis error:", error)

        return error_response(str(error), 500)


# ============================================================
# LIVE PASTED EMAIL / MESSAGE ANALYSIS
# ============================================================

@app.route("/api/analyze/email-text", methods=["POST"])
def analyze_email_text():

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:

        return error_response(
            "No message received",
            400
        )

    message = data.get("message", "")

    if not isinstance(message, str):

        return error_response(
            "Message must be text",
            400
        )

    message = message.strip()

    if not message:

        return error_response(
            "Please enter or paste a message",
            400
        )

    temporary_path = None

    try:

        # Save temporarily so the existing analyzer
        # (which reads files) can be reused.

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            errors="ignore",
            prefix="live_message_",
            suffix=".txt",
            delete=False,
            dir=UPLOAD_FOLDER
        ) as temporary_file:

            temporary_file.write(message)

            temporary_path = temporary_file.name

        analysis = analyze_email(
            temporary_path
        )

        # Real output of the trained Linear SVM
        ml_prediction = predict_email_with_ml(
            message
        )

        # ----------------------------------------------------
        # INDICATORS
        # ----------------------------------------------------

        suspicious_keywords = (
            as_list(analysis.get("suspicious_keywords"))
            or find_keywords(message)
        )

        urls = (
            as_list(analysis.get("urls"))
            or find_urls(message)
        )

        credential_request = bool(
            analysis.get("credential_request", False)
        )

        payment_request = bool(
            analysis.get("payment_request", False)
        )

        urgent_request = bool(
            analysis.get("urgent_request", False)
        )

        # ----------------------------------------------------
        # EXPLAINABLE RISK ENGINE
        # ----------------------------------------------------

        risk_factors = []

        def add_factor(name, points):

            if points > 0:

                risk_factors.append({
                    "factor": name,
                    "points": points
                })

        add_factor(
            f"{len(suspicious_keywords)} suspicious keyword(s)",
            min(len(suspicious_keywords) * 3, 15)
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

        # The spam/ham model is only a supporting signal.
        if ml_prediction == "spam":
            add_factor("ML model flagged message as spam", 5)

        risk_points = min(
            sum(item["points"] for item in risk_factors),
            100
        )

        if risk_points >= 60:

            risk_level = "HIGH"
            classification = "High Risk / Potential Phishing"

        elif risk_points >= 30:

            risk_level = "MEDIUM"
            classification = "Suspicious / Needs Investigation"

        else:

            risk_level = "LOW"
            classification = "Legitimate / Low Risk"

        return jsonify({

            "success": True,

            "analysis": {

                # Raw model output: spam / ham / unknown.
                # The frontend turns it into display text.
                "ml_prediction": ml_prediction,
                "ml_model_prediction": ml_prediction,

                "classification": classification,

                "risk_score": risk_points,
                "risk_level": risk_level,
                "risk_factors": risk_factors,

                "subject": analysis.get("subject", ""),

                "suspicious_keywords": suspicious_keywords,
                "urls": urls,

                "credential_request": credential_request,
                "payment_request": payment_request,
                "urgent_request": urgent_request,

                "details": analysis

            }

        })

    except Exception as error:

        print("Pasted message analysis error:", error)

        return error_response(str(error), 500)

    finally:

        if (
            temporary_path
            and os.path.exists(temporary_path)
        ):

            try:
                os.remove(temporary_path)
            except Exception:
                pass


# ============================================================
# IMAGE / SCREENSHOT OCR ANALYSIS
# ============================================================

@app.route("/api/analyze/image", methods=["POST"])
def analyze_image_api():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        data = request.form.to_dict()

    absolute_file_path, error, status_code = (
        locate_evidence_file(
            text_value(data, "file_path"),
            text_value(data, "filename"),
            text_value(data, "case_id"),
            data.get("evidence_id")
        )
    )

    if not absolute_file_path:

        return error_response(error, status_code)

    try:

        result = analyze_image(
            absolute_file_path,
            ml_predictor=predict_email_with_ml
        )

        return jsonify({
            "success": True,
            "analysis": result
        })

    except FileNotFoundError as error:

        return error_response(str(error), 404)

    except ImageReadError as error:

        return error_response(str(error), 400)

    except OCRNotAvailableError as error:

        return error_response(str(error), 503)

    except Exception as error:

        print("Image analysis error:", error)

        return error_response(str(error), 500)


# ============================================================
# PDF ANALYSIS
# ============================================================

@app.route("/api/analyze/pdf", methods=["POST"])
def analyze_pdf_api():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        data = request.form.to_dict()

    absolute_file_path, error, status_code = (
        locate_evidence_file(
            text_value(data, "file_path"),
            text_value(data, "filename"),
            text_value(data, "case_id"),
            data.get("evidence_id")
        )
    )

    if not absolute_file_path:

        return error_response(error, status_code)

    try:

        result = analyze_pdf(
            absolute_file_path,
            ml_predictor=predict_email_with_ml
        )

        return jsonify({
            "success": True,
            "analysis": result
        })

    except FileNotFoundError as error:

        return error_response(str(error), 404)

    except PDFReadError as error:

        return error_response(str(error), 400)

    except Exception as error:

        print("PDF analysis error:", error)

        return error_response(str(error), 500)


# ============================================================
# URL ANALYSIS API
# ============================================================

@app.route("/api/analyze/url", methods=["POST"])
def analyze_url_api():

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:

        return error_response(
            "No JSON data received",
            400
        )

    url = text_value(data, "url")

    if not url:

        return error_response(
            "URL is required",
            400
        )

    try:

        result = analyze_url(url)

        return jsonify({
            "success": True,
            "analysis": result
        })

    except Exception as error:

        return error_response(str(error), 500)


# ============================================================
# INVESTIGATION REPORT (PDF)
# ============================================================

TEXT_EXTENSIONS = {"txt", "eml"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def resolve_evidence_path(file_path, filename):

    candidates = []

    if file_path:
        candidates.append(file_path)

    if filename:
        candidates.append(
            os.path.join(UPLOAD_FOLDER, os.path.basename(filename))
        )

    for candidate in candidates:

        if (
            candidate
            and is_inside_uploads(candidate)
            and os.path.isfile(candidate)
        ):
            return os.path.abspath(candidate)

    return None


_ANALYSIS_CACHE = {}


def analyze_evidence_for_report(path, filename):
    """
    Same as _analyze_evidence_uncached, but remembers the result while
    the file is unchanged, so the report and the IOC table do not run
    OCR on the same screenshot again and again.
    """

    try:

        info = os.stat(path)

        key = (path, info.st_mtime_ns, info.st_size)

    except OSError:

        return _analyze_evidence_uncached(path, filename)

    if key not in _ANALYSIS_CACHE:

        if len(_ANALYSIS_CACHE) > 200:
            _ANALYSIS_CACHE.clear()

        _ANALYSIS_CACHE[key] = _analyze_evidence_uncached(path, filename)

    return _ANALYSIS_CACHE[key]


def _analyze_evidence_uncached(path, filename):
    """
    Runs the real analyzers for one evidence file.
    Returns (analysis_or_None, note, url_results, text_excerpt).
    """

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension in TEXT_EXTENSIONS:

        with open(
            path, "r", encoding="utf-8", errors="ignore"
        ) as text_file:

            text = text_file.read()

        details = analyze_email(path)

        ml_prediction = predict_email_with_ml(text)

        keywords = (
            as_list(details.get("suspicious_keywords"))
            or find_keywords(text)
        )

        urls = as_list(details.get("urls")) or find_urls(text)

        credential = bool(details.get("credential_request", False))
        payment = bool(details.get("payment_request", False))
        urgent = bool(details.get("urgent_request", False))

        risk = calculate_text_risk(
            urls,
            keywords,
            credential,
            payment,
            urgent,
            ml_prediction
        )

        analysis = {
            "ml_prediction": ml_prediction,
            "subject": details.get("subject", ""),
            "suspicious_keywords": keywords,
            "urls": urls,
            "credential_request": credential,
            "payment_request": payment,
            "urgent_request": urgent,
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "classification": risk["classification"],
            "risk_factors": risk["risk_factors"],
        }

        excerpt = text

    elif extension in IMAGE_EXTENSIONS:

        analysis = analyze_image(
            path,
            ml_predictor=predict_email_with_ml
        )

        urls = analysis.get("urls") or []

        excerpt = ""

    elif extension == "pdf":

        analysis = analyze_pdf(
            path,
            ml_predictor=predict_email_with_ml
        )

        urls = analysis.get("urls") or []

        excerpt = ""

    else:

        return (
            None,
            "No automated analyzer is available for this file type "
            "(" + (extension or "unknown") + "). The file is recorded "
            "as evidence only.",
            [],
            ""
        )

    url_results = []

    for url in urls[:5]:

        try:

            url_result = analyze_url(url)

            url_results.append({
                "url": url,
                "classification": url_result.get("classification"),
                "risk_score": url_result.get("risk_score"),
            })

        except Exception:

            url_results.append({
                "url": url,
                "classification": "Could not be analyzed",
                "risk_score": "-",
            })

    return analysis, "", url_results, excerpt


def url_risk_for_ioc(url):

    result = analyze_url(url)

    return (
        result.get("classification"),
        result.get("risk_score")
    )


def ioc_source(filename, analysis, excerpt):

    analysis = analysis or {}

    return {
        "filename": filename,
        "text": excerpt or analysis.get("extracted_text") or "",
        "urls": analysis.get("urls") or [],
    }


@app.route("/api/reports/generate", methods=["POST"])
def generate_report():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        data = request.form.to_dict()

    case_id = text_value(data, "case_id")

    if not case_id:

        return error_response("case_id is required.", 400)

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT case_id, title, description,
                   investigator, created_at
            FROM cases
            WHERE case_id = ?
        """, (case_id,))

        case_row = cursor.fetchone()

        if not case_row:

            return error_response("Case not found.", 404)

        cursor.execute("""
            SELECT filename, evidence_type, file_path, uploaded_at
            FROM evidence
            WHERE case_id = ?
            ORDER BY id
        """, (case_id,))

        evidence_rows = cursor.fetchall()

    finally:

        connection.close()

    try:

        from report_generator import build_report_pdf

        case = {
            "case_id": case_row[0],
            "title": case_row[1],
            "description": case_row[2],
            "investigator": case_row[3],
            "created_at": case_row[4],
        }

        items = []

        for row in evidence_rows:

            item = {
                "filename": row[0],
                "evidence_type": row[1],
                "uploaded_at": row[3],
                "analysis": None,
                "note": "",
                "url_results": [],
                "text_excerpt": "",
            }

            path = resolve_evidence_path(row[2], row[0])

            if not path:

                item["note"] = (
                    "The evidence file could not be found on the "
                    "server, so it was not analyzed."
                )

            else:

                try:

                    (
                        item["analysis"],
                        item["note"],
                        item["url_results"],
                        item["text_excerpt"]
                    ) = analyze_evidence_for_report(path, row[0])

                except Exception as analysis_error:

                    print("Report analysis error:", analysis_error)

                    item["note"] = (
                        "Automated analysis failed for this file: "
                        + str(analysis_error)
                    )

            items.append(item)

        analyzed = [i for i in items if i["analysis"]]

        scored = [
            i["analysis"] for i in analyzed
            if i["analysis"].get("risk_level") in RISK_ORDER
        ]

        if scored:

            top = max(
                scored,
                key=lambda a: (
                    RISK_ORDER[a["risk_level"]],
                    a.get("risk_score", 0)
                )
            )

            overall = {
                "risk_level": top["risk_level"],
                "risk_score": top.get("risk_score", 0),
            }

        else:

            overall = {
                "risk_level": "NOT ASSESSED",
                "risk_score": None,
            }

        overall["analyzed"] = len(analyzed)
        overall["total"] = len(items)

        safe_case = re.sub(
            r"[^A-Za-z0-9_-]", "_", str(case["case_id"])
        )

        filename = (
            "report_"
            + safe_case
            + "_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".pdf"
        )

        ioc_table = build_ioc_table(
            [
                ioc_source(
                    item["filename"],
                    item["analysis"],
                    item["text_excerpt"]
                )
                for item in items
                if item["analysis"]
            ],
            url_risk_for_ioc
        )

        build_report_pdf(
            os.path.join(REPORTS_FOLDER, filename),
            case,
            items,
            overall,
            ioc_table
        )

        return jsonify({
            "success": True,
            "message": "Investigation report generated successfully.",
            "filename": filename,
            "report_url": "/reports/" + filename,
            "overall_risk": overall["risk_level"]
        })

    except Exception as error:

        print("Report generation error:", error)

        return error_response(str(error), 500)


@app.route("/api/reports/count", methods=["GET"])
def count_reports():

    try:

        count = len([
            name for name in os.listdir(REPORTS_FOLDER)
            if name.lower().endswith(".pdf")
        ])

    except OSError:

        count = 0

    return jsonify({
        "success": True,
        "count": count
    })


@app.route("/reports/<path:filename>")
def serve_report(filename):

    return send_from_directory(
        REPORTS_FOLDER,
        filename,
        as_attachment=False
    )


# ============================================================
# IOC EXTRACTION FOR A CASE
# ============================================================

@app.route("/api/cases/<case_id>/iocs", methods=["GET"])
def case_iocs(case_id):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            "SELECT case_id FROM cases WHERE case_id = ?",
            (case_id,)
        )

        if not cursor.fetchone():

            return error_response("Case not found.", 404)

        cursor.execute("""
            SELECT filename, file_path
            FROM evidence
            WHERE case_id = ?
            ORDER BY id
        """, (case_id,))

        evidence_rows = cursor.fetchall()

    finally:

        connection.close()

    try:

        sources = []
        skipped = []

        for filename, file_path in evidence_rows:

            path = resolve_evidence_path(file_path, filename)

            if not path:

                skipped.append({
                    "filename": filename,
                    "reason": "File not found on the server."
                })

                continue

            try:

                analysis, note, url_results, excerpt = (
                    analyze_evidence_for_report(path, filename)
                )

            except Exception as analysis_error:

                print("IOC analysis error:", analysis_error)

                skipped.append({
                    "filename": filename,
                    "reason": str(analysis_error)
                })

                continue

            if not analysis:

                skipped.append({
                    "filename": filename,
                    "reason": note or "No analyzer for this file type."
                })

                continue

            sources.append(
                ioc_source(filename, analysis, excerpt)
            )

        table = build_ioc_table(sources, url_risk_for_ioc)

        return jsonify({
            "success": True,
            "case_id": case_id,
            "summary": table["summary"],
            "indicators": table["indicators"],
            "skipped": skipped
        })

    except Exception as error:

        print("IOC extraction error:", error)

        return error_response(str(error), 500)


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )