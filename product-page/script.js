// script.js — Alfa Hawk Product Page Interactions

(function () {
    'use strict';

    // ═══ NAVBAR SCROLL EFFECT ═══
    const navbar = document.getElementById('navbar');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.scrollY;
        if (currentScroll > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        lastScroll = currentScroll;
    });

    // ═══ MOBILE NAV TOGGLE ═══
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            navToggle.classList.toggle('active');
        });

        // Close menu on link click
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
                navToggle.classList.remove('active');
            });
        });
    }

    // ═══ SCROLL REVEAL ANIMATION ═══
    const revealElements = () => {
        const selectors = [
            '.pain-card', '.feature-card', '.step-card',
            '.sec-card', '.contact-card', '.ep-step',
            '.problem-text', '.security-text', '.enterprise-block',
            '.section-header', '.hero-stats'
        ];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (!el.classList.contains('reveal')) {
                    el.classList.add('reveal');
                }
            });
        });
    };

    const observerCallback = (entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    };

    const observer = new IntersectionObserver(observerCallback, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', () => {
        revealElements();
        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    });

    // Fallback if DOMContentLoaded already fired
    if (document.readyState !== 'loading') {
        revealElements();
        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    }

    // ═══ SMOOTH SCROLL FOR ANCHOR LINKS ═══
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ═══ STAGGERED CARD ANIMATION ═══
    const staggerCards = (selector) => {
        const cards = document.querySelectorAll(selector);
        cards.forEach((card, index) => {
            card.style.transitionDelay = `${index * 0.08}s`;
        });
    };

    staggerCards('.feature-card');
    staggerCards('.pain-card');
    staggerCards('.contact-card');
    staggerCards('.sec-card');

})();
