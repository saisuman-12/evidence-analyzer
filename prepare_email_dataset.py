import os
import tarfile
import csv
import re
import html
from email import policy
from email.parser import BytesParser


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

RAW_DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
    "raw"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "emails.csv"
)


# ============================================================
# DATASET FILES
# ============================================================

DATASETS = [
    ("20030228_easy_ham.tar.bz2", "ham"),
    ("20030228_easy_ham_2.tar.bz2", "ham"),
    ("20030228_spam.tar.bz2", "spam"),
    ("20030228_spam_2.tar.bz2", "spam")
]


# ============================================================
# STATISTICS
# ============================================================

stats = {
    "processed": 0,
    "skipped": 0,
    "parse_errors": 0
}


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        r"<script.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FALLBACK RAW TEXT EXTRACTION
# ============================================================

def fallback_extract_text(raw_email):

    try:

        text = raw_email.decode(
            "utf-8",
            errors="ignore"
        )

        return clean_text(text)

    except Exception:

        return ""


# ============================================================
# EXTRACT EMAIL TEXT
# ============================================================

def extract_email_text(raw_email):

    try:

        # ----------------------------------------------------
        # Use compat32 policy.
        # It is more tolerant of old/malformed emails.
        # ----------------------------------------------------

        parser = BytesParser(
            policy=policy.compat32
        )

        message = parser.parsebytes(
            raw_email
        )

        subject = message.get(
            "Subject",
            ""
        ) or ""

        body_parts = []

        # ----------------------------------------------------
        # Multipart email
        # ----------------------------------------------------

        if message.is_multipart():

            for part in message.walk():

                content_type = (
                    part.get_content_type()
                )

                disposition = (
                    part.get(
                        "Content-Disposition",
                        ""
                    ) or ""
                )

                if "attachment" in disposition.lower():
                    continue

                if content_type in (
                    "text/plain",
                    "text/html"
                ):

                    try:

                        payload = part.get_payload(
                            decode=True
                        )

                        if payload:

                            text = payload.decode(
                                "utf-8",
                                errors="ignore"
                            )

                            body_parts.append(
                                text
                            )

                    except Exception:

                        continue

        # ----------------------------------------------------
        # Normal email
        # ----------------------------------------------------

        else:

            try:

                payload = message.get_payload(
                    decode=True
                )

                if payload:

                    if isinstance(
                        payload,
                        bytes
                    ):

                        text = payload.decode(
                            "utf-8",
                            errors="ignore"
                        )

                    else:

                        text = str(payload)

                    body_parts.append(
                        text
                    )

            except Exception:

                pass

        combined_text = (
            str(subject)
            + " "
            + " ".join(body_parts)
        )

        cleaned = clean_text(
            combined_text
        )

        if len(cleaned) >= 20:
            return cleaned

        # If parsed result is too small,
        # use fallback extraction.
        return fallback_extract_text(
            raw_email
        )

    except Exception:

        stats["parse_errors"] += 1

        # ----------------------------------------------------
        # IMPORTANT:
        # A malformed email should not stop
        # the entire dataset preparation.
        # ----------------------------------------------------

        return fallback_extract_text(
            raw_email
        )


# ============================================================
# PROCESS ARCHIVE
# ============================================================

def process_archive(
    archive_path,
    label
):

    emails = []

    print()
    print(
        f"Processing: "
        f"{os.path.basename(archive_path)}"
    )

    try:

        with tarfile.open(
            archive_path,
            "r:bz2"
        ) as archive:

            members = archive.getmembers()

            for member in members:

                if not member.isfile():
                    continue

                filename = os.path.basename(
                    member.name
                )

                if filename.startswith("."):
                    continue

                extracted_file = archive.extractfile(
                    member
                )

                if extracted_file is None:
                    stats["skipped"] += 1
                    continue

                try:

                    raw_email = (
                        extracted_file.read()
                    )

                    text = extract_email_text(
                        raw_email
                    )

                    if len(text) < 20:

                        stats["skipped"] += 1
                        continue

                    emails.append({
                        "text": text,
                        "label": label
                    })

                    stats["processed"] += 1

                except Exception:

                    stats["skipped"] += 1
                    continue

    except Exception as error:

        print(
            f"Archive error: {error}"
        )

    print(
        f"Extracted {len(emails)} "
        f"{label} emails"
    )

    return emails


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 50)
    print("   EMAIL DATASET PREPARATION")
    print("=" * 50)

    all_emails = []

    # --------------------------------------------------------
    # Process all datasets
    # --------------------------------------------------------

    for filename, label in DATASETS:

        archive_path = os.path.join(
            RAW_DATA_DIR,
            filename
        )

        if not os.path.exists(
            archive_path
        ):

            print()
            print(
                f"ERROR: Dataset not found:"
            )

            print(
                archive_path
            )

            continue

        emails = process_archive(
            archive_path,
            label
        )

        all_emails.extend(
            emails
        )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    print()
    print(
        "Removing duplicate emails..."
    )

    unique_emails = []
    seen = set()

    for email_record in all_emails:

        text = email_record["text"]

        normalized = (
            text.lower()
            .strip()
        )

        if normalized not in seen:

            seen.add(
                normalized
            )

            unique_emails.append(
                email_record
            )

    duplicates_removed = (
        len(all_emails)
        - len(unique_emails)
    )

    # --------------------------------------------------------
    # Count labels
    # --------------------------------------------------------

    ham_count = sum(
        1
        for item in unique_emails
        if item["label"] == "ham"
    )

    spam_count = sum(
        1
        for item in unique_emails
        if item["label"] == "spam"
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "text",
                "label"
            ]
        )

        writer.writeheader()

        writer.writerows(
            unique_emails
        )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print()
    print("=" * 50)
    print("   DATASET PREPARATION COMPLETE")
    print("=" * 50)

    print(
        f"Successfully processed: "
        f"{stats['processed']}"
    )

    print(
        f"Parse errors handled: "
        f"{stats['parse_errors']}"
    )

    print(
        f"Skipped files: "
        f"{stats['skipped']}"
    )

    print(
        f"Duplicates removed: "
        f"{duplicates_removed}"
    )

    print(
        f"Final dataset size: "
        f"{len(unique_emails)}"
    )

    print(
        f"Ham emails: "
        f"{ham_count}"
    )

    print(
        f"Spam emails: "
        f"{spam_count}"
    )

    print()
    print(
        "Dataset saved to:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()