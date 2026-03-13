// script.js — Smart Evidence Writer: Frontend Logic
// Handles upload, analysis polling, report rendering, PDF download, lightbox

(function () {
    'use strict';

    // ═══════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════
    let selectedFile = null;
    let currentSessionId = null;
    let pollTimer = null;

    // ═══════════════════════════════════════════════════
    // DOM REFS
    // ═══════════════════════════════════════════════════
    const $ = (sel) => document.querySelector(sel);
    const dropZone = $('#drop-zone');
    const fileInput = $('#evidenceFile');
    const selectFileBtn = $('#selectFileBtn');
    const fileInfo = $('#file-info');
    const fileTypeIcon = $('#file-type-icon');
    const fileName = $('#file-name');
    const fileMeta = $('#file-meta');
    const removeFileBtn = $('#removeFileBtn');
    const analyzeBtn = $('#analyzeBtn');
    const uploadSection = $('#upload-section');
    const progressSection = $('#progress-section');
    const progressFill = $('#progress-fill');
    const progressPercent = $('#progress-percent');
    const progressMessage = $('#progress-message');
    const progressSteps = $('#progress-steps');
    const errorSection = $('#error-section');
    const errorMessage = $('#error-message');
    const retryBtn = $('#retryBtn');
    const reportSection = $('#report-section');
    const reportContent = $('#report-content');
    const downloadPdfBtn = $('#downloadPdfBtn');
    const newAnalysisBtn = $('#newAnalysisBtn');
    const framesGallery = $('#frames-gallery');
    const framesGrid = $('#frames-grid');
    const lightbox = $('#lightbox');
    const lightboxImg = $('#lightbox-img');
    const lightboxCaption = $('#lightbox-caption');

    // ═══════════════════════════════════════════════════
    // FILE HANDLING
    // ═══════════════════════════════════════════════════

    selectFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetFileSelection();
    });

    function handleFileSelect(file) {
        // Validate file size (100 MB)
        if (file.size > 100 * 1024 * 1024) {
            alert('File too large. Maximum size is 100 MB.');
            return;
        }

        selectedFile = file;

        // Update UI
        const mediaType = file.type.split('/')[0];
        const icons = { image: '🖼️', video: '🎬', audio: '🎵' };
        fileTypeIcon.textContent = icons[mediaType] || '📄';
        fileName.textContent = file.name;
        fileMeta.textContent = `${mediaType.toUpperCase()} • ${formatFileSize(file.size)}`;

        fileInfo.style.display = 'flex';
        dropZone.style.display = 'none';
        analyzeBtn.disabled = false;
    }

    function resetFileSelection() {
        selectedFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        dropZone.style.display = 'block';
        analyzeBtn.disabled = true;
    }

    // ═══════════════════════════════════════════════════
    // UPLOAD & ANALYZE
    // ═══════════════════════════════════════════════════

    analyzeBtn.addEventListener('click', startAnalysis);

    async function startAnalysis() {
        if (!selectedFile) return;

        // Show progress
        showSection('progress');
        updateProgress(2, 'Uploading evidence file...');
        updateStepState('upload', 'active');

        try {
            // Step 1: Upload
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('case_number', $('#caseNumber').value || '');
            formData.append('officer_id', $('#officerId').value || '');
            formData.append('case_description', $('#caseDescription').value || '');

            const uploadRes = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (!uploadRes.ok) {
                const err = await uploadRes.json();
                throw new Error(err.error || 'Upload failed');
            }

            const uploadData = await uploadRes.json();
            currentSessionId = uploadData.session_id;

            updateStepState('upload', 'done');
            updateProgress(8, 'File uploaded. Starting analysis...');

            // Step 2: Start analysis
            const analyzeRes = await fetch(`/api/analyze/${currentSessionId}`, {
                method: 'POST',
            });

            if (!analyzeRes.ok) {
                const err = await analyzeRes.json();
                throw new Error(err.error || 'Analysis start failed');
            }

            // Step 3: Poll for progress
            startPolling();

        } catch (err) {
            showError(err.message);
        }
    }

    // ═══════════════════════════════════════════════════
    // POLLING
    // ═══════════════════════════════════════════════════

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(pollStatus, 1500);
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    async function pollStatus() {
        if (!currentSessionId) return;

        try {
            const res = await fetch(`/api/status/${currentSessionId}`);
            if (!res.ok) throw new Error('Status check failed');

            const data = await res.json();
            const { status, progress, progress_message } = data;

            updateProgress(progress, progress_message);

            // Update step indicators
            if (progress >= 5) updateStepState('upload', 'done');
            if (progress >= 15) updateStepState('process', progress < 35 ? 'active' : 'done');
            if (progress >= 35) updateStepState('analyze', progress < 75 ? 'active' : 'done');
            if (progress >= 75) updateStepState('report', progress < 85 ? 'active' : 'done');
            if (progress >= 85) updateStepState('pdf', progress < 100 ? 'active' : 'done');

            if (status === 'complete') {
                stopPolling();
                renderReport(data.report);
                showSection('report');
            } else if (status === 'error') {
                stopPolling();
                showError(data.error || 'Analysis failed');
            }

        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    // ═══════════════════════════════════════════════════
    // PROGRESS UI
    // ═══════════════════════════════════════════════════

    function updateProgress(percent, message) {
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        progressMessage.textContent = message;
    }

    function updateStepState(step, state) {
        const el = progressSteps.querySelector(`[data-step="${step}"]`);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (state) el.classList.add(state);
    }

    // ═══════════════════════════════════════════════════
    // SECTION VISIBILITY
    // ═══════════════════════════════════════════════════

    function showSection(name) {
        uploadSection.style.display = name === 'upload' ? 'block' : 'none';
        progressSection.style.display = name === 'progress' ? 'block' : 'none';
        errorSection.style.display = name === 'error' ? 'block' : 'none';
        reportSection.style.display = name === 'report' ? 'block' : 'none';
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        showSection('error');
    }

    // ═══════════════════════════════════════════════════
    // REPORT RENDERING
    // ═══════════════════════════════════════════════════

    function renderReport(report) {
        if (!report) {
            reportContent.innerHTML = '<p class="report-body-text">No report data available.</p>';
            return;
        }

        let html = '';

        // Header
        const hdr = report.header || {};
        html += `
            <div class="report-header">
                <div class="classification">${esc(hdr.classification || 'RESTRICTED')}</div>
                <h2>${esc(hdr.report_title || 'EVIDENCE ANALYSIS REPORT')}</h2>
                <div class="system-name">${esc(hdr.system_name || '')}</div>
            </div>
        `;

        // Case Info
        html += `
            <div class="report-case-info">
                <div class="case-field"><span class="case-field-label">Case No:</span><span class="case-field-value">${esc(hdr.case_number || 'N/A')}</span></div>
                <div class="case-field"><span class="case-field-label">Report ID:</span><span class="case-field-value">${esc(hdr.report_id || 'N/A')}</span></div>
                <div class="case-field"><span class="case-field-label">Date:</span><span class="case-field-value">${esc(hdr.date || 'N/A')}</span></div>
                <div class="case-field"><span class="case-field-label">Time:</span><span class="case-field-value">${esc(hdr.time || 'N/A')}</span></div>
                <div class="case-field"><span class="case-field-label">Officer:</span><span class="case-field-value">${esc(hdr.officer_id || 'N/A')}</span></div>
                <div class="case-field"><span class="case-field-label">Description:</span><span class="case-field-value">${esc(hdr.case_description || 'N/A')}</span></div>
            </div>
        `;

        // Evidence Description
        const ev = report.evidence_description || {};
        html += `<h3 class="report-section-title">Evidence File Details</h3>`;
        html += '<div class="report-case-info">';
        for (const [k, v] of Object.entries(ev)) {
            if (v) html += `<div class="case-field"><span class="case-field-label">${esc(formatKey(k))}:</span><span class="case-field-value">${esc(String(v))}</span></div>`;
        }
        html += '</div>';

        // Executive Summary
        html += `<h3 class="report-section-title">1. Executive Summary</h3>`;
        html += `<p class="report-body-text">${esc(report.executive_summary || 'No summary available.')}</p>`;

        // Scene Description
        if (report.scene_description) {
            html += `<h3 class="report-section-title">2. Scene Description</h3>`;
            html += `<p class="report-body-text">${esc(report.scene_description)}</p>`;
        }

        // Detailed Analysis
        const details = report.detailed_analysis || [];
        if (details.length > 0) {
            html += `<h3 class="report-section-title">3. Detailed Analysis</h3>`;
            for (const sec of details) {
                html += `<p class="report-body-text"><strong>${esc(sec.title || '')}:</strong> ${esc(sec.content || '')}</p>`;
            }
        }

        // Violations
        const violations = report.violations || [];
        if (violations.length > 0) {
            html += `<h3 class="report-section-title">4. Violations Detected (${violations.length})</h3>`;
            html += renderFindings(violations, 'Violation');
        }

        // Accidents
        const accidents = report.accidents || [];
        if (accidents.length > 0) {
            html += `<h3 class="report-section-title">5. Accident Analysis (${accidents.length})</h3>`;
            html += renderFindings(accidents, 'Accident');
        }

        // Persons Identified
        const persons = report.persons_identified || [];
        if (persons.length > 0) {
            html += `<h3 class="report-section-title">6. Persons Identified (${persons.length})</h3>`;
            html += renderPersonsTable(persons);
        }

        // Vehicle Registry
        const vehicles = report.vehicle_registry || [];
        if (vehicles.length > 0) {
            html += `<h3 class="report-section-title">7. Vehicle / Number Plate Registry (${vehicles.length})</h3>`;
            html += renderVehiclesTable(vehicles);
        }

        // Landmarks
        const landmarks = report.landmarks_locations || [];
        if (landmarks.length > 0) {
            html += `<h3 class="report-section-title">8. Landmarks & Locations (${landmarks.length})</h3>`;
            html += renderLandmarksTable(landmarks);
        }

        // Timeline
        const timeline = report.timeline || [];
        if (timeline.length > 0) {
            html += `<h3 class="report-section-title">9. Chronological Timeline</h3>`;
            html += renderTimeline(timeline);
        }

        // Environmental Conditions
        const env = report.environmental_conditions || {};
        if (Object.keys(env).length > 0) {
            html += `<h3 class="report-section-title">Environmental Conditions</h3>`;
            html += '<div class="report-case-info">';
            for (const [k, v] of Object.entries(env)) {
                if (v) html += `<div class="case-field"><span class="case-field-label">${esc(formatKey(k))}:</span><span class="case-field-value">${esc(String(v))}</span></div>`;
            }
            html += '</div>';
        }

        // Risk Assessment
        const risk = report.risk_assessment || {};
        if (risk.threat_level) {
            html += `<h3 class="report-section-title">10. Risk Assessment</h3>`;
            html += renderRisk(risk);
        }

        // Recommendations
        const recs = report.investigative_recommendations || [];
        if (recs.length > 0) {
            html += `<h3 class="report-section-title">11. Investigative Recommendations</h3>`;
            html += '<ol class="recommendations-list">';
            for (const rec of recs) {
                html += `<li>${esc(rec)}</li>`;
            }
            html += '</ol>';
        }

        // Certification
        const cert = report.certification || {};
        html += `<h3 class="report-section-title">Report Certification</h3>`;
        html += `<p class="report-body-text" style="font-style: italic; font-size: 0.8rem;">${esc(cert.disclaimer || '')}</p>`;
        html += `<p class="report-body-text" style="font-size: 0.78rem; color: var(--text-muted);">Generated by: ${esc(cert.system || '')} at ${esc(cert.generated_at || '')}</p>`;
        if (report.confidence_score !== undefined) {
            html += `<p class="report-body-text"><strong>Analysis Confidence:</strong> ${(report.confidence_score * 100).toFixed(0)}%</p>`;
        }

        // Signature blocks
        const sigs = cert.signature_blocks || [];
        if (sigs.length > 0) {
            html += '<div class="signature-blocks">';
            for (const sig of sigs) {
                html += `
                    <div class="signature-block">
                        <h4>${esc(sig.title || '')}</h4>
                        <div class="signature-line">Name / Rank / Badge / Date</div>
                    </div>
                `;
            }
            html += '</div>';
        }

        reportContent.innerHTML = html;

        // Render frames gallery
        renderFramesGallery(report.evidence_exhibits || []);
    }

    function renderFindings(items, type) {
        let html = '';
        for (const item of items) {
            const severity = (item.severity || 'unknown').toLowerCase();
            html += `
                <div class="finding-card severity-${severity}">
                    <div class="finding-header">
                        <span class="finding-title">${type} #${item.index}: ${esc(item.type || '')}</span>
                        <span class="severity-badge ${severity}">${severity}</span>
                    </div>
                    <div class="finding-desc">${esc(item.description || '')}</div>
                    ${item.evidence_details ? `<div class="finding-desc" style="margin-top:0.3rem;"><em>${esc(item.evidence_details)}</em></div>` : ''}
                    ${item.vehicles_involved ? `<div class="finding-meta">Vehicles: ${esc(item.vehicles_involved)}</div>` : ''}
                    ${item.damage_assessment ? `<div class="finding-meta">Damage: ${esc(item.damage_assessment)}</div>` : ''}
                    ${item.detected_at ? `<div class="finding-meta">Detected at: ${esc(item.detected_at)}</div>` : ''}
                    ${item.evidence_frame_base64 ? `
                        <div class="finding-frame">
                            <img src="data:image/jpeg;base64,${item.evidence_frame_base64}" 
                                 alt="${type} evidence" 
                                 onclick="window.__openLightbox(this.src, '${esc(type)} #${item.index} evidence frame')">
                        </div>
                    ` : ''}
                </div>
            `;
        }
        return html;
    }

    function renderPersonsTable(persons) {
        let html = `
            <table class="report-table">
                <thead><tr><th>#</th><th>ID</th><th>Description</th><th>Activity</th><th>Relevance</th></tr></thead>
                <tbody>
        `;
        for (const p of persons) {
            html += `<tr>
                <td>${p.index}</td>
                <td>${esc(p.person_id || '')}</td>
                <td>${esc(p.description || '')}</td>
                <td>${esc(p.activity || '')}</td>
                <td>${esc(p.relevance || '')}</td>
            </tr>`;
        }
        html += '</tbody></table>';

        // Add evidence frames for persons
        for (const p of persons) {
            if (p.evidence_frame_base64) {
                html += `
                    <div class="finding-frame" style="max-width: 400px; margin: 0.5rem 0;">
                        <img src="data:image/jpeg;base64,${p.evidence_frame_base64}" 
                             alt="Person evidence" 
                             onclick="window.__openLightbox(this.src, '${esc(p.person_id || 'Person')} evidence')">
                    </div>
                `;
            }
        }
        return html;
    }

    function renderVehiclesTable(vehicles) {
        let html = `
            <table class="report-table">
                <thead><tr><th>#</th><th>Plate Number</th><th>Vehicle</th><th>Color</th><th>Region</th><th>Confidence</th></tr></thead>
                <tbody>
        `;
        for (const v of vehicles) {
            html += `<tr>
                <td>${v.index}</td>
                <td class="plate-text">${esc(v.plate_text || 'N/A')}</td>
                <td>${esc(v.vehicle_type || '')}</td>
                <td>${esc(v.vehicle_color || '')}</td>
                <td>${esc(v.plate_region || '')}</td>
                <td>${esc(v.confidence || '')}</td>
            </tr>`;
        }
        html += '</tbody></table>';

        for (const v of vehicles) {
            if (v.evidence_frame_base64) {
                html += `
                    <div class="finding-frame" style="max-width: 400px; margin: 0.5rem 0;">
                        <img src="data:image/jpeg;base64,${v.evidence_frame_base64}" 
                             alt="Vehicle evidence" 
                             onclick="window.__openLightbox(this.src, 'Plate: ${esc(v.plate_text || 'N/A')}')">
                    </div>
                `;
            }
        }
        return html;
    }

    function renderLandmarksTable(landmarks) {
        let html = `
            <table class="report-table">
                <thead><tr><th>#</th><th>Name</th><th>Type</th><th>Details</th><th>Location</th></tr></thead>
                <tbody>
        `;
        for (const l of landmarks) {
            html += `<tr>
                <td>${l.index}</td>
                <td>${esc(l.name || '')}</td>
                <td>${esc(l.type || '')}</td>
                <td>${esc(l.details || '')}</td>
                <td>${esc(l.location_hint || '')}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        return html;
    }

    function renderTimeline(timeline) {
        let html = `
            <table class="report-table">
                <thead><tr><th>Seq</th><th>Time</th><th>Event</th></tr></thead>
                <tbody>
        `;
        for (const t of timeline) {
            html += `<tr>
                <td>${t.sequence || ''}</td>
                <td style="font-family: var(--font-mono); white-space: nowrap;">${esc(String(t.time || ''))}</td>
                <td>${esc(String(t.event || ''))}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        return html;
    }

    function renderRisk(risk) {
        const level = (risk.threat_level || 'unknown').toLowerCase();
        return `
            <div class="risk-card threat-${level}">
                <div class="risk-level ${level}">⚠ Threat Level: ${level.toUpperCase()}</div>
                ${risk.risk_factors ? `<p class="report-body-text"><strong>Risk Factors:</strong> ${esc(risk.risk_factors)}</p>` : ''}
                ${risk.recommended_response ? `<p class="report-body-text"><strong>Recommended Response:</strong> ${esc(risk.recommended_response)}</p>` : ''}
            </div>
        `;
    }

    // ═══════════════════════════════════════════════════
    // FRAMES GALLERY
    // ═══════════════════════════════════════════════════

    function renderFramesGallery(exhibits) {
        if (!exhibits || exhibits.length === 0) {
            framesGallery.style.display = 'none';
            return;
        }

        framesGallery.style.display = 'block';
        framesGrid.innerHTML = '';

        for (const exhibit of exhibits) {
            if (!exhibit.base64) continue;

            const card = document.createElement('div');
            card.className = `frame-card${exhibit.is_key_finding ? ' key-finding' : ''}`;
            card.innerHTML = `
                <img src="data:image/jpeg;base64,${exhibit.base64}" alt="Evidence frame" loading="lazy">
                <div class="frame-card-info">
                    <span class="frame-card-time">${esc(exhibit.timestamp || '')}</span>
                    <span class="frame-card-desc">${esc(exhibit.description || '')}</span>
                </div>
            `;

            card.addEventListener('click', () => {
                openLightbox(`data:image/jpeg;base64,${exhibit.base64}`, exhibit.description || '');
            });

            framesGrid.appendChild(card);
        }
    }

    // ═══════════════════════════════════════════════════
    // LIGHTBOX
    // ═══════════════════════════════════════════════════

    function openLightbox(src, caption) {
        lightboxImg.src = src;
        lightboxCaption.textContent = caption;
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = '';
    }

    // Global access for inline onclick
    window.__openLightbox = openLightbox;

    lightbox.querySelector('.lightbox-overlay').addEventListener('click', closeLightbox);
    lightbox.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
    });

    // ═══════════════════════════════════════════════════
    // ACTIONS
    // ═══════════════════════════════════════════════════

    downloadPdfBtn.addEventListener('click', () => {
        if (!currentSessionId) return;
        window.open(`/api/pdf/${currentSessionId}`, '_blank');
    });

    newAnalysisBtn.addEventListener('click', resetAll);
    retryBtn.addEventListener('click', resetAll);

    function resetAll() {
        stopPolling();
        currentSessionId = null;
        selectedFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        dropZone.style.display = 'block';
        analyzeBtn.disabled = true;
        reportContent.innerHTML = '';
        framesGrid.innerHTML = '';
        framesGallery.style.display = 'none';
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressMessage.textContent = 'Initializing...';

        // Reset step indicators
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'done'));

        showSection('upload');
    }

    // ═══════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════

    function esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

})();