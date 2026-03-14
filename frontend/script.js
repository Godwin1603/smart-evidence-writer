/**
 * ALFA HAWK - PROFESSIONAL FORENSIC WORKSTATION LOGIC
 * V3.0 "Investigation Dashboard" Edition
 */

(function () {
    'use strict';

    // ═══════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════
    let selectedFile = null;
    let currentSessionId = null;
    let currentReport = null;
    let pollTimer = null;
    let clientId = null;
    let activeTab = 'overview';
    let currentFrameContext = null;
    const apiBaseMeta = document.querySelector('meta[name="alfa-hawk-api-base"]');
    const defaultApiBase = isLocalHost() ? '' : 'https://api.alfagroups.tech';
    const apiBase = normalizeApiBase(window.ALFA_HAWK_API_BASE || apiBaseMeta?.content || defaultApiBase);
    const allowedExtensions = new Set(['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.wav']);

    function normalizeApiBase(value) {
        return value ? value.replace(/\/+$/, '') : '';
    }

    function isLocalHost() {
        return ['localhost', '127.0.0.1'].includes(window.location.hostname);
    }

    function apiUrl(path) {
        if (!path) return apiBase;
        if (/^https?:\/\//i.test(path)) return path;
        return `${apiBase}${path}`;
    }

    // ═══════════════════════════════════════════════════
    // INITIALIZATION — CLIENT ID & PERSISTENCE
    // ═══════════════════════════════════════════════════
    function init() {
        initClientId();
        setupEventListeners();
        fetchUsageStats(); // Try to get usage stats
    }

    function initClientId() {
        clientId = localStorage.getItem('alfa_hawk_client_id');
        if (!clientId) {
            clientId = 'AH-' + Math.random().toString(36).substr(2, 9).toUpperCase() + '-' + Date.now();
            localStorage.setItem('alfa_hawk_client_id', clientId);
        }
        console.info('Alfa Hawk Investigation ID:', clientId);
    }

    // ═══════════════════════════════════════════════════
    // DOM REFS
    // ═══════════════════════════════════════════════════
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dropZone = $('#drop-zone');
    const fileInput = $('#evidenceFile');
    const selectFileBtn = $('#selectFileBtn');
    const fileInfo = $('#file-info');
    const analyzeBtn = $('#analyzeBtn');
    const workspace = $('#workspace');
    
    // Views
    const viewInitial = $('#view-initial');
    const viewProgress = $('#view-progress');
    const viewResults = $('#view-results');
    const viewError = $('#view-error');

    // Tab buttons
    const tabBtns = $$('.tab-btn');
    const tabContents = $$('.tab-content');

    // ═══════════════════════════════════════════════════
    // EVENT LISTENERS
    // ═══════════════════════════════════════════════════
    function setupEventListeners() {
        // ... previous listeners ...
        selectFileBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => { if (fileInput.files.length > 0) handleFileSelect(fileInput.files[0]); });
        $('#removeFileBtn').addEventListener('click', resetFileSelection);

        $$('input[name="analysisMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const isByo = e.target.value === 'byo';
                $('#byo-key-group').style.display = isByo ? 'flex' : 'none';
            });
        });

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-tab');
                switchTab(tabId);
            });
        });

        analyzeBtn.addEventListener('click', startAnalysis);
        $('#retryBtn').addEventListener('click', resetAll);
        $('#downloadPdfBtn').addEventListener('click', downloadPdf);
        $('#downloadJsonBtn').addEventListener('click', downloadJson);
        
        $('.lightbox-close').addEventListener('click', closeLightbox);
        $('.lightbox-overlay').addEventListener('click', closeLightbox);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLightbox(); });

        // Connectivity Monitor
        window.addEventListener('online', () => updateConnectionStatus('online'));
        window.addEventListener('offline', () => updateConnectionStatus('offline'));

        // Sidebar Resizer Logic
        const resizer = $('#sidebar-resizer');
        const sidebar = $('#sidebar');
        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            resizer.classList.add('dragging');
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const offsetLeft = e.clientX;
            // Limit sidebar width between 200px and 600px
            if (offsetLeft > 200 && offsetLeft < 600) {
                sidebar.style.width = `${offsetLeft}px`;
            }
        });

        document.addEventListener('mouseup', () => {
            isResizing = false;
            document.body.style.cursor = 'default';
            resizer.classList.remove('dragging');
        });
    }

    function updateConnectionStatus(state) {
        const dot = $('.status-dot');
        const text = $('.status-text');
        if (!dot || !text) return;

        dot.className = 'status-dot ' + (state === 'online' ? 'online' : state === 'waiting' ? 'waiting' : 'offline');
        text.textContent = state === 'online' ? 'Station: Connected' : state === 'waiting' ? 'Station: Retrying...' : 'Station: Offline';
    }
    // ═══════════════════════════════════════════════════
    // FILE HANDLING & PREVIEW
    // ═══════════════════════════════════════════════════
    function handleFileSelect(file) {
        const ext = `.${(file.name.split('.').pop() || '').toLowerCase()}`;
        if (!allowedExtensions.has(ext)) {
            showTopLevelError('Unsupported evidence type. Use JPG, PNG, MP4, MOV, AVI, or WAV files.');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            showTopLevelError('File size exceeds 50MB limit.');
            return;
        }
        
        selectedFile = file;
        $('#file-name').textContent = file.name;
        $('#file-size').textContent = formatFileSize(file.size);
        
        const previewContainer = $('#preview-container');
        previewContainer.innerHTML = '';
        $('#media-meta').style.display = 'none';

        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            previewContainer.appendChild(img);
            img.onload = () => {
                $('#file-res').textContent = `${img.naturalWidth}x${img.naturalHeight}`;
                $('#file-duration').textContent = 'N/A';
                $('#media-meta').style.display = 'block';
            };
        } else if (file.type.startsWith('video/')) {
            const video = document.createElement('video');
            video.src = URL.createObjectURL(file);
            video.muted = true;
            video.controls = false;
            previewContainer.appendChild(video);
            video.onloadedmetadata = () => {
                $('#file-res').textContent = `${video.videoWidth}x${video.videoHeight}`;
                const duration = Math.round(video.duration);
                $('#file-duration').textContent = `${duration}s`;
                $('#media-meta').style.display = 'block';
                
                if (duration > 60) {
                    showTopLevelError('Video duration exceeds 60s limit.');
                    resetFileSelection();
                }
            };
        } else {
             previewContainer.innerHTML = '<div style="font-size:3rem">📄</div>';
        }

        fileInfo.style.display = 'block';
        dropZone.style.display = 'none';
        analyzeBtn.disabled = false;
        showSection('initial');
    }

    function resetFileSelection() {
        selectedFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        dropZone.style.display = 'block';
        analyzeBtn.disabled = true;
    }

    // ═══════════════════════════════════════════════════
    // ANALYSIS PIPELINE
    // ═══════════════════════════════════════════════════
    let pollInterval = 2000;
    let failedPolls = 0;

    async function startAnalysis() {
        if (!selectedFile) return;
        
        resetProgressSteps();
        showSection('progress');
        updateProgress(5, 'Validating evidence file...', 'validate');

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('case_number', $('#caseNumber').value || '');
            formData.append('officer_id', $('#officerId').value || '');
            formData.append('case_description', $('#caseDescription').value || '');
            
            const isByo = $('input[name="analysisMode"]:checked').value === 'byo';
            if (isByo) {
                const key = $('#ai-api-key').value.trim();
                formData.append('ai_api_key', key);
            }

            const uploadRes = await fetch(apiUrl('/api/upload'), { 
                method: 'POST', 
                body: formData,
                headers: { 'X-Client-ID': clientId }
            });

            if (!uploadRes.ok) {
                const err = await uploadRes.json();
                throw new Error(err.error || 'Upload failed');
            }

            const uploadData = await uploadRes.json();
            currentSessionId = uploadData.session_id;

            markStepDone('validate');
            updateProgress(15, 'Extracting forensics frames...', 'extract');

            await fetch(apiUrl(`/api/analyze/${currentSessionId}`), { 
                method: 'POST',
                headers: { 'X-Client-ID': clientId }
            });

            startPolling();
        } catch (err) {
            showSection('error');
            $('#error-message').textContent = err.message;
        }
    }

    function startPolling() {
        if (pollTimer) clearTimeout(pollTimer);
        pollInterval = 2000;
        failedPolls = 0;
        pollTimer = setTimeout(pollStatus, pollInterval);
    }

    async function pollStatus() {
        if (!currentSessionId) return;
        try {
            const res = await fetch(apiUrl(`/api/status/${currentSessionId}`), {
                headers: { 'X-Client-ID': clientId }
            });
            
            if (!res.ok) throw new Error('Network response not ok');
            
            const data = await res.json();
            failedPolls = 0;
            pollInterval = 2000;
            updateConnectionStatus('online');

            const { status, progress, progress_message } = data;
            
            let activeStep = 'validate';
            if (progress >= 15) { markStepDone('validate'); activeStep = 'extract'; }
            if (progress >= 30) { markStepDone('extract'); activeStep = 'upload'; }
            if (progress >= 50) { markStepDone('upload'); activeStep = 'analyze'; }
            if (progress >= 75) { markStepDone('analyze'); activeStep = 'reconstruct'; }
            if (progress >= 90) { markStepDone('reconstruct'); activeStep = 'report'; }
            
            updateProgress(progress, progress_message, activeStep);

            if (status === 'complete') {
                markStepDone('report');
                currentReport = data.report;
                renderDashboard(data.report);
                showSection('results');
                fetchUsageStats();
            } else if (status === 'error') {
                showSection('error');
                $('#error-message').textContent = data.error || 'AI analysis failed';
            } else {
                pollTimer = setTimeout(pollStatus, pollInterval);
            }
        } catch (err) {
            failedPolls++;
            updateConnectionStatus('waiting');
            pollInterval = Math.min(10000, pollInterval * 1.5);
            console.warn(`Polling failed (${failedPolls}). Retrying in ${pollInterval}ms...`);
            pollTimer = setTimeout(pollStatus, pollInterval);
        }
    }

    // ═══════════════════════════════════════════════════
    // DASHBOARD RENDERING
    // ═══════════════════════════════════════════════════
    function renderDashboard(report) {
        if (!report) return;
        currentReport = report;

        // ═══════════════════════════════════════════════════
        // HEADER & EXPORT SYNC
        // ═══════════════════════════════════════════════════
        const hdr = report.header || {};
        $('#report-header-preview').innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1px solid var(--border-color); padding-bottom:1rem; margin-bottom:1.5rem;">
                <div>
                    <h2 style="font-size:1.5rem; margin-bottom:0.25rem;">${esc(hdr.report_title || 'FORENSIC REPORT')}</h2>
                    <span class="mono-tech" style="color:var(--text-muted);">ID: ${esc(hdr.report_id || 'UNKNOWN')}</span>
                </div>
                <div style="text-align:right">
                    <div style="font-size:0.8rem; font-weight:700; color:var(--accent-crimson);">${esc(hdr.classification || 'RESTRICTED')}</div>
                    <div class="mono-tech" style="color:var(--text-secondary);">${esc(hdr.date || '')} ${esc(hdr.time || '')}</div>
                </div>
            </div>
        `;

        $('#export-confidence').textContent = `${report.confidence_score || 0}%`;
        $('#export-frames').textContent = (report.evidence_exhibits || []).length;
        $('#export-status').textContent = 'READY';

        // ═══════════════════════════════════════════════════
        // 1. OVERVIEW — INTEGRITY LEDGER & PHASES
        // ═══════════════════════════════════════════════════
        const aiMeta = report.ai_metadata || {};
        const integrity = report.evidence_integrity || {};
        
        const phaseCardsHtml = buildPhaseCards(report);
        let overviewHtml = `
            <div class="overview-shell">
                <div class="overview-main-column">
                    <div class="grid-card phases-card">
                        <div class="section-header">
                            <div>
                                <span class="section-kicker">Overview</span>
                                <h3>Incident Phase Reconstruction</h3>
                            </div>
                            <span class="section-meta mono-tech">${(report.incident_phases || []).length} phases</span>
                        </div>
                        <div class="phase-cards-track">
                            ${phaseCardsHtml}
                        </div>
                    </div>
                </div>
                <div class="overview-side-column">
                    <div class="grid-card integrity-card">
                        <h3>Forensic Integrity Ledger</h3>
                        <div class="integrity-ledger">
                            <div class="detail-row"><span class="detail-label">Evidence Hash:</span><span class="detail-value mono-tech truncate">${integrity.sha256 || '--'}</span></div>
                            <div class="detail-row"><span class="detail-label">Report ID:</span><span class="detail-value mono-tech">${hdr.report_id || '--'}</span></div>
                            <div class="detail-row"><span class="detail-label">AI Model:</span><span class="detail-value mono-tech">${aiMeta.model || 'Gemini 2.5 Flash'}</span></div>
                            <div class="detail-row"><span class="detail-label">Signature:</span><span class="detail-value mono-tech truncate">${report.report_integrity_hash || '--'}</span></div>
                        </div>
                        <div class="threat-level-section" style="margin-top:1.5rem">
                             <span class="detail-label">INDICATIVE THREAT LEVEL:</span>
                             <div id="threat-indicator" class="threat-box threat-${(report.risk_assessment?.threat_level || 'LOW').toLowerCase()}">${(report.risk_assessment?.threat_level || 'LOW')}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        $('#tab-overview').innerHTML = overviewHtml;

        // ═══════════════════════════════════════════════════
        // 2. TIMELINE — SCRUBBER & LIST
        // ═══════════════════════════════════════════════════
        const timeline = report.timeline || [];
        const duration = report.evidence_integrity?.duration_seconds || 10;
        $('#scrubber-end').textContent = report.evidence_integrity?.duration || '00:10';
        
        let timeHtml = '';
        let markersHtml = '';
        let firstMarkerPercent = 0;
        
        timeline.forEach((t, idx) => {
            const timeStr = t.time || '00:00';
            const totalSecs = timeToSeconds(timeStr);
            const percent = Math.min(100, (totalSecs / duration) * 100);
            const frame = findFrameById(t.evidence_frame);
            const subjects = inferSubjectsFromEntry(t, report);
            const observation = frame?.description || t.event || 'No frame observation available.';

            if (idx === 0) firstMarkerPercent = percent;
            
            markersHtml += `<button class="marker marker-button" type="button" style="left: ${percent}%" title="${esc(t.event || '')}" onclick="window.__openTimelineEvent(${idx})"></button>`;
            
            timeHtml += `
            <article id="timeline-event-${idx}" class="timeline-item interactive-node" onclick="window.__openTimelineEvent(${idx})">
                <div class="timeline-node-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-head">
                        <span class="timeline-time mono-tech">${esc(timeStr)}</span>
                        <span class="timeline-sequence mono-tech">Event ${(t.sequence || idx + 1)}</span>
                    </div>
                    <p class="timeline-event">${esc(t.event || '')}</p>
                    <div class="timeline-subjects">
                        ${subjects.length ? subjects.map(subject => `<span class="subject-chip">${esc(subject)}</span>`).join('') : '<span class="subject-chip subject-chip-muted">Unassigned subjects</span>'}
                    </div>
                    <div class="timeline-evidence-row">
                        <button class="frame-preview-button" type="button" onclick="event.stopPropagation(); window.__openTimelineEvent(${idx});">
                            ${frame?.base64 ? `<img src="data:image/jpeg;base64,${frame.base64}" alt="Frame ${esc(t.evidence_frame || '')}" loading="lazy">` : '<div class="frame-preview-placeholder">NO FRAME</div>'}
                            <div class="frame-preview-meta">
                                <span class="frame-preview-label">Frame</span>
                                <span class="frame-preview-id mono-tech">${esc(t.evidence_frame || 'N/A')}</span>
                            </div>
                        </button>
                        <div class="timeline-evidence-text">
                            <span class="evidence-link-label">Associated evidence frame</span>
                            <span class="timeline-observation">${esc(observation)}</span>
                        </div>
                    </div>
                </div>
            </article>`;
        });
        
        $('#timeline-markers').innerHTML = markersHtml;
        $('#timeline-list').innerHTML = timeHtml || '<p class="text-muted">No timeline data.</p>';
        updateScrubberPosition(timeline.length ? firstMarkerPercent : 0);

        // ═══════════════════════════════════════════════════
        // 3. PERSONS — INVESTIGATION TABLE
        // ═══════════════════════════════════════════════════
        const persons = report.persons_identified || [];
        let pTableHtml = `
            <table class="investigation-table">
                <thead><tr><th>ID</th><th>Observed Role</th><th>First Seen</th><th>Visibility</th><th>Evidentiary Link</th></tr></thead>
                <tbody>
                    ${persons.map(p => `
                        <tr>
                            <td class="id-cell">${esc(p.person_id)}</td>
                            <td><span class="role-badge role-${(p.observed_role || 'unknown').toLowerCase().replace(' ', '-')}">${esc(p.observed_role)}</span></td>
                            <td class="mono-tech">${esc(p.first_seen)}</td>
                            <td>${esc(p.visibility_confidence)}</td>
                            <td class="mono-tech"><span class="frame-tag" onclick="window.__openEvidenceFrame('${p.evidence_frame}')">${esc(p.evidence_frame || 'N/A')}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        $('#persons-table-container').innerHTML = persons.length ? pTableHtml : '<p class="text-muted">No persons detected.</p>';

        // ═══════════════════════════════════════════════════
        // 4. OBJECTS CATEGORIZED
        // ═══════════════════════════════════════════════════
        const objects = report.weapons_objects || [];
        // Grouping logic
        const groups = { 'Vehicles': [], 'Weapons': [], 'Other Objects': [] };
        objects.forEach(o => {
            const cat = (o.object || '').toLowerCase().includes('car') || (o.object || '').toLowerCase().includes('motorcycle') || (o.object || '').toLowerCase().includes('suv') ? 'Vehicles' : 
                        (o.object || '').toLowerCase().includes('gun') || (o.object || '').toLowerCase().includes('knife') || (o.object || '').toLowerCase().includes('weapon') ? 'Weapons' : 'Other Objects';
            groups[cat].push(o);
        });

        let objRegistryHtml = '';
        for (const [catName, items] of Object.entries(groups)) {
            if (items.length === 0) continue;
            objRegistryHtml += `
                <div class="registry-group">
                    <h4 class="registry-group-title">${catName}</h4>
                    <table class="investigation-table">
                        <thead><tr><th>Object Type</th><th>Timestamp</th><th>Reliability</th><th>Description</th></tr></thead>
                        <tbody>
                            ${items.map(i => `
                                <tr>
                                    <td style="font-weight:700">${esc(i.object)}</td>
                                    <td class="mono-tech">${esc(i.timestamp)}</td>
                                    <td>${i.confidence_percent || 75}%</td>
                                    <td>${esc(i.description)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        $('#objects-registry-container').innerHTML = objRegistryHtml || '<p class="text-muted">No object inventory detected.</p>';

        // ═══════════════════════════════════════════════════
        // 5. FRAMES WITH LABELS
        // ═══════════════════════════════════════════════════
        const frames = report.evidence_exhibits || [];
        let framesHtml = '';
        frames.forEach(f => {
            if (!f.base64) return;
            framesHtml += `
            <div class="frame-card" onclick="window.__openEvidenceFrame('${f.frame_id || ''}')">
                <img src="data:image/jpeg;base64,${f.base64}" alt="Evidence" loading="lazy">
                <div class="frame-meta">
                    <span class="mono-tech">${esc(f.timestamp || '--')}</span>
                    <span class="id-tag">${esc(f.frame_id || '')}</span>
                </div>
                <div class="frame-observation-overlay">${esc(f.description || 'Observation')}</div>
            </div>`;
        });
        $('#frames-grid').innerHTML = framesHtml || '<p class="text-muted">No exhibits.</p>';

        switchTab('overview');
    }

    // ═══════════════════════════════════════════════════
    // UI UTILITIES
    // ═══════════════════════════════════════════════════
    function showSection(name) {
        viewInitial.style.display = 'none';
        viewProgress.style.display = 'none';
        viewResults.style.display = 'none';
        viewError.style.display = 'none';
        
        switch(name) {
            case 'initial': viewInitial.style.display = 'block'; break;
            case 'progress': viewProgress.style.display = 'block'; break;
            case 'results': viewResults.style.display = 'block'; break;
            case 'error': viewError.style.display = 'block'; break;
        }
    }

    function switchTab(tabId) {
        activeTab = tabId;
        tabBtns.forEach(btn => btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId));
        tabContents.forEach(content => content.classList.toggle('active', content.id === `tab-${tabId}`));
    }

    function updateProgress(percent, message, activeStepId) {
        $('#progress-fill').style.width = `${percent}%`;
        $('#progress-message').textContent = message;
        
        const steps = $$('.f-step');
        let foundActive = false;
        steps.forEach(s => {
            const id = s.getAttribute('data-step');
            if (id === activeStepId) {
                s.className = 'f-step active';
                foundActive = true;
            } else if (!foundActive) {
                s.className = 'f-step done';
            } else {
                s.className = 'f-step';
            }
        });
    }

    function markStepDone(stepId) {
        const step = $(`.f-step[data-step="${stepId}"]`);
        if (step) step.className = 'f-step done';
    }

    function resetProgressSteps() {
        $$('.f-step').forEach(s => s.className = 'f-step');
        $('#progress-fill').style.width = '0%';
    }

    function showTopLevelError(msg) {
        alert('FORENSIC ERROR: ' + msg);
    }

    function resetAll() {
        clearInterval(pollTimer);
        currentSessionId = null;
        currentReport = null;
        resetFileSelection();
        showSection('initial');
    }

    async function fetchUsageStats() {
        try {
            const res = await fetch(apiUrl('/api/usage'), {
                headers: { 'X-Client-ID': clientId }
            });
            if (res.ok) {
                const data = await res.json();
                const usageMonthly = $('#usage-monthly');
                if (usageMonthly) {
                    usageMonthly.textContent = `${data.client_daily_count} / ${data.client_daily_limit}`;
                }
                const usageDaily = $('#usage-daily');
                if (usageDaily) {
                    usageDaily.textContent = `${data.global_daily_count} / ${data.global_daily_limit}`;
                }
            }
        } catch (e) {
            console.warn('Could not fetch usage stats.');
        }
    }

    // ═══════════════════════════════════════════════════
    // EXPORT
    // ═══════════════════════════════════════════════════
    async function downloadPdf() {
        if (!currentSessionId) return;
        try {
            const res = await fetch(apiUrl(`/api/pdf/${currentSessionId}`), { headers: { 'X-Client-ID': clientId } });
            if (!res.ok) throw new Error('PDF generation failure');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `AlfaHawk_Forensic_Report_${currentSessionId.split('-')[0]}.pdf`;
            a.click();
        } catch (e) { alert('Error: ' + e.message); }
    }

    function downloadJson() {
        if (!currentReport) return;
        const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AlfaHawk_Investigation_Data_${Date.now()}.json`;
        a.click();
    }

    // ═══════════════════════════════════════════════════
    // LIGHTBOX & HELPERS
    // ═══════════════════════════════════════════════════
    function openLightbox(src, caption, timestamp, meta = {}) {
        $('#lightbox-img').src = src;
        $('#lightbox-caption').textContent = caption;
        $('#lightbox-timestamp').textContent = timestamp || '';
        $('#lightbox-frame-id').textContent = meta.frameId || 'FRAME --';
        $('#lightbox-linked-event').textContent = meta.linkedEvent || 'No linked event';

        const jumpButton = $('#lightbox-jump-link');
        currentFrameContext = meta;
        if (meta.timelineIndex !== undefined && meta.timelineIndex !== null) {
            jumpButton.style.display = 'inline-flex';
        } else {
            jumpButton.style.display = 'none';
        }
        $('#lightbox').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        $('#lightbox').style.display = 'none';
        document.body.style.overflow = '';
        currentFrameContext = null;
    }

    window.__openLightbox = openLightbox;
    
    window.__openEvidenceFrame = (frameId, options = {}) => {
        if (!currentReport || !frameId || frameId === 'N/A') return;
        const frame = findFrameById(frameId);
        if (frame && frame.base64) {
            openLightbox(
                `data:image/jpeg;base64,${frame.base64}`,
                frame.description || 'No AI observation available.',
                frame.timestamp,
                {
                    frameId: frame.frame_id || frameId,
                    linkedEvent: options.linkedEvent || 'Direct evidence access',
                    timelineIndex: options.timelineIndex ?? null,
                }
            );
        } else {
            console.warn('Frame not found in exhibits:', frameId);
        }
    };

    window.__openTimelineEvent = (index) => {
        if (!currentReport) return;
        const timeline = currentReport.timeline || [];
        const event = timeline[index];
        if (!event) return;

        const frame = findFrameById(event.evidence_frame);
        const observation = frame?.description || event.event || 'No AI observation available.';
        const timeStr = event.time || frame?.timestamp || '--';
        const totalSecs = timeToSeconds(timeStr);
        const duration = currentReport.evidence_integrity?.duration_seconds || 10;
        const percent = Math.min(100, duration ? (totalSecs / duration) * 100 : 0);

        updateScrubberPosition(percent);
        window.__openEvidenceFrame(event.evidence_frame, {
            timelineIndex: index,
            linkedEvent: `${timeStr} - ${event.event || 'Timeline event'}`,
        });
        const node = document.getElementById(`timeline-event-${index}`);
        if (node) {
            document.querySelectorAll('.timeline-item.active').forEach((item) => item.classList.remove('active'));
            node.classList.add('active');
        }
    };

    window.__openPersonDetails = (personId) => {
        const person = (currentReport?.persons_identified || []).find(p => p.person_id === personId);
        if (person) {
            // Persons tab doesn't have a detail panel, so we just open their primary evidence frame
            window.__openEvidenceFrame(person.evidence_frame);
        }
    };

    $('#lightbox-jump-link').addEventListener('click', () => {
        if (!currentFrameContext || currentFrameContext.timelineIndex === undefined || currentFrameContext.timelineIndex === null) return;
        const timelineIndex = currentFrameContext.timelineIndex;
        switchTab('timeline');
        closeLightbox();
        setTimeout(() => {
            const node = document.getElementById(`timeline-event-${timelineIndex}`);
            if (node) {
                node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                node.classList.add('pulse-focus');
                setTimeout(() => node.classList.remove('pulse-focus'), 1200);
            }
        }, 50);
    });

    function esc(str) {
        if (!str) return '';
        const d = document.createElement('div');
        d.textContent = String(str);
        return d.innerHTML;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    function findFrameById(frameId) {
        return (currentReport?.evidence_exhibits || []).find(f => f.frame_id === frameId);
    }

    function timeToSeconds(timeValue) {
        if (typeof timeValue === 'number') return timeValue;
        if (!timeValue || typeof timeValue !== 'string') return 0;
        const parts = timeValue.split(':').map(Number).filter(num => !Number.isNaN(num));
        if (parts.length === 2) return (parts[0] * 60) + parts[1];
        if (parts.length === 3) return (parts[0] * 3600) + (parts[1] * 60) + parts[2];
        return 0;
    }

    function extractSubjects(text) {
        if (!text || typeof text !== 'string') return [];
        const matches = text.match(/\bP\d+\b/gi) || [];
        return [...new Set(matches.map(match => match.toUpperCase()))];
    }

    function inferSubjectsFromEntry(entry, report) {
        const explicitSubjects = [
            ...(Array.isArray(entry?.subjects) ? entry.subjects : []),
            ...(Array.isArray(entry?.persons_involved) ? entry.persons_involved : []),
            ...(Array.isArray(entry?.person_ids) ? entry.person_ids : []),
        ].filter(Boolean);

        const detectedSubjects = [
            ...explicitSubjects,
            ...extractSubjects(entry?.description),
            ...extractSubjects(entry?.event),
        ];

        if (entry?.evidence_frame) {
            (report?.persons_identified || []).forEach((person) => {
                if (person.evidence_frame === entry.evidence_frame && person.person_id) {
                    detectedSubjects.push(person.person_id);
                }
            });
        }

        return [...new Set(detectedSubjects.map(subject => String(subject).toUpperCase()))];
    }

    function derivePhaseTitle(phase, index) {
        if (phase.title) return phase.title;
        if (phase.name) return phase.name;
        const description = phase.description || '';
        const firstChunk = description.split(/[.:-]/)[0].trim();
        return firstChunk || `Phase ${phase.phase || index + 1}`;
    }

    function renderEvidenceMiniFrame(frameId, contextLabel, meta = {}) {
        const frame = findFrameById(frameId);
        return `
            <button class="mini-frame-card" type="button" onclick="event.stopPropagation(); window.__openEvidenceFrame('${esc(frameId || '')}', ${JSON.stringify(meta).replace(/"/g, '&quot;')});">
                <div class="mini-frame-thumb">
                    ${frame?.base64 ? `<img src="data:image/jpeg;base64,${frame.base64}" alt="${esc(frameId || 'Evidence frame')}" loading="lazy">` : '<div class="mini-frame-fallback">NO IMAGE</div>'}
                </div>
                <div class="mini-frame-details">
                    <span class="mini-frame-label">${esc(contextLabel)}</span>
                    <span class="mini-frame-id mono-tech">${esc(frameId || 'N/A')}</span>
                </div>
            </button>
        `;
    }

    function buildPhaseCards(report) {
        const phases = report.incident_phases || [];
        if (!phases.length) {
            return '<p class="text-muted">No phase reconstruction available.</p>';
        }

        return phases.map((phase, index) => {
            const subjects = inferSubjectsFromEntry(phase, report);
            const title = derivePhaseTitle(phase, index);
            const linkedFrame = phase.evidence_frame || 'N/A';
            const linkedTimelineIndex = findTimelineIndexByFrame(linkedFrame, report);
            const frameMeta = {
                linkedEvent: `Phase ${phase.phase || index + 1} reconstruction`,
                timelineIndex: linkedTimelineIndex >= 0 ? linkedTimelineIndex : null,
            };

            return `
                <article class="phase-card" onclick="window.__openEvidenceFrame('${esc(linkedFrame)}', ${JSON.stringify(frameMeta).replace(/"/g, '&quot;')})">
                    <div class="phase-card-topline">
                        <span class="phase-index mono-tech">PHASE ${esc(phase.phase || index + 1)}</span>
                        <span class="phase-time mono-tech">${esc(phase.time_range || 'Time range unavailable')}</span>
                    </div>
                    <h4>${esc(title)}</h4>
                    <div class="phase-card-grid">
                        <div class="phase-metric">
                            <span class="phase-metric-label">Subjects</span>
                            <div class="phase-chip-row">
                                ${subjects.length ? subjects.map(subject => `<span class="subject-chip">${esc(subject)}</span>`).join('') : '<span class="subject-chip subject-chip-muted">Unknown</span>'}
                            </div>
                        </div>
                        <div class="phase-metric">
                            <span class="phase-metric-label">Evidence Frames</span>
                            <div class="phase-evidence-row">
                                ${renderEvidenceMiniFrame(linkedFrame, 'Primary frame', frameMeta)}
                            </div>
                        </div>
                    </div>
                    <p class="phase-brief">${esc(phase.description || 'No brief description available.')}</p>
                </article>
            `;
        }).join('');
    }

    function findTimelineIndexByFrame(frameId, report) {
        return (report?.timeline || []).findIndex(item => item.evidence_frame === frameId);
    }

    function updateScrubberPosition(percent) {
        const safePercent = `${Math.max(0, Math.min(100, percent))}%`;
        $('#scrubber-progress').style.width = safePercent;
        $('#scrubber-handle').style.left = safePercent;
    }

    // START
    init();

})();
