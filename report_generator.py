"""
PDF investigation report builder (ReportLab).

build_report_pdf() only draws a PDF from data that the Flask route
has already collected from the database and the real analyzers.
Nothing in the report is invented: if an evidence file could not be
analyzed, the report says so.
"""

from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


LEVEL_COLORS = {
    "HIGH": colors.HexColor("#b91c1c"),
    "MEDIUM": colors.HexColor("#b45309"),
    "LOW": colors.HexColor("#15803d"),
}

GREY = colors.HexColor("#64748b")
LIGHT = colors.HexColor("#f1f5f9")
LINE = colors.HexColor("#cbd5e1")


def _clean(value, default="N/A"):

    if value is None or value == "":
        return default

    return escape(str(value))


def _multiline(text, limit):

    text = str(text or "").strip()

    if len(text) > limit:
        text = text[:limit].rstrip() + " ..."

    return escape(text).replace("\n", "<br/>")


def _level_color(level):

    return LEVEL_COLORS.get(str(level).upper(), GREY)


def _page_footer(canvas, document):

    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)

    canvas.drawString(
        2 * cm,
        1.1 * cm,
        "AI-Powered Smart Evidence Analyzer for "
        "Cybercrime and Fraud Detection"
    )

    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.1 * cm,
        "Page " + str(document.page)
    )

    canvas.restoreState()


def build_report_pdf(report_path, case, items, overall, iocs=None):
    """
    case:    dict(case_id, title, description, investigator, created_at)
    items:   list of dict(filename, evidence_type, uploaded_at,
                          status, note, analysis, url_results)
    overall: dict(risk_level, risk_score, analyzed, total)
    iocs:    optional dict(summary, indicators) from ioc_extractor
    """

    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "T", parent=base["Title"], fontSize=21, leading=25,
        alignment=0, spaceAfter=4
    )

    sub_style = ParagraphStyle(
        "S", parent=base["Normal"], fontSize=9, textColor=GREY
    )

    h2 = ParagraphStyle(
        "H2", parent=base["Heading2"], fontSize=14,
        spaceBefore=16, spaceAfter=6
    )

    h3 = ParagraphStyle(
        "H3", parent=base["Heading3"], fontSize=11.5,
        spaceBefore=10, spaceAfter=4
    )

    body = ParagraphStyle(
        "B", parent=base["BodyText"], fontSize=10, leading=14
    )

    cell = ParagraphStyle(
        "C", parent=base["BodyText"], fontSize=9, leading=11.5
    )

    small = ParagraphStyle(
        "Sm", parent=base["BodyText"], fontSize=8.5, leading=11,
        textColor=colors.HexColor("#334155")
    )

    mono = ParagraphStyle(
        "M", parent=base["BodyText"], fontName="Courier",
        fontSize=8, leading=10, backColor=LIGHT,
        borderPadding=6, spaceBefore=4, spaceAfter=6
    )

    def grid(data, widths, header=False):

        table = Table(data, colWidths=widths, repeatRows=1 if header else 0)

        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]

        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT))
        else:
            style.append(("BACKGROUND", (0, 0), (0, -1), LIGHT))

        table.setStyle(TableStyle(style))

        return table

    def P(text, style=cell):
        return Paragraph(text, style)

    document = SimpleDocTemplate(
        report_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title="Investigation Report " + str(case.get("case_id", "")),
        author="AI-Powered Smart Evidence Analyzer"
    )

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(P("Digital Evidence Investigation Report", title_style))

    story.append(
        P(
            "Generated on "
            + datetime.now().strftime("%d %B %Y, %H:%M"),
            sub_style
        )
    )

    # --------------------------------------------------------
    # CASE DETAILS
    # --------------------------------------------------------

    story.append(P("1. Case Details", h2))

    story.append(grid([
        [P("<b>Case ID</b>"), P(_clean(case.get("case_id")))],
        [P("<b>Title</b>"), P(_clean(case.get("title")))],
        [P("<b>Description</b>"), P(_clean(case.get("description")))],
        [P("<b>Investigator / Team</b>"), P(_clean(case.get("investigator")))],
        [P("<b>Case created</b>"), P(_clean(case.get("created_at")))],
    ], [4.5 * cm, 12.5 * cm]))

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    story.append(P("2. Summary of Findings", h2))

    level = overall.get("risk_level", "NOT ASSESSED")

    level_text = (
        '<font color="%s"><b>%s</b></font>'
        % (_level_color(level).hexval().replace("0x", "#"), escape(str(level)))
    )

    story.append(grid([
        [P("<b>Overall risk level</b>"), P(level_text)],
        [P("<b>Highest risk score</b>"),
         P(_clean(
             str(overall.get("risk_score")) + " / 100"
             if overall.get("risk_score") is not None else None
         ))],
        [P("<b>Evidence items</b>"), P(str(overall.get("total", 0)))],
        [P("<b>Items analyzed automatically</b>"),
         P(str(overall.get("analyzed", 0)))],
    ], [4.5 * cm, 12.5 * cm]))

    story.append(Spacer(1, 4))

    story.append(
        P(
            "The overall level is the highest level found across the "
            "analyzed evidence. It is a decision-support indicator, "
            "not a legal finding.",
            small
        )
    )

    # --------------------------------------------------------
    # EVIDENCE REGISTER
    # --------------------------------------------------------

    story.append(P("3. Evidence Register", h2))

    if items:

        rows = [[P("<b>#</b>"), P("<b>File</b>"), P("<b>Type</b>"),
                 P("<b>Uploaded</b>"), P("<b>Risk</b>")]]

        for number, item in enumerate(items, start=1):

            analysis = item.get("analysis") or {}

            risk_cell = (
                _clean(
                    str(analysis.get("risk_level"))
                    + " ("
                    + str(analysis.get("risk_score"))
                    + ")"
                )
                if analysis else "Not analyzed"
            )

            rows.append([
                P(str(number)),
                P(_clean(item.get("filename"))),
                P(_clean(item.get("evidence_type"))),
                P(_clean(item.get("uploaded_at"))),
                P(risk_cell),
            ])

        story.append(
            grid(rows, [0.9 * cm, 6 * cm, 3 * cm, 4 * cm, 3.1 * cm], True)
        )

    else:

        story.append(
            P("No evidence has been uploaded for this case.", body)
        )

    # --------------------------------------------------------
    # DETAILED FINDINGS
    # --------------------------------------------------------

    # --------------------------------------------------------
    # INDICATORS OF COMPROMISE
    # --------------------------------------------------------

    story.append(P("4. Indicators of Compromise (IOCs)", h2))

    indicators = (iocs or {}).get("indicators") or []

    if indicators:

        summary = iocs.get("summary", {})

        story.append(
            P(
                "%d indicator(s) were extracted from the analyzed evidence: "
                "%d URL(s), %d domain(s), %d IP address(es) and "
                "%d email address(es)." % (
                    summary.get("total", len(indicators)),
                    summary.get("urls", 0),
                    summary.get("domains", 0),
                    summary.get("ips", 0),
                    summary.get("emails", 0),
                ),
                body
            )
        )

        story.append(Spacer(1, 4))

        shown = indicators[:60]

        ioc_rows = [[
            P("<b>Type</b>"), P("<b>Indicator</b>"),
            P("<b>Found in</b>"), P("<b>Count</b>"),
            P("<b>Assessment</b>")
        ]]

        for entry in shown:

            ioc_rows.append([
                P(_clean(entry.get("type"))),
                P(_clean(entry.get("value"))),
                P(_clean(", ".join(entry.get("sources") or []))),
                P(_clean(entry.get("count"))),
                P(_clean(entry.get("assessment"), "")),
            ])

        story.append(
            grid(
                ioc_rows,
                [2.3 * cm, 5.3 * cm, 3.3 * cm, 1.6 * cm, 4.5 * cm],
                True
            )
        )

        if len(indicators) > len(shown):

            story.append(
                P(
                    "Showing the first %d of %d indicators."
                    % (len(shown), len(indicators)),
                    small
                )
            )

    else:

        story.append(
            P(
                "No indicators (URLs, domains, IP addresses or email "
                "addresses) were found in the analyzed evidence.",
                body
            )
        )

    story.append(P("5. Detailed Findings", h2))

    if not items:

        story.append(P("There is no evidence to analyze.", body))

    for number, item in enumerate(items, start=1):

        analysis = item.get("analysis")

        block = [
            P(
                "5.%d  %s  <font color='#64748b' size='9'>(%s)</font>"
                % (
                    number,
                    _clean(item.get("filename")),
                    _clean(item.get("evidence_type")),
                ),
                h3
            )
        ]

        if not analysis:

            block.append(
                P(
                    _clean(
                        item.get("note"),
                        "This evidence was not analyzed automatically."
                    ),
                    body
                )
            )

            story.append(KeepTogether(block))

            continue

        item_level = analysis.get("risk_level", "UNKNOWN")

        block.append(grid([
            [P("<b>Risk score</b>"),
             P("%s / 100" % _clean(analysis.get("risk_score")))],
            [P("<b>Risk level</b>"),
             P('<font color="%s"><b>%s</b></font>' % (
                 _level_color(item_level).hexval().replace("0x", "#"),
                 _clean(item_level)))],
            [P("<b>Classification</b>"),
             P(_clean(analysis.get("classification")))],
            [P("<b>Subject</b>"),
             P(_clean(analysis.get("subject"), "Not detected"))],
            [P("<b>ML model (supporting signal)</b>"),
             P(_clean(analysis.get("ml_prediction"), "unknown"))],
            [P("<b>Credential request</b>"),
             P("Detected" if analysis.get("credential_request") else "Not detected")],
            [P("<b>Payment request</b>"),
             P("Detected" if analysis.get("payment_request") else "Not detected")],
            [P("<b>Urgent language</b>"),
             P("Detected" if analysis.get("urgent_request") else "Not detected")],
        ] + (
            [[P("<b>OCR confidence</b>"),
              P("%s%%" % _clean(analysis.get("ocr_confidence")))]]
            if analysis.get("ocr_confidence") is not None else []
        ), [5.5 * cm, 11.5 * cm]))

        pdf_info = analysis.get("pdf_info")

        if pdf_info:

            def yes_no(flag):
                return "Yes" if flag else "No"

            meta = pdf_info.get("metadata") or {}

            pdf_rows = [
                [P("<b>Pages</b>"),
                 P("%s (%s analyzed)" % (
                     _clean(pdf_info.get("pages")),
                     _clean(pdf_info.get("pages_analyzed"))))],
                [P("<b>Contains JavaScript</b>"),
                 P(yes_no(pdf_info.get("has_javascript")))],
                [P("<b>Contains launch action</b>"),
                 P(yes_no(pdf_info.get("has_launch_action")))],
                [P("<b>Contains embedded files</b>"),
                 P(yes_no(pdf_info.get("has_embedded_files")))],
                [P("<b>Clickable links</b>"),
                 P(_clean(pdf_info.get("link_count")))],
            ]

            for label, key in (
                ("Title", "title"),
                ("Author", "author"),
                ("Created with", "creator"),
                ("Created", "created"),
            ):

                if meta.get(key):
                    pdf_rows.append([
                        P("<b>%s</b>" % label),
                        P(_clean(meta.get(key)))
                    ])

            block.append(Spacer(1, 4))
            block.append(P("<b>PDF structure</b>", small))
            block.append(grid(pdf_rows, [5.5 * cm, 11.5 * cm]))

        keywords = analysis.get("suspicious_keywords") or []

        block.append(P("<b>Suspicious keywords</b>", small))
        block.append(
            P(
                escape(", ".join(str(k) for k in keywords))
                if keywords else "None detected",
                small
            )
        )

        factors = analysis.get("risk_factors") or []

        if factors:

            block.append(Spacer(1, 4))
            block.append(KeepTogether([P("<b>Why this score</b>", small), grid(
                [[P("<b>Factor</b>"), P("<b>Points</b>")]] + [
                    [P(_clean(f.get("factor"))),
                     P("+%s" % _clean(f.get("points"), "0"))]
                    for f in factors
                ],
                [13 * cm, 4 * cm],
                True
            )]))

        url_results = item.get("url_results") or []

        if url_results:

            block.append(Spacer(1, 4))
            block.append(KeepTogether([P("<b>URLs found and their assessment</b>", small), grid(
                [[P("<b>URL</b>"), P("<b>Result</b>")]] + [
                    [P(_clean(u.get("url"))),
                     P("%s (%s/100)" % (
                         _clean(u.get("classification")),
                         _clean(u.get("risk_score"))))]
                    for u in url_results
                ],
                [10.5 * cm, 6.5 * cm],
                True
            )]))

        for warning in analysis.get("warnings") or []:

            block.append(Spacer(1, 3))
            block.append(P("Note: " + _clean(warning), small))

        excerpt = analysis.get("extracted_text") or item.get("text_excerpt")

        if excerpt:

            block.append(Spacer(1, 4))

            block.append(KeepTogether([
                P(
                    "<b>Extracted text (excerpt)</b>"
                    if analysis.get("ocr_confidence") is not None
                    else "<b>Content (excerpt)</b>",
                    small
                ),
                Paragraph(_multiline(excerpt, 900), mono)
            ]))

        story.append(block[0])
        story.extend(block[1:])

    # --------------------------------------------------------
    # METHOD AND LIMITATIONS
    # --------------------------------------------------------

    story.append(P("6. Method and Limitations", h2))

    for line in [
        "Risk scores come from an explainable rule-based engine: "
        "suspicious keywords, URLs, credential, payment and urgent "
        "language indicators, plus the email classifier's output as "
        "a supporting signal. Every point in a score is listed above.",

        "The email classifier is a TF-IDF + Linear SVM model trained on "
        "a 5,673-email dataset. On its held-out test set (1,135 emails) "
        "it reached 99.56% accuracy, 99.17% precision, 99.45% recall "
        "and 99.31% F1. These figures describe that email dataset only "
        "and do not guarantee accuracy on other kinds of messages.",

        "Text in images is read with OCR (Tesseract) and may contain "
        "mistakes, especially on low-quality images.",

        "URLs are assessed from their structure only. No website was "
        "visited or contacted.",

        "Indicators are found with pattern matching. They can include "
        "false positives (for example a version number that looks like "
        "an IP address) and should be checked by the investigator.",

        "Results support an investigator's judgement and should be "
        "verified against the original evidence.",
    ]:

        story.append(P("&bull; " + escape(line), body))

    story.append(Spacer(1, 14))

    story.append(
        P(
            "Generated by AI-Powered Smart Evidence Analyzer for "
            "Cybercrime and Fraud Detection.",
            sub_style
        )
    )

    document.build(
        story,
        onFirstPage=_page_footer,
        onLaterPages=_page_footer
    )