(function () {
    'use strict';

    const topbar = document.getElementById('topbar');
    const navToggle = document.getElementById('navToggle');
    const topnav = document.getElementById('topnav');
    const reportModal = document.getElementById('reportModal');
    const reportFrame = document.getElementById('reportFrame');
    const reportModalTitle = document.getElementById('reportModalTitle');
    const reportModalFile = document.getElementById('reportModalFile');
    const modalClose = document.getElementById('modalClose');
    const reportCards = document.querySelectorAll('.report-card');

    function syncTopbarState() {
        if (!topbar) return;
        topbar.classList.toggle('is-scrolled', window.scrollY > 18);
    }

    function closeNav() {
        if (!topnav || !navToggle) return;
        topnav.classList.remove('is-open');
        navToggle.setAttribute('aria-expanded', 'false');
    }

    function toggleNav() {
        if (!topnav || !navToggle) return;
        const isOpen = topnav.classList.toggle('is-open');
        navToggle.setAttribute('aria-expanded', String(isOpen));
    }

    function openReportModal(src, title, fileLabel) {
        if (!reportModal || !reportFrame) return;
        reportModalTitle.textContent = title || 'Example Report';
        reportModalFile.textContent = fileLabel || 'report.pdf';
        reportFrame.src = `${src}#toolbar=0&navpanes=0&scrollbar=1&view=FitH`;
        reportModal.classList.add('is-open');
        reportModal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
    }

    function closeReportModal() {
        if (!reportModal || !reportFrame) return;
        reportModal.classList.remove('is-open');
        reportModal.setAttribute('aria-hidden', 'true');
        reportFrame.src = '';
        document.body.classList.remove('modal-open');
    }

    function smoothAnchorNavigation(event) {
        const trigger = event.target.closest('a[href^="#"]');
        if (!trigger) return;
        const targetId = trigger.getAttribute('href');
        if (!targetId || targetId === '#') return;
        const target = document.querySelector(targetId);
        if (!target) return;

        event.preventDefault();
        closeNav();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    window.addEventListener('scroll', syncTopbarState, { passive: true });
    syncTopbarState();

    if (navToggle) {
        navToggle.addEventListener('click', toggleNav);
    }

    document.addEventListener('click', smoothAnchorNavigation);

    if (topnav) {
        topnav.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', closeNav);
        });
    }

    reportCards.forEach((card) => {
        card.addEventListener('click', () => {
            openReportModal(
                card.dataset.reportSrc,
                card.dataset.reportTitle,
                card.dataset.reportFile
            );
        });
    });

    if (modalClose) {
        modalClose.addEventListener('click', closeReportModal);
    }

    if (reportModal) {
        reportModal.addEventListener('click', (event) => {
            if (event.target instanceof HTMLElement && event.target.dataset.closeModal === 'true') {
                closeReportModal();
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeReportModal();
            closeNav();
        }
    });
})();