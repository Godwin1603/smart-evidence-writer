/**
 * ALFA HAWK - PROFESSIONAL FORENSIC WORKSTATION LOGIC
 * V3.0 "Investigation Dashboard" Edition
 */

(function () {
    'use strict';

    // ═══════════════════════════════════════════════════
    // STATE ARCHITECTURE
    // ═══════════════════════════════════════════════════
    const AppState = {
        report: null,              
        media: { duration: 0, type: null }, 
        viewMode: 'investigation', // 'investigation' | 'report'
        activeEventIndex: -1,      
        analysisMode: 'platform',  // 'platform' | 'byo'
    };

    /**
     * CRITICAL: The ONLY way to mutate state.
     * Patches the AppState and dispatches 'StateChanged' to trigger UI re-renders.
     */
    function updateState(patch) {
        Object.assign(AppState, patch);
        document.dispatchEvent(new CustomEvent('StateChanged'));
    }

    // Helper accessors
    function getActiveEvent() { return AppState.report?.timeline?.[AppState.activeEventIndex] || null; }
    function getActiveFrame() {
        const event = getActiveEvent();
        if (!event || !event.evidence_frame || !AppState.report?.video_context?.extracted_frames) return null;
        return AppState.report.video_context.extracted_frames.find(f => f.frame_id === event.evidence_frame) || null;
    }

    // Legacy State (To be migrated)
    let selectedFile = null;
    let currentSessionId = null;
    let pollTimer = null;
    let clientId = null;
    let renderDashboardTaskId = 0;

    const apiBaseMeta = document.querySelector('meta[name="alfa-hawk-api-base"]');
    const defaultApiBase = isLocalHost() ? '' : (window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : 'https://web-production-4c3f2.up.railway.app');
    const API_BASE = normalizeApiBase(window.ALFA_HAWK_API_BASE || apiBaseMeta?.content || defaultApiBase);
    const allowedExtensions = new Set(['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.wav']);

    function normalizeApiBase(value) {
        return value ? value.replace(/\/+$/, '') : '';
    }

    function isLocalHost() {
        return ['localhost', '127.0.0.1'].includes(window.location.hostname);
    }

    function apiUrl(path) {
        if (!path) return API_BASE;
        if (/^https?:\/\//i.test(path)) return path;
        return `${API_BASE}${path}`;
    }

    // ═══════════════════════════════════════════════════
    // INITIALIZATION & PERSISTENCE
    // ═══════════════════════════════════════════════════
    function init() {
        initClientId();
        restoreSessionApiKey();
        setupEventListeners();
        fetchUsageStats();
    }

    function restoreSessionApiKey() {
        const storedKey = sessionStorage.getItem('alfa_hawk_api_key');
        if (storedKey) {
            updateState({ analysisMode: 'byo' });
            $('#ai-api-key').value = storedKey;
            $('input[name="analysisMode"][value="byo"]').checked = true;
            $('#byo-key-group').style.display = 'flex';
        }
    }

    function initClientId() {
        try {
            clientId = localStorage.getItem('alfa_hawk_client_id');
            if (!clientId) {
                clientId = 'AH-' + Math.random().toString(36).substr(2, 9).toUpperCase() + '-' + Date.now();
                localStorage.setItem('alfa_hawk_client_id', clientId);
            }
        } catch (e) {
            // Fallback for private browsing or null origin (file://)
            clientId = 'AH-TEMP-' + Math.random().toString(36).substr(2, 9).toUpperCase();
            console.warn('LocalStorage inaccessible. Using session-only ID:', clientId);
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
    const centerColumn = $('#center-column');
    
    // Views
    const viewInitial = $('#view-initial');
    const viewProgress = $('#view-progress');
    const viewResults = $('#view-results');
    const viewError = $('#view-error');

    // New 3-Column 
    const fvEmpty = $('#fv-empty');
    const fvLoading = $('#fv-loading');
    const fvMissing = $('#fv-missing');
    const fvActive = $('#fv-active');
    const fvImage = $('#fv-image');
    
    const epAiObservation = $('#ep-ai-observation');
    const epFramesRow = $('#ep-frames-row');

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

        analyzeBtn.addEventListener('click', startAnalysis);
        $('#retryBtn').addEventListener('click', resetAll);
        
        // Evidence Panel Buttons
        const epPdfBtn = document.querySelector('#evidence-panel #downloadPdfBtn');
        const epJsonBtn = document.querySelector('#evidence-panel #downloadJsonBtn');
        if (epPdfBtn) epPdfBtn.addEventListener('click', downloadPdf);
        if (epJsonBtn) epJsonBtn.addEventListener('click', downloadJson);
        
        document.addEventListener('StateChanged', renderInvestigationView);

        // Evidence Panel Reference Tabs
        $$('.ep-ref-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const ref = tab.getAttribute('data-ref');
                $$('.ep-ref-tab').forEach(t => t.classList.toggle('active', t === tab));
                $$('.ep-ref-pane').forEach(p => {
                    const isActive = p.id === `ref-${ref}`;
                    p.classList.toggle('active', isActive);
                    p.style.display = isActive ? 'block' : 'none';
                });
            });
        });

        // Frame viewer navigation arrows
        const nextBtn = $('.fv-nav-next');
        const prevBtn = $('.fv-nav-prev');
        if (nextBtn) nextBtn.addEventListener('click', () => navigateEvent(1));
        if (prevBtn) prevBtn.addEventListener('click', () => navigateEvent(-1));
        
        // Global keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (AppState.activeEventIndex === -1 || !AppState.report) return;
            // Ignore if focus is in an input or textarea
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                navigateEvent(1);
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                navigateEvent(-1);
            }
        });
        
        setupFrameZoomPan();

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
                sessionStorage.setItem('alfa_hawk_api_key', key);
            } else {
                sessionStorage.removeItem('alfa_hawk_api_key');
            }

            const uploadRes = await fetch(apiUrl('/api/upload'), { 
                method: 'POST', 
                body: formData,
                headers: { 'X-Client-ID': clientId }
            });

            if (!uploadRes.ok) {
                const errStatus = uploadRes.status;
                const err = await uploadRes.json().catch(() => ({}));
                if (errStatus === 401 || (err.error && err.error.toLowerCase().includes('api key'))) {
                    throw new Error('Invalid or missing API Key. Please check your AI API key setting.');
                }
                throw new Error(err.error || 'Upload failed');
            }

            const uploadData = await uploadRes.json();
            currentSessionId = uploadData.session_id;

            markStepDone('validate');
            updateProgress(15, 'Extracting forensics frames...', 'extract');

            const analyzeRes = await fetch(apiUrl(`/api/analyze/${currentSessionId}`), { 
                method: 'POST',
                headers: { 'X-Client-ID': clientId }
            });
            
            if (!analyzeRes.ok) {
                const errStatus = analyzeRes.status;
                if (errStatus === 401) {
                    throw new Error('Invalid or missing API Key. Please check your AI API key setting.');
                }
            }

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
                updateState({ report: data.report, activeEventIndex: 0 });
                showSection('results');
                fetchUsageStats();
            } else if (status === 'error') {
                showSection('error');
                const errMsg = data.error || 'AI analysis failed';
                $('#error-message').textContent = errMsg.toLowerCase().includes('api key') 
                    ? 'Invalid or missing API Key. Please check your AI API key setting.' 
                    : errMsg;
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
    // RENDER INVESTIGATION VIEW (Phase 3)
    // ═══════════════════════════════════════════════════
    function renderInvestigationView() {
        const report = AppState.report;
        if (!report) return;

        const timeline = report.timeline || [];
        const activeIdx = AppState.activeEventIndex;
        
        // 1. Render Timeline Dots & Event List
        if (timeline.length > 0) {
            const duration = report.evidence_integrity?.duration_seconds || 10;
            
            let dotsHtml = '';
            let listHtml = '';
            
            timeline.forEach((t, idx) => {
                const timeStr = t.time || '00:00';
                const totalSecs = timeToSeconds(timeStr);
                const percent = Math.min(100, duration ? (totalSecs / duration) * 100 : 0);
                const isActive = idx === activeIdx;
                
                // Timeline Dot
                dotsHtml += `<div class="tl-dot ${isActive ? 'active' : ''}" style="left: ${percent}%" title="${esc(t.event)}" onclick="window.__openTimelineEvent(${idx})"></div>`;
                
                // Event Card
                const frame = findFrameById(t.evidence_frame);
                listHtml += `
                    <div class="event-card ${isActive ? 'active' : ''}" id="event-card-${idx}" onclick="window.__openTimelineEvent(${idx})">
                        ${frame?.base64 ? `<img src="data:image/jpeg;base64,${frame.base64}" class="event-card-thumb">` : `<div class="event-card-thumb" style="background:#eee"></div>`}
                        <div class="event-card-body">
                            <span class="event-card-time">${esc(timeStr)}</span>
                            <span class="event-card-title">${esc(t.event)}</span>
                            <span class="event-card-desc">${esc(frame?.description || 'No observation')}</span>
                        </div>
                    </div>
                `;
            });
            
            const timelineDotsEl = $('.timeline-dots');
            if (timelineDotsEl) timelineDotsEl.innerHTML = dotsHtml;
            
            const eventListEl = $('.event-list');
            if (eventListEl) eventListEl.innerHTML = listHtml;
            
            // Scroll active card into view
            if (activeIdx >= 0 && eventListEl) {
                const activeCard = $(`#event-card-${activeIdx}`);
                if (activeCard) {
                    activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }

        // 2. Render Active Frame & Evidence Panel
        const frame = getActiveFrame();
        const event = getActiveEvent();
        
        // Hide all viewer states
        fvEmpty.classList.remove('active');
        fvLoading.classList.remove('active');
        fvMissing.classList.remove('active');
        fvActive.classList.remove('active');

        if (!report) {
            fvEmpty.classList.add('active');
        } else if (!frame) {
            fvMissing.classList.add('active');
        } else {
            // Render Active Frame
            fvActive.classList.add('active');
            fvImage.src = `data:image/jpeg;base64,${frame.base64}`;
            
            // Overlays
            const idBadge = $('#fv-badge-id');
            const confBadge = $('#fv-badge-conf');
            const timeBadge = $('#fv-badge-time');
            const eventLabel = $('#fv-event-title');
            
            if (idBadge) idBadge.textContent = esc(frame.frame_ref || frame.frame_id);
            if (confBadge) confBadge.textContent = `${frame.confidence_percent || 99}% CONF`;
            if (timeBadge) timeBadge.textContent = esc(frame.timestamp || event?.time || '--');
            if (eventLabel) eventLabel.textContent = esc(event?.event || 'Evidence Reference');
            
            // Render Evidence Panel
            if (epAiObservation) {
                epAiObservation.innerHTML = `<strong>AI Analysis:</strong> ${esc(frame.description || event?.event || 'No detailed analysis available.')}`;
            }
            
            if (epFramesRow) {
                // Determine linked frames (all frames for the event's subjects)
                const subjects = inferSubjectsFromEntry(event, report);
                const allFrames = report.evidence_exhibits || [];
                let linkedHtml = '';
                
                allFrames.forEach((f, fIdx) => {
                    // Very basic linking simulation: if same frame or just show a few
                    if (f.frame_id === frame.frame_id || (fIdx < 3)) {
                        const isPrimary = f.frame_id === frame.frame_id;
                        linkedHtml += `<img src="data:image/jpeg;base64,${f.base64}" title="${esc(f.frame_ref || f.frame_id)}" class="${isPrimary ? 'active' : ''}" onclick="window.__openEvidenceFrame('${f.frame_id}')">`;
                    }
                });
                epFramesRow.innerHTML = linkedHtml || '<p class="ep-body">No linked frames.</p>';
            }
        }
        
        // 3. Render Reference Drawer Data
        if ($('#ref-persons')) {
            const persons = report.persons_identified || [];
            if (persons.length) {
                $('#ref-persons').innerHTML = persons.map(p => `
                    <div style="margin-bottom:0.5rem; font-size:var(--text-sm);">
                        <strong>${esc(p.person_id)}</strong> - ${esc(p.observed_role)} 
                        <br><span style="color:var(--text-muted)">Seen: ${esc(p.first_seen)}</span>
                    </div>`).join('');
            } else {
                $('#ref-persons').innerHTML = '<span style="color:var(--text-muted); font-size:var(--text-sm);">No persons detected.</span>';
            }
        }
        
        if ($('#ref-objects')) {
            const objects = report.weapons_objects || [];
            if (objects.length) {
                $('#ref-objects').innerHTML = objects.map(o => `
                    <div style="margin-bottom:0.5rem; font-size:var(--text-sm);">
                        <strong>${esc(o.object)}</strong> <span style="font-size:var(--text-xs); color:var(--text-muted);">(${o.confidence_percent}%)</span>
                        <br><span style="color:var(--text-secondary)">${esc(o.description)}</span>
                    </div>`).join('');
            } else {
                $('#ref-objects').innerHTML = '<span style="color:var(--text-muted); font-size:var(--text-sm);">No objects detected.</span>';
            }
        }
        
        if ($('#ref-frames')) {
            const frames = report.evidence_exhibits || [];
            if (frames.length) {
                let fHtml = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;">';
                frames.forEach(f => {
                    if (!f.base64) return;
                    fHtml += `<img src="data:image/jpeg;base64,${f.base64}" title="${esc(f.frame_ref || f.frame_id)}" onclick="window.__openEvidenceFrame('${f.frame_id}')" style="width:100%; border-radius:2px; cursor:pointer; border:1px solid var(--border-default);">`;
                });
                fHtml += '</div>';
                $('#ref-frames').innerHTML = fHtml;
            } else {
                $('#ref-frames').innerHTML = '<span style="color:var(--text-muted); font-size:var(--text-sm);">No exhibits available.</span>';
            }
        }
    }

    // ═══════════════════════════════════════════════════
    // INTERACTION LOGIC
    // ═══════════════════════════════════════════════════
    function navigateEvent(direction) {
        if (!AppState.report || AppState.activeEventIndex === -1) return;
        const timeline = AppState.report.timeline || [];
        const newIdx = AppState.activeEventIndex + direction;
        if (newIdx >= 0 && newIdx < timeline.length) {
            updateState({ activeEventIndex: newIdx });
        }
    }

    // ═══════════════════════════════════════════════════
    // UI UTILITIES
    // ═══════════════════════════════════════════════════
    function showSection(name) {
        viewInitial.style.display = 'none';
        viewProgress.style.display = 'none';
        viewResults.style.display = 'none';
        viewError.style.display = 'none';
        
        const viewReport = $('#view-report');
        if (viewReport) viewReport.style.display = 'none';
        
        switch(name) {
            case 'initial': viewInitial.style.display = 'block'; break;
            case 'progress': viewProgress.style.display = 'block'; break;
            case 'results': viewResults.style.display = 'block'; break;
            case 'error': viewError.style.display = 'block'; break;
            case 'report': if (viewReport) viewReport.style.display = 'block'; break;
        }
    }
    
    window.__switchViewMode = (mode) => {
        if (!AppState.report) return;
        updateState({ viewMode: mode });
        
        // Update header buttons
        const btnInv = $('#mode-investigation');
        const btnRep = $('#mode-report');
        if (btnInv) btnInv.classList.toggle('active', mode === 'investigation');
        if (btnRep) btnRep.classList.toggle('active', mode === 'report');
        
        if (mode === 'report') {
            showSection('report');
            const ep = $('#evidence-panel');
            if (ep) ep.style.display = 'none';
            // Render the report view dynamically here or later in Phase 4
            if (window.__renderReportMode) {
                window.__renderReportMode();
            }
        } else {
            showSection('results');
            const ep = $('#evidence-panel');
            if (ep) ep.style.display = '';
        }
    };

    window.__renderReportMode = () => {
        const report = AppState.report;
        if (!report) return;
        
        const container = $('#report-container');
        if (!container) return;
        
        const metadata = report.metadata || {};
        const timeline = report.timeline || [];
        const duration = report.evidence_integrity?.duration_seconds || '--';
        
        let html = `
            <div class="report-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid var(--border-strong);">
                <div>
                    <h2 style="margin:0 0 0.5rem 0;">Alfa Hawk Forensic Report</h2>
                    <div style="font-family:var(--font-mono); font-size:var(--text-sm); color:var(--text-secondary);">
                        Case: ${esc(metadata.case_number || 'N/A')} &bull; Officer: ${esc(metadata.officer_id || 'N/A')} <br>
                        Analysis ID: ${esc(metadata.analysis_id || 'N/A')} &bull; Duration: ${duration}s
                    </div>
                </div>
                <div>
                    <button id="btn-export-json" class="btn btn-ghost" onclick="window.__exportReportJson()" style="font-size: var(--text-sm);">Export JSON</button>
                </div>
            </div>
            
            <div style="margin-bottom: 2rem;">
                <h3 style="margin-bottom: 1rem;">Chronological Reconstruction</h3>
                <div style="display:flex; flex-direction:column; gap: 1rem;">
        `;
        
        if (timeline.length === 0) {
            html += '<p>No timeline events extracted.</p>';
        } else {
            timeline.forEach((t, idx) => {
                const frame = findFrameById(t.evidence_frame);
                const confPercent = frame ? (frame.confidence_percent || 99) : '--';
                
                html += `
                    <div style="display:grid; grid-template-columns: 80px 1fr; gap: 1rem; padding: 1rem; border: 1px solid var(--border-default); border-radius: 2px; background: var(--surface-panel);">
                        <div style="font-family:var(--font-mono); font-weight:600;">${esc(t.time || '00:00')}</div>
                        <div>
                            <div style="font-weight:600; margin-bottom: 0.25rem;">${esc(t.event)}</div>
                            <div style="font-size:var(--text-sm); color:var(--text-secondary); margin-bottom: 0.5rem;">${esc(frame?.description || 'No detailed observation.')}</div>
                            <div style="display:flex; justify-content:space-between; align-items:center; font-size:var(--text-xs); color:var(--text-muted);">
                                <span>Confidence: ${confPercent}%</span>
                                <a href="#" onclick="event.preventDefault(); window.__jumpToInvestigation(${idx});" style="color:var(--accent-primary); text-decoration:none; font-weight:600;">[Inspect Frame ${esc(t.evidence_frame)}]</a>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        html += `
                </div>
            </div>
            
            <div style="margin-bottom: 2rem;">
                <h3 style="margin-bottom: 1rem;">Forensic Trace Metadata</h3>
                <pre style="background:var(--surface-raised); border:1px solid var(--border-default); padding:1rem; border-radius:2px; font-family:var(--font-mono); font-size:var(--text-xs); overflow-x:auto;">
${esc(JSON.stringify({
    evidence_integrity: report.evidence_integrity || {},
    detected_entities: {
        persons: (report.persons_identified || []).length,
        objects: (report.weapons_objects || []).length
    }
}, null, 2))}
                </pre>
            </div>
        `;
        
        container.innerHTML = html;
        container.style.padding = '2rem';
        container.style.maxWidth = '900px';
        container.style.margin = '0 auto';
    };
    
    window.__jumpToInvestigation = (index) => {
        window.__switchViewMode('investigation');
        window.__openTimelineEvent(index);
    };
    
    window.__exportReportJson = () => {
        if (!AppState.report) return;
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(AppState.report, null, 2));
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", `alfa_hawk_${AppState.report.metadata?.analysis_id || 'report'}.json`);
        document.body.appendChild(dlAnchorElem);
        dlAnchorElem.click();
        dlAnchorElem.remove();
    };

    function switchTab(tabId) {
        /* activeTab tracked by DOM .active class */
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
            const pctEl = s.querySelector('.f-step-pct');
            
            if (id === activeStepId) {
                s.className = 'f-step active';
                foundActive = true;
                if (pctEl) pctEl.textContent = `${Math.round(percent)}%`;
            } else if (!foundActive) {
                s.className = 'f-step done';
                if (pctEl) pctEl.textContent = '100%';
            } else {
                s.className = 'f-step';
                if (pctEl) pctEl.textContent = '0%';
            }
        });
    }

    function markStepDone(stepId) {
        const step = $(`.f-step[data-step="${stepId}"]`);
        if (step) step.className = 'f-step done';
    }

    function resetProgressSteps() {
        $$('.f-step').forEach(s => {
            s.className = 'f-step';
            const pctEl = s.querySelector('.f-step-pct');
            if (pctEl) pctEl.textContent = '';
        });
        $('#progress-fill').style.width = '0%';
    }

    function showTopLevelError(msg) {
        alert('FORENSIC ERROR: ' + msg);
    }

    function resetAll() {
        clearInterval(pollTimer);
        currentSessionId = null;
        updateState({ report: null, activeEventIndex: -1 });
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
        if (!AppState.report) return;
        const blob = new Blob([JSON.stringify(AppState.report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AlfaHawk_Investigation_Data_${Date.now()}.json`;
        a.click();
    }

    // ═══════════════════════════════════════════════════
    // NAVIGATION HELPERS
    // ═══════════════════════════════════════════════════
    window.__openEvidenceFrame = (frameId) => {
        if (!AppState.report || !frameId || frameId === 'N/A') return;
        
        // Find if this frame is explicitly linked to an event in the timeline
        const timelineIdx = (AppState.report.timeline || []).findIndex(
            item => item.evidence_frame === frameId || item.evidence_frame_ref === frameId
        );
        
        if (timelineIdx >= 0) {
            updateState({ activeEventIndex: timelineIdx });
        } else {
            // Technically a frame could exist without an event, but Phase 3 
            // drives everything through activeEventIndex. If it's isolated,
            // we could either create a fake event context or just warn.
            console.warn('Frame has no direct timeline event association. Isolated viewing not supported in Phase 3 layout yet.');
        }
    };

    window.__openTimelineEvent = (index) => {
        if (!AppState.report) return;
        const timeline = AppState.report.timeline || [];
        if (index >= 0 && index < timeline.length) {
            updateState({ activeEventIndex: index });
        }
    };
    
    function setupFrameZoomPan() {
        const fvImage = $('#fv-image');
        if (!fvImage) return;
        let isZoomed = false;
        
        fvImage.addEventListener('click', (e) => {
            isZoomed = !isZoomed;
            if (isZoomed) {
                fvImage.style.cursor = 'zoom-out';
                fvImage.style.transform = 'scale(2.5)';
                updatePan(e);
            } else {
                fvImage.style.cursor = 'zoom-in';
                fvImage.style.transform = 'none';
                fvImage.style.transformOrigin = 'center center';
            }
        });
        
        fvImage.addEventListener('mousemove', (e) => {
            if (!isZoomed) return;
            updatePan(e);
        });
        
        fvImage.addEventListener('mouseleave', () => {
            if (isZoomed) {
                isZoomed = false;
                fvImage.style.cursor = 'zoom-in';
                fvImage.style.transform = 'none';
                fvImage.style.transformOrigin = 'center center';
            }
        });
        
        function updatePan(e) {
            const rect = fvImage.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            fvImage.style.transformOrigin = `${x}% ${y}%`;
        }
        
        // Reset zoom on state change
        document.addEventListener('StateChanged', () => {
            if (isZoomed) {
                isZoomed = false;
                fvImage.style.cursor = 'zoom-in';
                fvImage.style.transform = 'none';
                fvImage.style.transformOrigin = 'center center';
            }
        });
    }

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
        return (AppState.report?.evidence_exhibits || []).find(
            (f) => f.frame_id === frameId || f.frame_ref === frameId
        );
    }

    function getFrameDisplayId(frame, fallbackId = 'N/A') {
        return frame?.frame_ref || frame?.frame_id || fallbackId;
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



    // START
    init();

})();
