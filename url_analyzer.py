import re
import ipaddress
from urllib.parse import urlparse, unquote


# ============================================================
# SUSPICIOUS URL KEYWORDS
# ============================================================

SUSPICIOUS_KEYWORDS = [
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
    "credential",
    "wallet",
    "recover",
    "unlock",
    "suspended",
    "reset"
]


# ============================================================
# HELPERS
# ============================================================

def is_ip_address(hostname):
    if not hostname:
        return False

    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def get_registered_domain(hostname):
    """
    Lightweight domain extraction.

    This intentionally avoids external DNS/API calls.
    """
    if not hostname:
        return ""

    hostname = hostname.lower().strip(".")

    parts = hostname.split(".")

    if len(parts) <= 2:
        return hostname

    return ".".join(parts[-2:])


def count_subdomains(hostname):
    if not hostname:
        return 0

    parts = hostname.split(".")

    if len(parts) <= 2:
        return 0

    return max(len(parts) - 2, 0)


def find_suspicious_keywords(url):
    lowered = unquote(url).lower()

    return [
        keyword
        for keyword in SUSPICIOUS_KEYWORDS
        if keyword in lowered
    ]


def count_special_characters(url):
    return len(
        re.findall(
            r"[^a-zA-Z0-9:/._?&=#%\-]",
            url
        )
    )


def contains_encoded_characters(url):
    return bool(
        re.search(
            r"%[0-9a-fA-F]{2}",
            url
        )
    )


# ============================================================
# MAIN URL ANALYZER
# ============================================================

def analyze_url(url):

    if not isinstance(url, str):
        raise ValueError("URL must be text.")

    url = url.strip()

    if not url:
        raise ValueError("URL is required.")

    # Add scheme for parsing if the user entered only a domain.
    normalized_url = url

    if not re.match(
        r"^[a-zA-Z][a-zA-Z0-9+.-]*://",
        normalized_url
    ):
        normalized_url = "http://" + normalized_url

    parsed = urlparse(normalized_url)

    hostname = parsed.hostname or ""
    path = parsed.path or ""
    query = parsed.query or ""

    hostname = hostname.lower()

    # ========================================================
    # BASIC FEATURES
    # ========================================================

    url_length = len(url)
    domain_length = len(hostname)

    dot_count = url.count(".")
    hyphen_count = url.count("-")
    slash_count = url.count("/")
    digit_count = sum(char.isdigit() for char in url)

    special_character_count = count_special_characters(url)

    uses_https = parsed.scheme.lower() == "https"

    ip_address = is_ip_address(hostname)

    contains_at_symbol = "@" in url

    subdomain_count = count_subdomains(hostname)

    encoded_characters = contains_encoded_characters(url)

    suspicious_keywords = find_suspicious_keywords(url)

    registered_domain = get_registered_domain(hostname)

    # ========================================================
    # ADDITIONAL SECURITY FEATURES
    # ========================================================

    port = parsed.port

    non_standard_port = (
        port is not None
        and port not in (80, 443)
    )

    has_query = bool(query)

    has_long_path = len(path) > 50

    excessive_subdomains = subdomain_count >= 3

    excessive_length = url_length >= 100

    hostname_has_double_hyphen = "--" in hostname

    # ========================================================
    # EXPLAINABLE RISK SCORING
    # ========================================================

    risk_factors = []
    risk_score = 0

    def add_factor(name, points):
        nonlocal risk_score

        risk_score += points

        risk_factors.append({
            "factor": name,
            "points": points
        })

    # HTTPS
    if not uses_https:
        add_factor(
            "URL does not use HTTPS",
            15
        )

    # IP address
    if ip_address:
        add_factor(
            "URL uses an IP address instead of a domain",
            25
        )

    # @ symbol
    if contains_at_symbol:
        add_factor(
            "URL contains @ symbol",
            20
        )

    # Suspicious keywords
    if suspicious_keywords:
        keyword_points = min(
            len(suspicious_keywords) * 5,
            25
        )

        add_factor(
            f"{len(suspicious_keywords)} suspicious keyword(s)",
            keyword_points
        )

    # Long URL
    if excessive_length:
        add_factor(
            "Unusually long URL",
            10
        )

    # Many subdomains
    if excessive_subdomains:
        add_factor(
            "Multiple subdomains detected",
            10
        )

    # Encoded characters
    if encoded_characters:
        add_factor(
            "Encoded characters detected",
            5
        )

    # Non-standard port
    if non_standard_port:
        add_factor(
            "Non-standard port detected",
            10
        )

    # Long path
    if has_long_path:
        add_factor(
            "Long URL path detected",
            5
        )

    # Many hyphens
    if hyphen_count >= 3:
        add_factor(
            "Multiple hyphens in URL",
            5
        )

    # Excessive digits
    if digit_count >= 8:
        add_factor(
            "High number of digits in URL",
            5
        )

    # Double hyphen in hostname
    if hostname_has_double_hyphen:
        add_factor(
            "Double hyphen in hostname",
            5
        )

    # Limit to 100
    risk_score = min(
        risk_score,
        100
    )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    if risk_score >= 60:
        classification = "Phishing / High Risk"
        risk_level = "HIGH"

    elif risk_score >= 20:
        classification = "Suspicious"
        risk_level = "MEDIUM"

    else:
        classification = "Likely Legitimate"
        risk_level = "LOW"

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "url": url,

        "normalized_url": normalized_url,

        "classification": classification,

        "risk_level": risk_level,

        "risk_score": risk_score,

        "risk_factors": risk_factors,

        "domain": hostname,

        "registered_domain": registered_domain,

        "features": {

            "url_length": url_length,

            "domain_length": domain_length,

            "dot_count": dot_count,

            "hyphen_count": hyphen_count,

            "slash_count": slash_count,

            "digit_count": digit_count,

            "special_character_count":
                special_character_count,

            "https": uses_https,

            "ip_address": ip_address,

            "at_symbol": contains_at_symbol,

            "subdomain_count": subdomain_count,

            "encoded_characters":
                encoded_characters,

            "non_standard_port":
                non_standard_port,

            "has_query": has_query,

            "path_length": len(path)

        },

        "suspicious_keywords":
            suspicious_keywords,

        "keyword_count":
            len(suspicious_keywords)

    }