"""
IOC (Indicator of Compromise) extraction.

Finds four kinds of indicators in the text of the evidence:
    URLs, domains, IP addresses (IPv4) and email addresses

and combines them across all evidence of a case into one table that
shows where each indicator was found and how often.

Everything here is plain pattern matching. It does not contact any
website, DNS server or threat-intelligence service.
"""

import ipaddress
import re
from urllib.parse import urlparse


MAX_INDICATORS = 500


# ============================================================
# PATTERNS
# ============================================================

URL_PATTERN = re.compile(
    r"(?i)\b(?:https?|ftp)://[^\s<>\"'`]+"
)

EMAIL_PATTERN = re.compile(
    r"(?i)\b[a-z0-9][a-z0-9._%+\-]*@"
    r"[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)*\.[a-z]{2,}\b"
)

IPV4_PATTERN = re.compile(
    r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.]*\d)"
)

# Bare domains are only accepted for well-known endings, so that file
# names such as "report.pdf" or "script.js" are not reported.

KNOWN_ENDINGS = (
    "com|net|org|info|biz|edu|gov|mil|int|co|io|ai|app|dev|tech|xyz|top|"
    "club|online|site|shop|store|live|link|click|support|help|bank|pay|"
    "money|cloud|work|space|website|page|fun|icu|vip|cc|tk|ml|ga|cf|gq|"
    "ly|me|tv|ws|pw|in|uk|us|ru|cn|de|fr|jp|br|au|ca|nl|it|es|pl|se|ch|"
    "kr|tr|ua|ir|pk|bd|ng|ke|za|id|my|sg|hk|tw|vn|th|ph|mx|ar|cl|eu|asia"
)

DOMAIN_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+"
    r"(?:" + KNOWN_ENDINGS + r")\b"
)

TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"


# ============================================================
# HELPERS
# ============================================================

def refang(text):
    """
    Security reports often "defang" indicators so they cannot be
    clicked (hxxp://evil[.]com). This turns them back into normal form.
    """

    text = re.sub(r"(?i)\bhxxp(s?)://", r"http\1://", text)
    text = re.sub(r"(?i)\bh\*\*p(s?)://", r"http\1://", text)
    text = re.sub(r"\[\s*\.\s*\]|\(\s*\.\s*\)|\{\s*\.\s*\}", ".", text)
    text = re.sub(r"(?i)\[\s*at\s*\]|\(\s*at\s*\)", "@", text)
    text = re.sub(r"\[\s*:\s*\]", ":", text)

    return text


def _clean_url(url):

    url = url.strip()

    while url and url[-1] in TRAILING_PUNCTUATION:
        url = url[:-1]

    return url


def _is_valid_ipv4(value):

    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


def _host_of(url):

    try:

        host = urlparse(url).hostname or ""

    except ValueError:

        host = ""

    return host.lower().strip(".")


def _count(values):
    """Ordered list of {"value", "count"}, keeping first-seen order."""

    counts = {}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    return [
        {"value": value, "count": number}
        for value, number in counts.items()
    ]


# ============================================================
# EXTRACTION FROM ONE TEXT
# ============================================================

def extract_iocs(text, extra_urls=None):
    """
    Returns {"urls": [...], "domains": [...], "ips": [...], "emails": [...]}
    where each item is {"value": str, "count": int}.

    extra_urls: URLs found by another analyzer (for example the real
    targets of clickable links in a PDF). They are added to the URL list.
    """

    text = refang(text or "")

    urls = [_clean_url(match) for match in URL_PATTERN.findall(text)]

    # URLs reported by another analyzer are added only when the text
    # does not already contain them (otherwise they would be counted twice).

    for url in extra_urls or []:

        cleaned = _clean_url(str(url))

        if cleaned and cleaned not in urls:
            urls.append(cleaned)

    urls = [url for url in urls if _host_of(url)]

    # Remove URLs from the text so their host names are not counted twice.

    remainder = URL_PATTERN.sub(" ", text)

    emails = [
        match.lower()
        for match in EMAIL_PATTERN.findall(remainder)
    ]

    remainder = EMAIL_PATTERN.sub(" ", remainder)

    ips = []
    domains = []

    for url in urls:

        host = _host_of(url)

        if _is_valid_ipv4(host):
            ips.append(host)
        else:
            domains.append(host)

    for match in IPV4_PATTERN.findall(remainder):

        if _is_valid_ipv4(match):
            ips.append(match)

    for email in emails:
        domains.append(email.rsplit("@", 1)[1])

    for match in DOMAIN_PATTERN.finditer(remainder):

        domain = match.group(0).lower().strip(".")

        if not _is_valid_ipv4(domain):
            domains.append(domain)

    return {
        "urls": _count(urls),
        "domains": _count(domains),
        "ips": _count(ips),
        "emails": _count(emails)
    }


# ============================================================
# COMBINE ALL EVIDENCE OF A CASE
# ============================================================

PRIVATE_NETWORKS = [
    ipaddress.ip_network(n)
    for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
]

DOCUMENTATION_NETWORKS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
]


def _ip_note(value):

    try:
        address = ipaddress.IPv4Address(value)
    except ValueError:
        return ""

    if address.is_loopback:
        return "Loopback address"

    if any(address in net for net in PRIVATE_NETWORKS):
        return "Private / internal address"

    if any(address in net for net in DOCUMENTATION_NETWORKS):
        return "Documentation / test address"

    if address.is_link_local:
        return "Link-local address"

    if address.is_multicast:
        return "Multicast address"

    if not address.is_global:
        return "Reserved address"

    return "Public address"


def build_ioc_table(sources, url_assessor=None):
    """
    sources: list of {"filename": str, "text": str, "urls": [str, ...]}
    url_assessor: optional function(url) -> (classification, risk_score)

    Returns {"summary": {...}, "indicators": [...]}
    """

    merged = {}

    kinds = (
        ("urls", "URL"),
        ("domains", "Domain"),
        ("ips", "IP Address"),
        ("emails", "Email Address"),
    )

    for source in sources:

        found = extract_iocs(
            source.get("text", ""),
            source.get("urls") or []
        )

        for key, label in kinds:

            for item in found[key]:

                entry = merged.setdefault(
                    (label, item["value"]),
                    {
                        "type": label,
                        "value": item["value"],
                        "count": 0,
                        "sources": []
                    }
                )

                entry["count"] += item["count"]

                if source.get("filename") not in entry["sources"]:
                    entry["sources"].append(source.get("filename"))

    indicators = list(merged.values())

    for entry in indicators:

        entry["assessment"] = ""
        entry["risk_score"] = None

        if entry["type"] == "URL" and url_assessor:

            try:

                classification, score = url_assessor(entry["value"])

                entry["assessment"] = f"{classification} ({score}/100)"
                entry["risk_score"] = score

            except Exception:

                entry["assessment"] = "Could not be assessed"

        elif entry["type"] == "IP Address":

            entry["assessment"] = _ip_note(entry["value"])

        elif entry["type"] == "Email Address":

            entry["assessment"] = "Sender / contact address"

        elif entry["type"] == "Domain":

            entry["assessment"] = "Host name seen in evidence"

    order = {"URL": 0, "Domain": 1, "IP Address": 2, "Email Address": 3}

    indicators.sort(
        key=lambda e: (
            order[e["type"]],
            -(e["risk_score"] if e["risk_score"] is not None else -1),
            -e["count"],
            e["value"]
        )
    )

    truncated = len(indicators) > MAX_INDICATORS

    indicators = indicators[:MAX_INDICATORS]

    summary = {
        "total": len(indicators),
        "urls": sum(1 for e in indicators if e["type"] == "URL"),
        "domains": sum(1 for e in indicators if e["type"] == "Domain"),
        "ips": sum(1 for e in indicators if e["type"] == "IP Address"),
        "emails": sum(1 for e in indicators if e["type"] == "Email Address"),
        "evidence_scanned": len(sources),
        "truncated": truncated
    }

    return {
        "summary": summary,
        "indicators": indicators
    }


# ============================================================
# TEST FROM THE COMMAND LINE
#   python backend/ioc_extractor.py "text with http://evil.com"
# ============================================================

if __name__ == "__main__":

    import json
    import sys

    sample = " ".join(sys.argv[1:]) or (
        "Visit http://secure-login.example.com/verify now or write to "
        "support@example.com. Server 192.168.1.10 and hxxp://bad[.]site/x"
    )

    print(
        json.dumps(
            extract_iocs(sample),
            indent=4
        )
    )