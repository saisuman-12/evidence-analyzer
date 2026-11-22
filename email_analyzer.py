import os
import re
from urllib.parse import urlparse


# ============================================================
# SUSPICIOUS KEYWORDS
# ============================================================

SUSPICIOUS_KEYWORDS = [
    "urgent",
    "immediately",
    "verify",
    "verification",
    "account",
    "password",
    "payment",
    "bank",
    "login",
    "click",
    "suspended",
    "cancelled",
    "confirm",
    "security",
    "expire",
    "24 hours",
    "credential",
    "credentials",
    "signin",
    "sign in",
    "update",
    "billing",
    "card",
    "credit card",
    "debit card"
]


# ============================================================
# URL PATTERN
# ============================================================

URL_PATTERN = r"https?://[^\s<>\"]+"


# ============================================================
# READ EMAIL
# ============================================================

def read_email(file_path):

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        return file.read()


# ============================================================
# EXTRACT SUBJECT
# ============================================================

def extract_subject(email_text):

    match = re.search(
        r"^Subject:\s*(.+)$",
        email_text,
        re.IGNORECASE | re.MULTILINE
    )

    if match:
        return match.group(1).strip()

    return ""


# ============================================================
# EXTRACT URLs
# ============================================================

def extract_urls(email_text):

    urls = re.findall(
        URL_PATTERN,
        email_text
    )

    cleaned_urls = []

    for url in urls:

        # Remove punctuation that may be attached
        # to the URL in normal sentences.
        url = url.rstrip(
            ".,!?;:)]}"
        )

        # Avoid duplicate URLs
        if url not in cleaned_urls:
            cleaned_urls.append(url)

    return cleaned_urls


# ============================================================
# EXTRACT DOMAINS
# ============================================================

def extract_domains(urls):

    domains = []

    for url in urls:

        try:

            parsed_url = urlparse(url)

            if parsed_url.netloc:

                domain = parsed_url.netloc.lower()

                # Remove username/password if present
                # and remove port where applicable.
                if "@" in domain:
                    domain = domain.split("@")[-1]

                if ":" in domain:
                    domain = domain.split(":")[0]

                if domain not in domains:
                    domains.append(domain)

        except Exception:

            continue

    return domains


# ============================================================
# FIND SUSPICIOUS KEYWORDS
# ============================================================

def find_suspicious_keywords(email_text):

    text = email_text.lower()

    found_keywords = []

    for keyword in SUSPICIOUS_KEYWORDS:

        keyword_lower = keyword.lower()

        if keyword_lower in text:

            found_keywords.append(keyword)

    return found_keywords


# ============================================================
# DETECT SUSPICIOUS REQUESTS
# ============================================================

def detect_requests(email_text):

    text = email_text.lower()

    # Normalize multiple spaces/newlines.
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # --------------------------------------------------------
    # Credential-related requests
    # --------------------------------------------------------

    credential_phrases = [

        "verify your account",

        "verify account",

        "account verification",

        "account information",

        "login information",

        "login details",

        "login credentials",

        "your password",

        "password",

        "username and password",

        "confirm your password",

        "enter your password",

        "sign in",

        "signin",

        "credential",

        "credentials"
    ]

    # --------------------------------------------------------
    # Payment-related requests
    # --------------------------------------------------------

    payment_phrases = [

        "payment information",

        "payment details",

        "bank details",

        "bank account",

        "card details",

        "credit card",

        "debit card",

        "billing information",

        "payment method",

        "financial information"
    ]

    # --------------------------------------------------------
    # Urgency-related requests
    # --------------------------------------------------------

    urgent_phrases = [

        "immediately",

        "urgent",

        "urgent action",

        "act now",

        "within 24 hours",

        "24 hours",

        "right away",

        "as soon as possible",

        "account will be suspended",

        "account has been suspended",

        "will be suspended",

        "final warning",

        "expires soon",

        "expire",

        "suspended"
    ]

    # --------------------------------------------------------
    # Detection
    # --------------------------------------------------------

    credential_request = any(
        phrase in text
        for phrase in credential_phrases
    )

    payment_request = any(
        phrase in text
        for phrase in payment_phrases
    )

    urgent_request = any(
        phrase in text
        for phrase in urgent_phrases
    )

    return {

        "credential_request":
            credential_request,

        "payment_request":
            payment_request,

        "urgent_request":
            urgent_request
    }


# ============================================================
# COMPLETE EMAIL ANALYSIS
# ============================================================

def analyze_email(file_path):

    # --------------------------------------------------------
    # Read email
    # --------------------------------------------------------

    email_text = read_email(
        file_path
    )

    # --------------------------------------------------------
    # Extract subject
    # --------------------------------------------------------

    subject = extract_subject(
        email_text
    )

    # --------------------------------------------------------
    # Extract URLs
    # --------------------------------------------------------

    urls = extract_urls(
        email_text
    )

    # --------------------------------------------------------
    # Extract domains
    # --------------------------------------------------------

    domains = extract_domains(
        urls
    )

    # --------------------------------------------------------
    # Find suspicious keywords
    # --------------------------------------------------------

    suspicious_keywords = (
        find_suspicious_keywords(
            email_text
        )
    )

    # --------------------------------------------------------
    # Detect suspicious requests
    # --------------------------------------------------------

    requests = detect_requests(
        email_text
    )

    # --------------------------------------------------------
    # Build final result
    # --------------------------------------------------------

    result = {

        "subject":
            subject,

        "text_length":
            len(email_text),

        "urls":
            urls,

        "url_count":
            len(urls),

        "domains":
            domains,

        "suspicious_keywords":
            suspicious_keywords,

        "suspicious_keyword_count":
            len(suspicious_keywords),

        "credential_request":
            requests[
                "credential_request"
            ],

        "payment_request":
            requests[
                "payment_request"
            ],

        "urgent_request":
            requests[
                "urgent_request"
            ]
    }

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    file_path = os.path.abspath(

        os.path.join(

            os.path.dirname(__file__),

            "..",

            "uploads",

            "suspicious_email.txt"
        )
    )

    try:

        result = analyze_email(
            file_path
        )

        print(
            "\n===== EMAIL ANALYSIS ====="
        )

        print(
            "Subject:",
            result["subject"]
        )

        print(
            "Text Length:",
            result["text_length"]
        )

        print(
            "URLs:",
            result["urls"]
        )

        print(
            "URL Count:",
            result["url_count"]
        )

        print(
            "Domains:",
            result["domains"]
        )

        print(
            "Suspicious Keywords:",
            result[
                "suspicious_keywords"
            ]
        )

        print(
            "Suspicious Keyword Count:",
            result[
                "suspicious_keyword_count"
            ]
        )

        print(
            "Credential Request:",
            result[
                "credential_request"
            ]
        )

        print(
            "Payment Request:",
            result[
                "payment_request"
            ]
        )

        print(
            "Urgent Request:",
            result[
                "urgent_request"
            ]
        )

    except Exception as error:

        print(
            "\nERROR:",
            error
        )