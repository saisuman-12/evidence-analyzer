// ============================================================
// AI SMART EVIDENCE ANALYZER
// FRONTEND SCRIPT
// ============================================================


// ============================================================
// GLOBAL VARIABLES
// ============================================================

let currentCaseId = "CASE-001";


// ============================================================
// DOM ELEMENTS
// ============================================================

const casesContainer = document.getElementById("casesContainer");

const totalCasesElement =
    document.getElementById("totalCases");

const totalEvidenceElement =
    document.getElementById("totalEvidence");

const caseModal =
    document.getElementById("caseModal");

const closeCaseModal =
    document.getElementById("closeCaseModal");

const cancelCaseButton =
    document.getElementById("cancelCaseButton");

const caseForm =
    document.getElementById("caseForm");

const caseTitle =
    document.getElementById("caseTitle");

const caseDescription =
    document.getElementById("caseDescription");

const investigator =
    document.getElementById("investigator");

const fileInput =
    document.getElementById("evidenceFile");

const uploadButton =
    document.getElementById("uploadButton");


// ============================================================
// PAGE LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadCases();

        setupCaseModal();

        setupEvidenceUpload();

    }
);


// ============================================================
// LOAD CASES
// ============================================================

async function loadCases() {

    try {

        const response =
            await fetch("/api/cases");

        const data =
            await response.json();

        console.log(
            "Cases loaded:",
            data
        );


        if (!data.success) {

            showCasesError(
                data.message ||
                "Unable to load cases."
            );

            return;
        }


        displayCases(
            data.cases
        );


        updateDashboardStats(
            data.cases
        );


        updateReportsCount();

    }

    catch (error) {

        console.error(
            "Error loading cases:",
            error
        );


        showCasesError(
            "Unable to load cases."
        );

    }

}


// ============================================================
// DISPLAY CASES
// ============================================================

function displayCases(cases) {

    if (!casesContainer) {
        return;
    }


    if (!cases || cases.length === 0) {

        casesContainer.innerHTML = `

            <div class="empty-state">

                <div class="empty-icon">
                    ◌
                </div>

                <h3>
                    No investigations yet
                </h3>

                <p>
                    Create a case to begin your investigation.
                </p>

            </div>

        `;

        return;
    }


    let html = "";


    cases.forEach(
        function (caseItem) {

            const evidenceList =
                caseItem.evidence || [];


            html += `

                <div class="case-card">

                    <div class="case-card-header">

                        <div>

                            <span class="case-id">
                                ${escapeHtml(
                                    caseItem.case_id
                                )}
                            </span>

                            <h3>
                                ${escapeHtml(
                                    caseItem.title
                                )}
                            </h3>

                        </div>

                        <span class="case-status">
                            Active
                        </span>

                    </div>


                    <p class="case-description">
                        ${escapeHtml(
                            caseItem.description || ""
                        )}
                    </p>


                    <div class="case-meta">

                        <span>
                            Team:
                            ${escapeHtml(
                                caseItem.investigator ||
                                "N/A"
                            )}
                        </span>

                        <span>
                            Evidence:
                            ${evidenceList.length}
                        </span>

                        <button
                            type="button"
                            class="analyze-evidence-button generate-report-button"
                            onclick="generateCaseReport(
                                '${escapeJs(caseItem.case_id)}',
                                this
                            )"
                        >
                            Generate Report
                        </button>

                        <button
                            type="button"
                            class="analyze-evidence-button extract-ioc-button"
                            onclick="extractCaseIocs(
                                '${escapeJs(caseItem.case_id)}',
                                this
                            )"
                        >
                            Extract IOCs
                        </button>

                    </div>


                    <div class="case-evidence">

                        <h4>
                            Evidence
                        </h4>

                        ${renderEvidence(
                            evidenceList,
                            caseItem.case_id
                        )}

                    </div>

                </div>

            `;

        }
    );


    casesContainer.innerHTML =
        html;

}


// ============================================================
// RENDER EVIDENCE
// ============================================================

function renderEvidence(
    evidenceList,
    caseId
) {

    if (
        !evidenceList ||
        evidenceList.length === 0
    ) {

        return `

            <p class="no-evidence">
                No evidence uploaded yet.
            </p>

        `;

    }


    let html = "";


    evidenceList.forEach(
        function (evidence) {

            const filename =
                evidence.filename ||
                "Unknown file";


            const evidenceType =
                evidence.evidence_type ||
                "Unknown";


            const lowerName =
                filename.toLowerCase();


            const isImage =
                evidenceType
                    .toLowerCase()
                    .includes("image") ||

                lowerName.endsWith(".png") ||
                lowerName.endsWith(".jpg") ||
                lowerName.endsWith(".jpeg") ||
                lowerName.endsWith(".bmp") ||
                lowerName.endsWith(".webp");


            const isPdf =
                !isImage &&
                (
                    evidenceType
                        .toLowerCase()
                        .includes("pdf") ||

                    lowerName.endsWith(".pdf")
                );


            const isEmail =
                !isImage &&
                !isPdf &&
                (
                    evidenceType
                        .toLowerCase()
                        .includes("email") ||

                    evidenceType
                        .toLowerCase()
                        .includes("text") ||

                    lowerName.endsWith(".txt") ||
                    lowerName.endsWith(".eml")
                );


            let actionButton = "";


            if (isEmail) {

                actionButton = `
                    <button
                        class="analyze-evidence-button"
                        onclick="analyzeEmailEvidence(
                            ${evidence.id},
                            '${escapeJs(
                                evidence.filename
                            )}',
                            '${escapeJs(
                                caseId
                            )}',
                            '${escapeJs(
                                evidence.file_path || ""
                            )}'
                        )"
                    >
                        Analyze
                    </button>
                `;

            }

            else if (isImage) {

                actionButton = `
                    <button
                        class="analyze-evidence-button"
                        onclick="analyzeImageEvidence(
                            ${evidence.id},
                            '${escapeJs(
                                evidence.filename
                            )}',
                            '${escapeJs(
                                caseId
                            )}',
                            '${escapeJs(
                                evidence.file_path || ""
                            )}'
                        )"
                    >
                        Analyze Image
                    </button>
                `;

            }

            else if (isPdf) {

                actionButton = `
                    <button
                        class="analyze-evidence-button"
                        onclick="analyzePdfEvidence(
                            ${evidence.id},
                            '${escapeJs(
                                evidence.filename
                            )}',
                            '${escapeJs(
                                caseId
                            )}',
                            '${escapeJs(
                                evidence.file_path || ""
                            )}'
                        )"
                    >
                        Analyze PDF
                    </button>
                `;

            }


            html += `

                <div class="evidence-item">

                    <div class="evidence-icon">
                        ${isEmail ? "✉" : "▧"}
                    </div>


                    <div class="evidence-info">

                        <strong>
                            ${escapeHtml(
                                filename
                            )}
                        </strong>

                        <span>
                            ${escapeHtml(
                                evidenceType
                            )}
                        </span>

                    </div>


                    ${actionButton}

                </div>

            `;

        }
    );


    return html;

}


// ============================================================
// CHOOSE EVIDENCE BUTTON
// ============================================================

function setupEvidenceUpload() {

    // IMPORTANT:
    // Your HTML uses id="uploadButton"
    // and the actual file input uses id="evidenceFile".

    if (uploadButton && fileInput) {

        uploadButton.addEventListener(
            "click",
            function () {

                fileInput.click();

            }
        );

    }


    if (fileInput) {

        fileInput.addEventListener(
            "change",
            handleEvidenceUpload
        );

    }

}


// ============================================================
// HANDLE EVIDENCE UPLOAD
// ============================================================

async function handleEvidenceUpload(event) {

    const file =
        event.target.files[0];


    if (!file) {
        return;
    }


    console.log(
        "Selected evidence:",
        file.name
    );


    if (!currentCaseId) {

        showTemporaryMessage(
            "Please create or select a case first.",
            "error"
        );

        return;
    }


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    formData.append(
        "case_id",
        currentCaseId
    );


    try {

        showTemporaryMessage(
            "Uploading evidence...",
            "info"
        );


        const response =
            await fetch(
                "/api/evidence/upload",
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        console.log(
            "Upload response:",
            data
        );


        if (!response.ok || !data.success) {

            showTemporaryMessage(
                data.message ||
                "Evidence upload failed.",
                "error"
            );

            return;
        }


        // ----------------------------------------------------
        // DUPLICATE
        // ----------------------------------------------------

        if (data.duplicate) {

            showTemporaryMessage(
                "Evidence already exists for this case.",
                "info"
            );


            await loadCases();

            return;
        }


        // ----------------------------------------------------
        // SUCCESS
        // ----------------------------------------------------

        showTemporaryMessage(
            "Evidence uploaded successfully.",
            "success"
        );


        await loadCases();


        // ----------------------------------------------------
        // AUTOMATIC EMAIL ANALYSIS
        // ----------------------------------------------------

        // ----------------------------------------------------
// AUTOMATIC EVIDENCE ANALYSIS
// ----------------------------------------------------

const extension =
    file.name
        .split(".")
        .pop()
        .toLowerCase();


// EMAIL / TEXT ANALYSIS
if (
    extension === "txt" ||
    extension === "eml"
) {

    await analyzeUploadedEmail(
        data
    );

}


// IMAGE ANALYSIS
else if (
    extension === "png" ||
    extension === "jpg" ||
    extension === "jpeg"
) {

    await analyzeUploadedImage(
        data
    );

}


// PDF ANALYSIS
else if (extension === "pdf") {

    await analyzeUploadedPdf(
        data
    );

}
    }

    catch (error) {

        console.error(
            "Evidence upload error:",
            error
        );


        showTemporaryMessage(
            "Evidence upload failed. Check Flask server.",
            "error"
        );

    }


    // Allows selecting the same file again
    event.target.value = "";

}

// ============================================================
// ANALYZE UPLOADED IMAGE
// ============================================================

async function analyzeUploadedImage(uploadData) {

    console.log(
        "Analyzing uploaded image:",
        uploadData
    );

    const evidence =
        uploadData.evidence || uploadData;

    const requestBody = {

        evidence_id:
            evidence.id ||
            uploadData.evidence_id ||
            null,

        file_path:
            evidence.file_path ||
            uploadData.file_path ||
            "",

        filename:
            evidence.filename ||
            uploadData.filename ||
            "",

        case_id:
            evidence.case_id ||
            uploadData.case_id ||
            ""

    };

    console.log(
        "Sending image analysis request:",
        requestBody
    );

    if (!requestBody.filename) {

        showImageAnalysisError(
            "Uploaded image filename could not be determined."
        );

        return;
    }

    showResultLoading(
        "Reading text from the image (OCR). This can take a few seconds..."
    );

    try {

        const response =
            await fetch(
                "/api/analyze/image",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        )
                }
            );

        const data =
            await response.json();

        console.log(
            "Image Analysis:",
            data
        );

        if (
            !response.ok ||
            !data.success
        ) {

            showImageAnalysisError(
                data.error ||
                data.message ||
                "Unable to analyze image."
            );

            return;
        }

        displayImageAnalysis(
            data.analysis
        );

    }

    catch (error) {

        console.error(
            "Image analysis error:",
            error
        );

        showImageAnalysisError(
            "Unable to analyze image. Check Flask server."
        );
    }
}


// ============================================================
// DISPLAY IMAGE ANALYSIS
// ============================================================

function displayImageAnalysis(analysis, kind = "image") {

    if (!analysis) {
        return;
    }

    const panel =
        getResultBox("imageAnalysisResult");

    showOnlyResult("image");

    const riskLevel =
        analysis.risk_level || "UNKNOWN";

    const riskScore =
        analysis.risk_score ?? 0;

    const classification =
        analysis.classification ||
        "Unknown";

    const keywords =
        Array.isArray(analysis.suspicious_keywords)
            ? analysis.suspicious_keywords
            : [];

    const urls =
        Array.isArray(analysis.urls)
            ? analysis.urls
            : [];

    panel.innerHTML = `

        <div class="analysis-result-header">

            <h3>
                ${kind === "pdf" ? "PDF" : "Image"} Analysis Result
            </h3>

        </div>

        <div class="analysis-summary-grid">

            <div class="analysis-card">

                <span class="analysis-label">
                    Classification
                </span>

                <strong>
                    ${escapeHtml(classification)}
                </strong>

            </div>


            <div class="analysis-card">

                <span class="analysis-label">
                    Risk Score
                </span>

                <strong>
                    ${riskScore}/100
                </strong>

            </div>


            <div class="analysis-card">

                <span class="analysis-label">
                    Risk Level
                </span>

                <strong>
                    ${escapeHtml(riskLevel)}
                </strong>

            </div>


            ${
                analysis.ocr_confidence !== null &&
                analysis.ocr_confidence !== undefined
                ?
                `<div class="analysis-card">

                    <span class="analysis-label">
                        OCR Confidence
                    </span>

                    <strong>
                        ${Number(analysis.ocr_confidence).toFixed(0)}%
                    </strong>

                </div>`
                :
                (
                    analysis.pdf_info
                    ?
                    `<div class="analysis-card">

                        <span class="analysis-label">
                            Pages
                        </span>

                        <strong>
                            ${Number(analysis.pdf_info.pages || 0)}
                        </strong>

                    </div>`
                    :
                    ""
                )
            }

        </div>


        <div class="detected-section">

            <h3>
                Extracted Text
            </h3>

            <div class="detected-item">

                ${escapeHtml(
                    analysis.extracted_text ||
                    "No text extracted."
                )}

            </div>

        </div>


        <div class="security-indicators">

            <div class="indicator-card">

                <span>
                    Credential Request
                </span>

                <strong>
                    ${formatBoolean(
                        analysis.credential_request
                    )}
                </strong>

            </div>


            <div class="indicator-card">

                <span>
                    Payment Request
                </span>

                <strong>
                    ${formatBoolean(
                        analysis.payment_request
                    )}
                </strong>

            </div>


            <div class="indicator-card">

                <span>
                    Urgent Request
                </span>

                <strong>
                    ${formatBoolean(
                        analysis.urgent_request
                    )}
                </strong>

            </div>

        </div>


        <div class="detected-section">

            <h3>
                Detected URLs
            </h3>

            ${
                urls.length
                ?
                urls.map(
                    function(url) {

                        return `
                            <div class="detected-item">
                                ${escapeHtml(url)}
                            </div>
                        `;

                    }
                ).join("")
                :
                `<span class="empty-result">
                    No URLs detected.
                </span>`
            }

        </div>


        <div class="detected-section">

            <h3>
                Suspicious Keywords
            </h3>

            ${
                keywords.length
                ?
                keywords.map(
                    function(keyword) {

                        return `
                            <span class="keyword-tag">
                                ${escapeHtml(keyword)}
                            </span>
                        `;

                    }
                ).join("")
                :
                `<span class="empty-result">
                    No suspicious keywords detected.
                </span>`
            }

        </div>


        ${
            analysis.pdf_info
            ?
            `<div class="detected-section">
                <h3>PDF Structure</h3>
                <div class="detected-item">
                    JavaScript: <strong>${analysis.pdf_info.has_javascript ? "Yes" : "No"}</strong>
                    &nbsp;|&nbsp; Launch action: <strong>${analysis.pdf_info.has_launch_action ? "Yes" : "No"}</strong>
                    &nbsp;|&nbsp; Embedded files: <strong>${analysis.pdf_info.has_embedded_files ? "Yes" : "No"}</strong>
                    &nbsp;|&nbsp; Clickable links: <strong>${Number(analysis.pdf_info.link_count || 0)}</strong>
                </div>
            </div>`
            :
            ""
        }


        ${
            Array.isArray(analysis.warnings) &&
            analysis.warnings.length
            ?
            `<div class="detected-section">
                <h3>Notes</h3>
                ${analysis.warnings.map(
                    function(note) {
                        return `<div class="detected-item">${escapeHtml(note)}</div>`;
                    }
                ).join("")}
            </div>`
            :
            ""
        }


        <div class="detected-section">

            <h3>
                Risk Factors
            </h3>

            ${
                Array.isArray(analysis.risk_factors) &&
                analysis.risk_factors.length
                ?
                analysis.risk_factors.map(
                    function(item) {

                        return `
                            <div class="detected-item">
                                ${escapeHtml(item.factor)}
                                <strong>
                                    +${Number(item.points || 0)}
                                </strong>
                            </div>
                        `;

                    }
                ).join("")
                :
                `<span class="empty-result">
                    No significant risk factors detected.
                </span>`
            }

        </div>

    `;

    panel.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
}


// ============================================================
// IMAGE ANALYSIS ERROR
// ============================================================

function showImageAnalysisError(message) {

    showResultError(
        "Image Analysis Failed",
        message
    );
}

// ============================================================
// ANALYZE UPLOADED EMAIL
// ============================================================

async function analyzeUploadedEmail(
    uploadData
) {

    console.log(
        "Analyzing uploaded email:",
        uploadData
    );

    // --------------------------------------------------------
    // GET EVIDENCE INFORMATION
    // The upload API returns the information inside
    // uploadData.evidence
    // --------------------------------------------------------

    const evidence =
        uploadData.evidence || uploadData;

    const requestBody = {

        evidence_id:
            evidence.id ||
            uploadData.evidence_id ||
            null,

        file_path:
            evidence.file_path ||
            uploadData.file_path ||
            "",

        filename:
            evidence.filename ||
            uploadData.filename ||
            "",

        case_id:
            evidence.case_id ||
            uploadData.case_id ||
            ""

    };

    console.log(
        "Sending email analysis request:",
        requestBody
    );

    // --------------------------------------------------------
    // CHECK FILENAME
    // --------------------------------------------------------

    if (!requestBody.filename) {

        showAnalysisError(
            "Uploaded email filename could not be determined."
        );

        console.error(
            "Email filename missing:",
            uploadData
        );

        return;
    }

    // --------------------------------------------------------
    // SEND TO BACKEND
    // --------------------------------------------------------

    try {

        const response =
            await fetch(
                "/api/analyze/email",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        )

                }
            );

        const data =
            await response.json();

        console.log(
            "Email Analysis:",
            data
        );

        // ----------------------------------------------------
        // HANDLE ERROR
        // ----------------------------------------------------

        if (
            !response.ok ||
            !data.success
        ) {

            showAnalysisError(
                data.error ||
                data.message ||
                "Unable to analyze email."
            );

            return;
        }

        // ----------------------------------------------------
        // DISPLAY RESULT
        // ----------------------------------------------------

        displayEmailAnalysis(
            data.analysis
        );

    }

    catch (error) {

        console.error(
            "Email analysis error:",
            error
        );

        showAnalysisError(
            "Unable to analyze email. Check Flask server."
        );

    }

}

// ============================================================
// ANALYZE EXISTING EMAIL
// ============================================================

async function analyzeEmailEvidence(
    evidenceId,
    filename,
    caseId,
    filePath
) {

    console.log(
        "Starting email analysis:",
        {
            evidenceId,
            filename,
            caseId,
            filePath
        }
    );


    const requestBody = {

        evidence_id:
            evidenceId,

        filename:
            filename,

        case_id:
            caseId

    };


    if (filePath) {

        requestBody.file_path =
            filePath;

    }


    console.log(
        "Sending email analysis request:",
        requestBody
    );


    try {

        const response =
            await fetch(
                "/api/analyze/email",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        )

                }
            );


        const data =
            await response.json();


        console.log(
            "Email Analysis:",
            data
        );


        if (
            !response.ok ||
            !data.success
        ) {

            showAnalysisError(data.error || data.message || "Unable to analyze email.");

            return;
        }


        displayEmailAnalysis(
            data.analysis
        );

    }

    catch (error) {

        console.error(
            "Email analysis error:",
            error
        );


        showAnalysisError(
            "Unable to analyze email. Check Flask server."
        );

    }

}


// ============================================================
// DISPLAY EMAIL ANALYSIS
// ============================================================

function displayEmailAnalysis(
    analysis
) {

    // IMPORTANT:
    // Your HTML uses id="analysisResult"
    // after the previous fix.

    const panel =
        document.getElementById(
            "analysisResult"
        );


    if (!panel) {

        console.error(
            "analysisResult element not found."
        );

        return;
    }


    showOnlyResult("email");


    const prediction =
        analysis.prediction ||
        "phishing";


    const subject =
        analysis.subject ||
        "No subject detected";


    const urlCount =
        analysis.url_count ?? 0;


    const keywordCount =
        analysis.suspicious_keyword_count ?? 0;


    // --------------------------------------------------------
    // PREDICTION
    // --------------------------------------------------------

    const predictionElement =
        document.getElementById(
            "resultPrediction"
        );


    if (predictionElement) {

        predictionElement.textContent =
            prediction;

    }


    // --------------------------------------------------------
    // SUBJECT
    // --------------------------------------------------------

    const subjectElement =
        document.getElementById(
            "resultSubject"
        );


    if (subjectElement) {

        subjectElement.textContent =
            subject;

    }


    // --------------------------------------------------------
    // URL COUNT
    // --------------------------------------------------------

    const urlCountElement =
        document.getElementById(
            "resultUrlCount"
        );


    if (urlCountElement) {

        urlCountElement.textContent =
            urlCount;

    }


    // --------------------------------------------------------
    // KEYWORD COUNT
    // --------------------------------------------------------

    const keywordCountElement =
        document.getElementById(
            "resultKeywordCount"
        );


    if (keywordCountElement) {

        keywordCountElement.textContent =
            keywordCount;

    }


    // --------------------------------------------------------
    // PREDICTION BADGE
    // --------------------------------------------------------

    const predictionBadge =
        document.getElementById(
            "predictionBadge"
        );


    if (predictionBadge) {

        predictionBadge.textContent =
            prediction;


        predictionBadge.className =
            "prediction-badge " +
            getPredictionClass(
                prediction
            );

    }


    // --------------------------------------------------------
    // CREDENTIAL INDICATOR
    // --------------------------------------------------------

    const credentialIndicator =
        document.getElementById(
            "credentialIndicator"
        );

    const credentialStatus =
        document.getElementById(
            "credentialStatus"
        );


    if (credentialIndicator) {

        credentialIndicator.classList.toggle(
            "detected",
            Boolean(
                analysis.credential_request
            )
        );

    }


    if (credentialStatus) {

        credentialStatus.textContent =
            analysis.credential_request
            ? "Detected"
            : "Not Detected";

    }


    // --------------------------------------------------------
    // PAYMENT INDICATOR
    // --------------------------------------------------------

    const paymentIndicator =
        document.getElementById(
            "paymentIndicator"
        );

    const paymentStatus =
        document.getElementById(
            "paymentStatus"
        );


    if (paymentIndicator) {

        paymentIndicator.classList.toggle(
            "detected",
            Boolean(
                analysis.payment_request
            )
        );

    }


    if (paymentStatus) {

        paymentStatus.textContent =
            analysis.payment_request
            ? "Detected"
            : "Not Detected";

    }


    // --------------------------------------------------------
    // URGENT INDICATOR
    // --------------------------------------------------------

    const urgentIndicator =
        document.getElementById(
            "urgentIndicator"
        );

    const urgentStatus =
        document.getElementById(
            "urgentStatus"
        );


    if (urgentIndicator) {

        urgentIndicator.classList.toggle(
            "detected",
            Boolean(
                analysis.urgent_request
            )
        );

    }


    if (urgentStatus) {

        urgentStatus.textContent =
            analysis.urgent_request
            ? "Detected"
            : "Not Detected";

    }


    panel.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });

}


// ============================================================
// ANALYSIS ERROR
// ============================================================

function showAnalysisError(
    message
) {

    showResultError(
        "Email Analysis Failed",
        message
    );

}


// ============================================================
// GET PREDICTION CLASS
// ============================================================

function getPredictionClass(
    prediction
) {

    const value =
        String(prediction)
            .toLowerCase();


    if (
        value.includes("phishing") ||
        value.includes("malicious") ||
        value.includes("spam")
    ) {

        return "prediction-danger";

    }


    if (
        value.includes("suspicious")
    ) {

        return "prediction-warning";

    }


    return "prediction-safe";

}


// ============================================================
// CASE MODAL
// ============================================================

function setupCaseModal() {

    if (!caseModal) {
        return;
    }


    if (closeCaseModal) {

        closeCaseModal.addEventListener(
            "click",
            function () {

                caseModal.style.display =
                    "none";

            }
        );

    }


    if (cancelCaseButton) {

        cancelCaseButton.addEventListener(
            "click",
            function () {

                caseModal.style.display =
                    "none";

            }
        );

    }


    window.addEventListener(
        "click",
        function (event) {

            if (
                event.target ===
                caseModal
            ) {

                caseModal.style.display =
                    "none";

            }

        }
    );


    if (caseForm) {

        caseForm.addEventListener(
            "submit",
            createNewCase
        );

    }

}


// ============================================================
// NEW CASE BUTTON
// ============================================================

const newCaseButton =
    document.getElementById(
        "newCaseButton"
    );


if (newCaseButton) {

    newCaseButton.addEventListener(
        "click",
        function () {

            if (caseModal) {

                caseModal.style.display =
                    "flex";

            }

        }
    );

}


// ============================================================
// CREATE NEW CASE
// ============================================================

async function createNewCase(
    event
) {

    event.preventDefault();


    const title =
        caseTitle
        ? caseTitle.value.trim()
        : "";


    const description =
        caseDescription
        ? caseDescription.value.trim()
        : "";


    const investigatorValue =
        investigator
        ? investigator.value.trim()
        : "";


    if (!title) {

        showTemporaryMessage(
            "Case title is required.",
            "error"
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/api/cases",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            title:
                                title,

                            description:
                                description,

                            investigator:
                                investigatorValue ||
                                "AIML Project Team"

                        })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showTemporaryMessage(
                data.message ||
                "Unable to create case.",
                "error"
            );

            return;
        }


        currentCaseId =
            data.case_id;


        const currentCaseDisplay =
            document.getElementById(
                "currentCaseDisplay"
            );


        if (currentCaseDisplay) {

            currentCaseDisplay.textContent =
                `Current Case: ${currentCaseId}`;

        }


        if (caseModal) {

            caseModal.style.display =
                "none";

        }


        if (caseForm) {

            caseForm.reset();

        }


        showTemporaryMessage(
            `Case ${data.case_id} created successfully.`,
            "success"
        );


        await loadCases();

    }

    catch (error) {

        console.error(
            "Case creation error:",
            error
        );


        showTemporaryMessage(
            "Unable to create case.",
            "error"
        );

    }

}


// ============================================================
// DASHBOARD STATS
// ============================================================

function updateDashboardStats(
    cases
) {

    if (!cases) {
        return;
    }


    let evidenceCount = 0;


    cases.forEach(
        function (caseItem) {

            evidenceCount +=
                (
                    caseItem.evidence ||
                    []
                ).length;

        }
    );


    if (totalCasesElement) {

        totalCasesElement.textContent =
            cases.length;

    }


    if (totalEvidenceElement) {

        totalEvidenceElement.textContent =
            evidenceCount;

    }

}


// ============================================================
// CASE ERROR
// ============================================================

function showCasesError(
    message
) {

    if (!casesContainer) {
        return;
    }


    casesContainer.innerHTML = `

        <div class="empty-state">

            <div class="empty-icon">
                !
            </div>

            <h3>
                ${escapeHtml(message)}
            </h3>

        </div>

    `;

}


// ============================================================
// TEMPORARY MESSAGE
// ============================================================

function showTemporaryMessage(
    message,
    type = "info"
) {

    const existing =
        document.querySelector(
            ".temporary-message"
        );


    if (existing) {

        existing.remove();

    }


    const element =
        document.createElement(
            "div"
        );


    element.className =
        `temporary-message ${type}`;


    element.textContent =
        message;


    document.body.appendChild(
        element
    );


    setTimeout(
        function () {

            if (element) {

                element.remove();

            }

        },
        3000
    );

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


// ============================================================
// JAVASCRIPT STRING ESCAPE
// ============================================================

function escapeJs(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)

        .replace(
            /\\/g,
            "\\\\"
        )

        .replace(
            /'/g,
            "\\'"
        )

        .replace(
            /\r/g,
            "\\r"
        )

        .replace(
            /\n/g,
            "\\n"
        );

}



// ============================================================
// LIVE EMAIL / MESSAGE ANALYZER
// ============================================================

function setupLiveMessageAnalyzer() {
    // Prevent duplicate setup
    if (document.getElementById("liveMessageAnalyzer")) {
        return;
    }

    // Create analyzer container
    const analyzerContainer = document.createElement("div");
    analyzerContainer.id = "liveMessageAnalyzer";
    analyzerContainer.className = "live-message-analyzer";

    analyzerContainer.innerHTML = `
        <div class="live-analyzer-header">
            <div>
                <h2>Live Email / Message Analyzer</h2>
                <p>
                    Paste suspicious email or message content below
                    and analyze it using AI, NLP and security indicators.
                </p>
            </div>
        </div>

        <div class="live-analyzer-input">
            <label for="liveMessageInput">
                Email / Message Content
            </label>

            <textarea
                id="liveMessageInput"
                placeholder="Paste the suspicious email or message here..."
                rows="10"
            ></textarea>

            <div class="live-analyzer-actions">
                <button
                    type="button"
                    id="analyzeLiveMessageButton"
                    class="primary-button"
                >
                    Analyze Message
                </button>

                <button
                    type="button"
                    id="clearLiveMessageButton"
                    class="secondary-button"
                >
                    Clear
                </button>
            </div>
        </div>

        <div
            id="liveMessageLoading"
            class="live-message-loading"
            style="display:none;"
        >
            Analyzing message...
        </div>

        <div
            id="liveMessageError"
            class="live-message-error"
            style="display:none;"
        ></div>

        <div
            id="liveMessageResult"
            class="live-message-result"
            style="display:none;"
        >
            <div class="analysis-result-header">
                <h3>Analysis Result</h3>
            </div>

            <div class="analysis-summary-grid">

                <div class="analysis-card">
                    <span class="analysis-label">
                        ML Prediction
                    </span>

                    <strong id="liveMLPrediction">
                        -
                    </strong>
                </div>

                <div class="analysis-card">
                    <span class="analysis-label">
                        Classification
                    </span>

                    <strong id="liveClassification">
                        -
                    </strong>
                </div>

                <div class="analysis-card">
                    <span class="analysis-label">
                        Risk Score
                    </span>

                    <strong id="liveRiskScore">
                        -
                    </strong>
                </div>

                <div class="analysis-card">
                    <span class="analysis-label">
                        Risk Level
                    </span>

                    <strong id="liveRiskLevel">
                        -
                    </strong>
                </div>

            </div>

            <div class="security-indicators">

                <div class="indicator-card">
                    <span>Credential Request</span>
                    <strong id="liveCredentialRequest">
                        -
                    </strong>
                </div>

                <div class="indicator-card">
                    <span>Payment Request</span>
                    <strong id="livePaymentRequest">
                        -
                    </strong>
                </div>

                <div class="indicator-card">
                    <span>Urgent Request</span>
                    <strong id="liveUrgentRequest">
                        -
                    </strong>
                </div>

            </div>

            <div class="detected-section">
                <h3>Detected URLs</h3>

                <div id="liveDetectedUrls">
                    No URLs detected.
                </div>
            </div>

            <div class="detected-section">
                <h3>Suspicious Keywords</h3>

                <div id="liveSuspiciousKeywords">
                    No suspicious keywords detected.
                </div>
            </div>

        </div>
    `;

    // Try to place it inside the existing Analysis section
    const analysisSection =
        document.querySelector("#analyzersBody") ||
        document.querySelector("#analysis") ||
        document.querySelector(".analysis-section") ||
        document.querySelector('[data-section="analysis"]');

    if (analysisSection) {
        analysisSection.appendChild(analyzerContainer);
    } else {
        // Safe fallback: add to main content
        const mainContent =
            document.querySelector("main") ||
            document.querySelector(".main-content") ||
            document.body;

        mainContent.appendChild(analyzerContainer);
    }

    // Button events
    const analyzeButton =
        document.getElementById("analyzeLiveMessageButton");

    const clearButton =
        document.getElementById("clearLiveMessageButton");

    if (analyzeButton) {
        analyzeButton.addEventListener(
            "click",
            analyzeLiveMessage
        );
    }

    if (clearButton) {
        clearButton.addEventListener(
            "click",
            clearLiveMessage
        );
    }
}


// ============================================================
// ANALYZE LIVE MESSAGE
// ============================================================

async function analyzeLiveMessage() {

    const input =
        document.getElementById("liveMessageInput");

    const loading =
        document.getElementById("liveMessageLoading");

    const errorBox =
        document.getElementById("liveMessageError");

    const resultBox =
        document.getElementById("liveMessageResult");

    if (!input) {
        console.error(
            "Live message input not found."
        );
        return;
    }

    const message = input.value.trim();

    // Clear previous messages
    if (errorBox) {
        errorBox.style.display = "none";
        errorBox.textContent = "";
    }

    if (resultBox) {
        resultBox.style.display = "none";
    }

    // Validate
    if (!message) {

        if (errorBox) {
            errorBox.textContent =
                "Please enter or paste a message first.";

            errorBox.style.display = "block";
        }

        return;
    }

    // Show loading
    if (loading) {
        loading.style.display = "block";
    }

    try {

        const response = await fetch(
            "/api/analyze/email-text",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.error ||
                "Message analysis failed."
            );
        }

        displayLiveMessageAnalysis(
            data.analysis
        );

    } catch (error) {

        console.error(
            "Live message analysis error:",
            error
        );

        if (errorBox) {

            errorBox.textContent =
                error.message ||
                "Unable to analyze the message.";

            errorBox.style.display = "block";
        }

    } finally {

        if (loading) {
            loading.style.display = "none";
        }
    }
}


// ============================================================
// DISPLAY ANALYSIS RESULT
// ============================================================

function displayLiveMessageAnalysis(
    analysis
) {

    const resultBox =
        document.getElementById(
            "liveMessageResult"
        );

    if (!resultBox) {
        return;
    }

    const mlPrediction =
        document.getElementById(
            "liveMLPrediction"
        );

    const classification =
        document.getElementById(
            "liveClassification"
        );

    const riskScore =
        document.getElementById(
            "liveRiskScore"
        );

    const riskLevel =
        document.getElementById(
            "liveRiskLevel"
        );

    const credentialRequest =
        document.getElementById(
            "liveCredentialRequest"
        );

    const paymentRequest =
        document.getElementById(
            "livePaymentRequest"
        );

    const urgentRequest =
        document.getElementById(
            "liveUrgentRequest"
        );

    const urlsContainer =
        document.getElementById(
            "liveDetectedUrls"
        );

    const keywordsContainer =
        document.getElementById(
            "liveSuspiciousKeywords"
        );


    // --------------------------------------------------------
    // BASIC RESULTS
    // --------------------------------------------------------

    if (mlPrediction) {
        mlPrediction.textContent =
            formatPrediction(
                analysis.ml_prediction
            );
    }

    if (classification) {
        classification.textContent =
            analysis.classification ||
            "Unknown";
    }

    if (riskScore) {
        riskScore.textContent =
            `${analysis.risk_score ?? 0}/100`;
    }

    if (riskLevel) {

        riskLevel.textContent =
            analysis.risk_level ||
            "UNKNOWN";

        riskLevel.className =
            "risk-" +
            String(
                analysis.risk_level || "unknown"
            ).toLowerCase();
    }


    // --------------------------------------------------------
    // SECURITY INDICATORS
    // --------------------------------------------------------

    if (credentialRequest) {
        credentialRequest.textContent =
            formatBoolean(
                analysis.credential_request
            );
    }

    if (paymentRequest) {
        paymentRequest.textContent =
            formatBoolean(
                analysis.payment_request
            );
    }

    if (urgentRequest) {
        urgentRequest.textContent =
            formatBoolean(
                analysis.urgent_request
            );
    }


    // --------------------------------------------------------
    // DETECTED URLS
    // --------------------------------------------------------

    if (urlsContainer) {

        const urls =
            Array.isArray(analysis.urls)
                ? analysis.urls
                : [];

        if (urls.length === 0) {

            urlsContainer.innerHTML =
                `<span class="empty-result">
                    No URLs detected.
                </span>`;

        } else {

            urlsContainer.innerHTML =
                urls.map(
                    function(url) {

                        return `
                            <div class="detected-item">
                                ${escapeHtmlLive(url)}
                            </div>
                        `;
                    }
                ).join("");
        }
    }


    // --------------------------------------------------------
    // SUSPICIOUS KEYWORDS
    // --------------------------------------------------------

    if (keywordsContainer) {

        const keywords =
            Array.isArray(
                analysis.suspicious_keywords
            )
                ? analysis.suspicious_keywords
                : [];

        if (keywords.length === 0) {

            keywordsContainer.innerHTML =
                `<span class="empty-result">
                    No suspicious keywords detected.
                </span>`;

        } else {

            keywordsContainer.innerHTML =
                keywords.map(
                    function(keyword) {

                        return `
                            <span
                                class="keyword-tag"
                            >
                                ${escapeHtmlLive(
                                    keyword
                                )}
                            </span>
                        `;
                    }
                ).join("");
        }
    }


    // Show result
    resultBox.style.display = "block";

    // Scroll to result
    resultBox.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
}


// ============================================================
// CLEAR LIVE MESSAGE
// ============================================================

function clearLiveMessage() {

    const input =
        document.getElementById(
            "liveMessageInput"
        );

    const resultBox =
        document.getElementById(
            "liveMessageResult"
        );

    const errorBox =
        document.getElementById(
            "liveMessageError"
        );

    if (input) {
        input.value = "";
    }

    if (resultBox) {
        resultBox.style.display = "none";
    }

    if (errorBox) {
        errorBox.style.display = "none";
        errorBox.textContent = "";
    }
}


// ============================================================
// HELPER FUNCTIONS
// ============================================================

function formatPrediction(
    prediction
) {

    if (!prediction) {
        return "Unknown";
    }

    const value =
        String(prediction).toLowerCase();

    if (value === "spam") { return "Suspicious Pattern Detected"; } if (value === "ham") { return "No Strong Threat Indicators"; } if (value.includes("suspicious pattern")) { return "Suspicious Pattern Detected"; } if (value.includes("no strong threat")) { return "No Strong Threat Indicators"; } return "Unknown";
}


function formatBoolean(
    value
) {

    return value
        ? "Detected"
        : "Not Detected";
}


function escapeHtmlLive(
    value
) {

    if (value === null ||
        value === undefined) {

        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// INITIALIZE LIVE ANALYZER
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        setupLiveMessageAnalyzer();

    }
);


// ============================================================
// LIVE URL ANALYZER
// ============================================================

function setupLiveURLAnalyzer() {

    // Prevent duplicate setup
    if (document.getElementById("liveURLAnalyzer")) {
        return;
    }

    const analyzerContainer = document.createElement("div");

    analyzerContainer.id = "liveURLAnalyzer";
    analyzerContainer.className = "live-url-analyzer";

    analyzerContainer.innerHTML = `
        <div class="live-url-header">
            <div>
                <h2>Live URL Analyzer</h2>
                <p>
                    Analyze a suspicious URL using explainable
                    security features and risk scoring.
                </p>
            </div>
        </div>

        <div class="live-url-input-area">

            <label for="liveURLInput">
                URL to Analyze
            </label>

            <input
                type="text"
                id="liveURLInput"
                placeholder="Example: http://example-login-verification.com"
            />

            <div class="live-url-actions">

                <button
                    type="button"
                    id="analyzeURLButton"
                    class="primary-button"
                >
                    Analyze URL
                </button>

                <button
                    type="button"
                    id="clearURLButton"
                    class="secondary-button"
                >
                    Clear
                </button>

            </div>

        </div>

        <div
            id="liveURLLoading"
            class="live-url-loading"
            style="display:none;"
        >
            Analyzing URL...
        </div>

        <div
            id="liveURLError"
            class="live-url-error"
            style="display:none;"
        ></div>

        <div
            id="liveURLResult"
            class="live-url-result"
            style="display:none;"
        >

            <div class="url-result-header">
                <h3>URL Analysis Result</h3>
            </div>

            <div class="url-summary-grid">

                <div class="url-analysis-card">
                    <span>Classification</span>
                    <strong id="urlClassification">-</strong>
                </div>

                <div class="url-analysis-card">
                    <span>Risk Score</span>
                    <strong id="urlRiskScore">-</strong>
                </div>

                <div class="url-analysis-card">
                    <span>Risk Level</span>
                    <strong id="urlRiskLevel">-</strong>
                </div>

                <div class="url-analysis-card">
                    <span>Domain</span>
                    <strong id="urlDomain">-</strong>
                </div>

            </div>

            <div class="url-result-section">

                <h3>Risk Factors</h3>

                <div id="urlRiskFactors">
                    No risk factors detected.
                </div>

            </div>

            <div class="url-result-section">

                <h3>Suspicious Keywords</h3>

                <div id="urlSuspiciousKeywords">
                    No suspicious keywords detected.
                </div>

            </div>

            <div class="url-result-section">

                <h3>URL Features</h3>

                <div
                    id="urlFeatures"
                    class="url-features-grid"
                ></div>

            </div>

        </div>
    `;

    // Try to place inside Analysis section
    const analysisSection =
        document.querySelector("#analyzersBody") ||
        document.querySelector("#analysis") ||
        document.querySelector(".analysis-section") ||
        document.querySelector('[data-section="analysis"]');

    if (analysisSection) {

        analysisSection.appendChild(
            analyzerContainer
        );

    } else {

        const mainContent =
            document.querySelector("main") ||
            document.querySelector(".main-content") ||
            document.body;

        mainContent.appendChild(
            analyzerContainer
        );
    }

    // Button events
    const analyzeButton =
        document.getElementById(
            "analyzeURLButton"
        );

    const clearButton =
        document.getElementById(
            "clearURLButton"
        );

    if (analyzeButton) {

        analyzeButton.addEventListener(
            "click",
            analyzeLiveURL
        );

    }

    if (clearButton) {

        clearButton.addEventListener(
            "click",
            clearLiveURL
        );

    }

    // Allow Enter key to analyze
    const input =
        document.getElementById(
            "liveURLInput"
        );

    if (input) {

        input.addEventListener(
            "keydown",
            function(event) {

                if (event.key === "Enter") {

                    event.preventDefault();

                    analyzeLiveURL();
                }

            }
        );

    }
}


// ============================================================
// ANALYZE URL
// ============================================================

async function analyzeLiveURL() {

    const input =
        document.getElementById(
            "liveURLInput"
        );

    const loading =
        document.getElementById(
            "liveURLLoading"
        );

    const errorBox =
        document.getElementById(
            "liveURLError"
        );

    const resultBox =
        document.getElementById(
            "liveURLResult"
        );

    if (!input) {
        return;
    }

    const url = input.value.trim();

    // Clear old messages
    if (errorBox) {

        errorBox.style.display = "none";
        errorBox.textContent = "";
    }

    if (resultBox) {

        resultBox.style.display = "none";
    }

    if (!url) {

        if (errorBox) {

            errorBox.textContent =
                "Please enter a URL first.";

            errorBox.style.display =
                "block";
        }

        return;
    }

    if (loading) {

        loading.style.display =
            "block";
    }

    try {

        const response = await fetch(
            "/api/analyze/url",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.error ||
                data.message ||
                "URL analysis failed."
            );
        }

        displayLiveURLAnalysis(
            data.analysis
        );

    } catch (error) {

        console.error(
            "URL analysis error:",
            error
        );

        if (errorBox) {

            errorBox.textContent =
                error.message ||
                "Unable to analyze URL.";

            errorBox.style.display =
                "block";
        }

    } finally {

        if (loading) {

            loading.style.display =
                "none";
        }
    }
}


// ============================================================
// DISPLAY URL ANALYSIS
// ============================================================

function displayLiveURLAnalysis(
    analysis
) {

    const resultBox =
        document.getElementById(
            "liveURLResult"
        );

    if (!resultBox || !analysis) {
        return;
    }

    const classification =
        document.getElementById(
            "urlClassification"
        );

    const riskScore =
        document.getElementById(
            "urlRiskScore"
        );

    const riskLevel =
        document.getElementById(
            "urlRiskLevel"
        );

    const domain =
        document.getElementById(
            "urlDomain"
        );

    const riskFactors =
        document.getElementById(
            "urlRiskFactors"
        );

    const suspiciousKeywords =
        document.getElementById(
            "urlSuspiciousKeywords"
        );

    const featuresContainer =
        document.getElementById(
            "urlFeatures"
        );

    if (classification) {

        classification.textContent =
            analysis.classification ||
            "Unknown";
    }

    if (riskScore) {

        riskScore.textContent =
            analysis.risk_score !== undefined
                ? analysis.risk_score
                : "-";
    }

    if (riskLevel) {

        riskLevel.textContent =
            analysis.risk_level ||
            "Unknown";
    }

    if (domain) {

        domain.textContent =
            analysis.domain ||
            "-";
    }

    // --------------------------------------------------------
    // Risk Factors
    // --------------------------------------------------------

    if (riskFactors) {

        const factors =
            analysis.risk_factors || [];

        if (factors.length === 0) {

            riskFactors.textContent =
                "No significant risk factors detected.";

        } else {

            riskFactors.innerHTML =
                factors.map(
                    function(item) {

                        return `
                            <div class="url-risk-factor">
                                <span>
                                    ${escapeURLText(
                                        item.factor
                                    )}
                                </span>

                                <strong>
                                    +${Number(
                                        item.points || 0
                                    )}
                                </strong>
                            </div>
                        `;
                    }
                ).join("");
        }
    }

    // --------------------------------------------------------
    // Suspicious Keywords
    // --------------------------------------------------------

    if (suspiciousKeywords) {

        const keywords =
            analysis.suspicious_keywords || [];

        if (keywords.length === 0) {

            suspiciousKeywords.textContent =
                "No suspicious keywords detected.";

        } else {

            suspiciousKeywords.innerHTML =
                keywords.map(
                    function(keyword) {

                        return `
                            <span class="url-keyword-tag">
                                ${escapeURLText(
                                    keyword
                                )}
                            </span>
                        `;
                    }
                ).join("");
        }
    }

    // --------------------------------------------------------
    // URL Features
    // --------------------------------------------------------

    if (featuresContainer) {

        const features =
            analysis.features || {};

        featuresContainer.innerHTML = "";

        Object.entries(features).forEach(
            function([key, value]) {

                const card =
                    document.createElement("div");

                card.className =
                    "url-feature-card";

                const label =
                    key
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, function(letter) {
                            return letter.toUpperCase();
                        });

                let displayValue = value;

                if (typeof value === "boolean") {

                    displayValue =
                        value
                            ? "Yes"
                            : "No";
                }

                card.innerHTML = `
                    <span>
                        ${escapeURLText(label)}
                    </span>

                    <strong>
                        ${escapeURLText(
                            String(displayValue)
                        )}
                    </strong>
                `;

                featuresContainer.appendChild(
                    card
                );
            }
        );
    }

    resultBox.style.display =
        "block";
}


// ============================================================
// CLEAR URL ANALYZER
// ============================================================

function clearLiveURL() {

    const input =
        document.getElementById(
            "liveURLInput"
        );

    const resultBox =
        document.getElementById(
            "liveURLResult"
        );

    const errorBox =
        document.getElementById(
            "liveURLError"
        );

    if (input) {

        input.value = "";
    }

    if (resultBox) {

        resultBox.style.display =
            "none";
    }

    if (errorBox) {

        errorBox.style.display =
            "none";

        errorBox.textContent =
            "";
    }
}


// ============================================================
// SAFE TEXT ESCAPE
// ============================================================

function escapeURLText(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// URL ANALYZER STYLES
// ============================================================

(function addLiveURLAnalyzerStyles() {

    if (
        document.getElementById(
            "liveURLAnalyzerStyles"
        )
    ) {

        return;
    }

    const style =
        document.createElement("style");

    style.id =
        "liveURLAnalyzerStyles";

    style.textContent = `

        .live-url-analyzer {
            margin-top: 30px;
            padding: 24px;
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
        }

        .live-url-header h2 {
            margin: 0 0 8px;
        }

        .live-url-header p {
            margin: 0 0 20px;
            opacity: 0.75;
        }

        .live-url-input-area label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }

        #liveURLInput {
            width: 100%;
            box-sizing: border-box;
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.15);
            background: rgba(0,0,0,0.18);
            color: inherit;
            font-size: 15px;
        }

        .live-url-actions {
            display: flex;
            gap: 12px;
            margin-top: 14px;
        }

        .live-url-loading {
            margin-top: 16px;
            padding: 12px;
            border-radius: 10px;
            background: rgba(255,255,255,0.05);
        }

        .live-url-error {
            margin-top: 16px;
            padding: 12px;
            border-radius: 10px;
            background: rgba(255,0,0,0.08);
            border: 1px solid rgba(255,0,0,0.20);
        }

        .live-url-result {
            margin-top: 24px;
        }

        .url-summary-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-top: 16px;
        }

        .url-analysis-card {
            padding: 18px;
            border-radius: 12px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
        }

        .url-analysis-card span {
            display: block;
            font-size: 13px;
            opacity: 0.65;
            margin-bottom: 8px;
        }

        .url-analysis-card strong {
            display: block;
            font-size: 18px;
            word-break: break-word;
        }

        .url-result-section {
            margin-top: 22px;
        }

        .url-result-section h3 {
            margin-bottom: 12px;
        }

        .url-risk-factor {
            display: flex;
            justify-content: space-between;
            gap: 15px;
            padding: 11px 14px;
            margin-bottom: 8px;
            border-radius: 9px;
            background: rgba(255,255,255,0.04);
        }

        .url-risk-factor strong {
            white-space: nowrap;
        }

        .url-keyword-tag {
            display: inline-block;
            margin: 4px;
            padding: 6px 10px;
            border-radius: 20px;
            background: rgba(255,255,255,0.08);
            font-size: 13px;
        }

        .url-features-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
        }

        .url-feature-card {
            padding: 12px;
            border-radius: 9px;
            background: rgba(255,255,255,0.04);
        }

        .url-feature-card span {
            display: block;
            font-size: 12px;
            opacity: 0.6;
            margin-bottom: 5px;
        }

        .url-feature-card strong {
            word-break: break-word;
        }

        @media (max-width: 600px) {

            .live-url-actions {
                flex-direction: column;
            }

        }

    `;

    document.head.appendChild(style);

})();


// ============================================================
// INITIALIZE URL ANALYZER
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        setupLiveURLAnalyzer();

    }
);


// ============================================================
// RESULT PANEL HELPERS
// Separate boxes for email result, image result and errors,
// so one never overwrites the HTML of another.
// ============================================================

function getResultBox(id) {

    let box = document.getElementById(id);

    if (box) {
        return box;
    }

    box = document.createElement("section");

    box.id = id;
    box.className = "analysis-result-panel";
    box.style.display = "none";

    const emailPanel =
        document.getElementById("analysisResult");

    if (emailPanel && emailPanel.parentNode) {

        emailPanel.parentNode.insertBefore(
            box,
            emailPanel.nextSibling
        );

    } else {

        (
            document.querySelector("main") ||
            document.body
        ).appendChild(box);
    }

    return box;
}


function showOnlyResult(which) {

    const boxes = {
        email: document.getElementById("analysisResult"),
        image: document.getElementById("imageAnalysisResult"),
        error: document.getElementById("analysisErrorBox"),
        ioc: document.getElementById("iocResult")
    };

    Object.keys(boxes).forEach(
        function (key) {

            if (boxes[key]) {

                boxes[key].style.display =
                    key === which
                        ? "block"
                        : "none";
            }
        }
    );

    if (boxes[which]) {

        boxes[which].scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });
    }
}


function showResultLoading(message) {

    const box = getResultBox("analysisErrorBox");

    box.innerHTML = `
        <div class="analysis-error" style="color:inherit;">
            <h3>Analyzing...</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    showOnlyResult("error");
}


function showResultError(title, message) {

    const box = getResultBox("analysisErrorBox");

    box.innerHTML = `
        <div class="analysis-error">
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    showOnlyResult("error");
}


// ============================================================
// ANALYZE IMAGE BUTTON (evidence list)
// ============================================================

function analyzeImageEvidence(
    evidenceId,
    filename,
    caseId,
    filePath
) {

    return analyzeUploadedImage({
        evidence_id: evidenceId,
        filename: filename,
        case_id: caseId,
        file_path: filePath
    });
}


// ============================================================
// ANALYSIS MODULE CARDS (Email / URL / Image shortcuts)
// ============================================================

function setupModuleShortcuts() {

    const cards =
        document.querySelectorAll(".module");

    cards.forEach(
        function (card) {

            const heading = card.querySelector("h3");

            const name = heading
                ? heading.textContent.trim().toLowerCase()
                : "";

            card.style.cursor = "pointer";

            card.addEventListener(
                "click",
                function () {

                    if (name.startsWith("email")) {

                        focusAnalyzer(
                            "liveMessageAnalyzer",
                            "liveMessageInput"
                        );

                    }

                    else if (name.startsWith("url")) {

                        focusAnalyzer(
                            "liveURLAnalyzer",
                            "liveURLInput"
                        );

                    }

                    else if (name.startsWith("image")) {

                        const imageButton =
                            document.querySelector(
                                '.evidence-item button[onclick*="analyzeImageEvidence"]'
                            );

                        if (imageButton) {

                            imageButton.click();

                        } else {

                            showTemporaryMessage(
                                "Upload a PNG or JPG screenshot first.",
                                "info"
                            );

                            if (fileInput) {
                                fileInput.click();
                            }
                        }
                    }
                }
            );
        }
    );
}


function focusAnalyzer(containerId, inputId) {

    const container =
        document.getElementById(containerId);

    if (!container) {
        return;
    }

    container.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    const input = document.getElementById(inputId);

    if (input) {

        setTimeout(
            function () {
                input.focus();
            },
            400
        );
    }
}


document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupModuleShortcuts();

    }
);


// ============================================================
// GENERATE INVESTIGATION REPORT (PDF)
// ============================================================

async function generateCaseReport(caseId, button) {

    const originalText =
        button ? button.textContent : "";

    if (button) {

        button.disabled = true;

        button.textContent =
            "Generating report...";
    }

    showTemporaryMessage(
        "Generating report. Image analysis can take a few seconds...",
        "info"
    );

    try {

        const response = await fetch(
            "/api/reports/generate",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    case_id: caseId
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showTemporaryMessage(
                data.error ||
                data.message ||
                "Unable to generate report.",
                "error"
            );

            return;
        }

        showTemporaryMessage(
            "Report generated successfully.",
            "success"
        );

        if (button) {

            const oldLink =
                button.parentNode.querySelector(
                    ".report-link"
                );

            if (oldLink) {
                oldLink.remove();
            }

            const link =
                document.createElement("a");

            link.className = "report-link";
            link.href = data.report_url;
            link.target = "_blank";
            link.rel = "noopener";
            link.textContent = "Open report PDF";
            link.style.marginLeft = "12px";
            link.style.fontWeight = "600";

            button.insertAdjacentElement(
                "afterend",
                link
            );
        }

        window.open(
            data.report_url,
            "_blank"
        );

        updateReportsCount();

    }

    catch (error) {

        console.error(
            "Report generation error:",
            error
        );

        showTemporaryMessage(
            "Unable to generate report. Check Flask server.",
            "error"
        );

    }

    finally {

        if (button) {

            button.disabled = false;

            button.textContent = originalText;
        }
    }
}


async function updateReportsCount() {

    const element =
        document.getElementById("totalReports");

    if (!element) {
        return;
    }

    try {

        const response =
            await fetch("/api/reports/count");

        const data = await response.json();

        if (data && data.success) {

            element.textContent = data.count;
        }
    }

    catch (error) {

        console.error(
            "Report count error:",
            error
        );
    }
}


// ============================================================
// PDF ANALYSIS
// ============================================================

function analyzePdfEvidence(
    evidenceId,
    filename,
    caseId,
    filePath
) {

    return analyzeUploadedPdf({
        evidence_id: evidenceId,
        filename: filename,
        case_id: caseId,
        file_path: filePath
    });
}


async function analyzeUploadedPdf(uploadData) {

    const evidence =
        uploadData.evidence || uploadData;

    const requestBody = {

        evidence_id:
            evidence.id ||
            uploadData.evidence_id ||
            null,

        file_path:
            evidence.file_path ||
            uploadData.file_path ||
            "",

        filename:
            evidence.filename ||
            uploadData.filename ||
            "",

        case_id:
            evidence.case_id ||
            uploadData.case_id ||
            ""

    };

    if (!requestBody.filename) {

        showResultError(
            "PDF Analysis Failed",
            "Uploaded PDF filename could not be determined."
        );

        return;
    }

    showResultLoading(
        "Reading the PDF (text, links and structure). " +
        "Scanned pages are read with OCR, which can take a few seconds..."
    );

    try {

        const response = await fetch(
            "/api/analyze/pdf",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(requestBody)
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showResultError(
                "PDF Analysis Failed",
                data.error ||
                data.message ||
                "Unable to analyze PDF."
            );

            return;
        }

        displayImageAnalysis(
            data.analysis,
            "pdf"
        );

    }

    catch (error) {

        console.error(
            "PDF analysis error:",
            error
        );

        showResultError(
            "PDF Analysis Failed",
            "Unable to analyze PDF. Check Flask server."
        );

    }
}


// ============================================================
// IOC EXTRACTION (URLs, domains, IP addresses, emails)
// ============================================================

let lastIocData = null;


async function extractCaseIocs(caseId, button) {

    const originalText =
        button ? button.textContent : "";

    if (button) {

        button.disabled = true;

        button.textContent = "Extracting...";
    }

    showResultLoading(
        "Extracting indicators from all evidence. " +
        "Images and scanned PDFs are read with OCR, " +
        "which can take a few seconds..."
    );

    try {

        const response = await fetch(
            "/api/cases/" +
            encodeURIComponent(caseId) +
            "/iocs"
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            showResultError(
                "IOC Extraction Failed",
                data.error ||
                data.message ||
                "Unable to extract indicators."
            );

            return;
        }

        lastIocData = data;

        displayIocs(data);

    }

    catch (error) {

        console.error(
            "IOC extraction error:",
            error
        );

        showResultError(
            "IOC Extraction Failed",
            "Unable to extract indicators. Check Flask server."
        );

    }

    finally {

        if (button) {

            button.disabled = false;

            button.textContent = originalText;
        }
    }
}


function addIocStyles() {

    if (document.getElementById("iocStyles")) {
        return;
    }

    const style = document.createElement("style");

    style.id = "iocStyles";

    style.textContent = `

        .ioc-counts {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 12px 0 16px;
        }

        .ioc-count {
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid rgba(128,128,128,0.35);
            font-size: 14px;
        }

        .ioc-table-wrap {
            overflow-x: auto;
        }

        .ioc-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .ioc-table th,
        .ioc-table td {
            padding: 8px 10px;
            text-align: left;
            vertical-align: top;
            border-bottom: 1px solid rgba(128,128,128,0.3);
            word-break: break-word;
        }

        .ioc-table th {
            background: rgba(128,128,128,0.12);
        }

        .ioc-high {
            font-weight: 700;
            color: #b91c1c;
        }

        .ioc-actions {
            margin-top: 14px;
        }
    `;

    document.head.appendChild(style);
}


function displayIocs(data) {

    addIocStyles();

    const box = getResultBox("iocResult");

    const summary = data.summary || {};

    const indicators = data.indicators || [];

    const skipped = data.skipped || [];

    const rows = indicators.map(
        function (item) {

            const isHigh =
                item.risk_score !== null &&
                item.risk_score !== undefined &&
                item.risk_score >= 60;

            return `
                <tr>
                    <td>${escapeHtml(item.type)}</td>
                    <td>${escapeHtml(item.value)}</td>
                    <td>${escapeHtml((item.sources || []).join(", "))}</td>
                    <td>${Number(item.count || 0)}</td>
                    <td class="${isHigh ? "ioc-high" : ""}">
                        ${escapeHtml(item.assessment || "")}
                    </td>
                </tr>
            `;
        }
    ).join("");

    const skippedHtml = skipped.length
        ? `<div class="detected-section">
                <h3>Not scanned</h3>
                ${skipped.map(
                    function (entry) {
                        return `<div class="detected-item">
                            ${escapeHtml(entry.filename)}:
                            ${escapeHtml(entry.reason)}
                        </div>`;
                    }
                ).join("")}
           </div>`
        : "";

    box.innerHTML = `

        <div class="analysis-result-header">
            <h3>Indicators of Compromise (IOCs)</h3>
        </div>

        <div class="ioc-counts">
            <span class="ioc-count">
                URLs: <strong>${Number(summary.urls || 0)}</strong>
            </span>
            <span class="ioc-count">
                Domains: <strong>${Number(summary.domains || 0)}</strong>
            </span>
            <span class="ioc-count">
                IP addresses: <strong>${Number(summary.ips || 0)}</strong>
            </span>
            <span class="ioc-count">
                Email addresses: <strong>${Number(summary.emails || 0)}</strong>
            </span>
            <span class="ioc-count">
                Evidence scanned:
                <strong>${Number(summary.evidence_scanned || 0)}</strong>
            </span>
        </div>

        ${
            indicators.length
            ?
            `<div class="ioc-table-wrap">
                <table class="ioc-table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Indicator</th>
                            <th>Found in</th>
                            <th>Count</th>
                            <th>Assessment</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>

            <div class="ioc-actions">
                <button
                    type="button"
                    class="analyze-evidence-button"
                    onclick="downloadIocCsv()"
                >
                    Download CSV
                </button>
            </div>`
            :
            `<span class="empty-result">
                No URLs, domains, IP addresses or email addresses
                were found in the scanned evidence.
            </span>`
        }

        ${skippedHtml}

    `;

    showOnlyResult("ioc");
}


function csvCell(value) {

    let text = String(value ?? "");

    // Stops spreadsheet programs from running text as a formula.
    if (/^[=+\-@\t\r]/.test(text)) {
        text = "'" + text;
    }

    return '"' + text.replace(/"/g, '""') + '"';
}


function downloadIocCsv() {

    if (!lastIocData || !lastIocData.indicators) {
        return;
    }

    const lines = [
        ["Type", "Indicator", "Found in", "Count", "Assessment"]
            .map(csvCell)
            .join(",")
    ];

    lastIocData.indicators.forEach(
        function (item) {

            lines.push([
                item.type,
                item.value,
                (item.sources || []).join("; "),
                item.count,
                item.assessment || ""
            ].map(csvCell).join(","));
        }
    );

    const blob = new Blob(
        ["\ufeff" + lines.join("\r\n")],
        { type: "text/csv;charset=utf-8" }
    );

    const link = document.createElement("a");

    link.href = URL.createObjectURL(blob);

    link.download =
        "iocs_" + (lastIocData.case_id || "case") + ".csv";

    document.body.appendChild(link);

    link.click();

    link.remove();

    setTimeout(
        function () {
            URL.revokeObjectURL(link.href);
        },
        1000
    );
}



// ============================================================
// ANALYZER TABS (Email / Message  |  URL)
// Shows one analyzer at a time inside the "Live Analyzers" card
// and removes the old dark-theme styles that clashed with the page.
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    const oldStyle = document.getElementById("liveURLAnalyzerStyles");

    if (oldStyle) {
        oldStyle.remove();
    }

    const cards = {
        email: document.getElementById("liveMessageAnalyzer"),
        url: document.getElementById("liveURLAnalyzer")
    };

    Object.keys(cards).forEach(function (key) {
        if (cards[key]) {
            cards[key].classList.add("analyzer-card");
        }
    });

    function showAnalyzer(key) {

        Object.keys(cards).forEach(function (name) {
            if (cards[name]) {
                cards[name].classList.toggle("active", name === key);
            }
        });

        document.querySelectorAll(".analyzer-tab").forEach(function (tab) {
            tab.classList.toggle("active", tab.dataset.target === key);
        });
    }

    document.querySelectorAll(".analyzer-tab").forEach(function (tab) {
        tab.addEventListener("click", function () {
            showAnalyzer(tab.dataset.target);
        });
    });

    showAnalyzer("email");

    // Sidebar links: scroll to the matching section
    const targets = {
        "Dashboard": ".topbar",
        "New Case": "#newCaseButton",
        "Evidence": ".dashboard-grid",
        "Analysis": "#analysis",
        "Reports": ".recent-panel"
    };

    document.querySelectorAll(".sidebar .nav-item").forEach(function (link) {

        link.addEventListener("click", function (event) {

            event.preventDefault();

            const label = link.textContent.trim().replace(/^\S+\s+/, "");

            if (label === "New Case") {
                const button = document.getElementById("newCaseButton");
                if (button) { button.click(); }
                return;
            }

            const target = document.querySelector(targets[label] || "");

            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }

            document.querySelectorAll(".sidebar .nav-item").forEach(function (item) {
                item.classList.remove("active");
            });

            link.classList.add("active");
        });
    });
});