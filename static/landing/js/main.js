/**
 * mr. sarafi | آقای صرافی Landing Page JavaScript
 * Handles language switching, RTL support, mobile menu, FAQ accordion, and smooth scrolling
 */

(function() {
    'use strict';

    // ============================================
    // Language Management
    // ============================================
    const LANGUAGE_KEY = 'mrsarafi_language';
    const DEFAULT_LANGUAGE = 'en';
    
    let currentLanguage = localStorage.getItem(LANGUAGE_KEY) || DEFAULT_LANGUAGE;
    
    // Initialize language on page load
    function initLanguage() {
        setLanguage(currentLanguage);
    }
    
    function setLanguage(lang) {
        currentLanguage = lang;
        localStorage.setItem(LANGUAGE_KEY, lang);
        
        const html = document.documentElement;
        const isRTL = lang === 'fa';
        
        // Set direction
        html.setAttribute('dir', isRTL ? 'rtl' : 'ltr');
        html.setAttribute('lang', lang);
        
        // Update language toggle button
        const langToggle = document.getElementById('languageToggle');
        if (langToggle) {
            const langText = langToggle.querySelector('.lang-text');
            if (langText) {
                langText.textContent = lang === 'en' ? 'FA' : 'EN';
            }
        }
        
        // Update all elements with data attributes
        updateLanguageElements(lang);
    }
    
    function updateLanguageElements(lang) {
        // Update navigation links
        document.querySelectorAll('[data-en][data-fa]').forEach(element => {
            const text = lang === 'en' ? element.getAttribute('data-en') : element.getAttribute('data-fa');
            if (text) {
                element.textContent = text;
            }
        });
        
        // Update logo items
        document.querySelectorAll('.logo-item[data-en][data-fa]').forEach(element => {
            const text = lang === 'en' ? element.getAttribute('data-en') : element.getAttribute('data-fa');
            if (text) {
                element.textContent = text;
            }
        });
    }
    
    // Language toggle button
    const languageToggle = document.getElementById('languageToggle');
    if (languageToggle) {
        languageToggle.addEventListener('click', function() {
            const newLang = currentLanguage === 'en' ? 'fa' : 'en';
            setLanguage(newLang);
        });
    }
    
    // Initialize language on load
    initLanguage();

    // ============================================
    // Mobile Menu Toggle
    // ============================================
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const navMenu = document.getElementById('navMenu');
    const navLinks = document.querySelectorAll('.nav-link');

    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            mobileMenuToggle.classList.toggle('active');
            
            // Animate hamburger icon
            const spans = mobileMenuToggle.querySelectorAll('span');
            if (navMenu.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translateY(8px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translateY(-8px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });

        // Close menu when clicking on a link
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
                const spans = mobileMenuToggle.querySelectorAll('span');
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInsideNav = navMenu.contains(event.target);
            const isClickOnToggle = mobileMenuToggle.contains(event.target);
            
            if (!isClickInsideNav && !isClickOnToggle && navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
                const spans = mobileMenuToggle.querySelectorAll('span');
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }

    // ============================================
    // Navbar Scroll Effect
    // ============================================
    const navbar = document.getElementById('navbar');
    
    if (navbar) {
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // ============================================
    // FAQ Accordion
    // ============================================
    const faqQuestions = document.querySelectorAll('.faq-question');
    
    faqQuestions.forEach(question => {
        question.addEventListener('click', function() {
            const faqItem = this.parentElement;
            const isActive = faqItem.classList.contains('active');
            
            // Close all other FAQ items
            document.querySelectorAll('.faq-item').forEach(item => {
                if (item !== faqItem) {
                    item.classList.remove('active');
                    const answer = item.querySelector('.faq-answer');
                    if (answer) {
                        answer.style.maxHeight = null;
                    }
                }
            });
            
            // Toggle current FAQ item
            if (isActive) {
                faqItem.classList.remove('active');
                const answer = faqItem.querySelector('.faq-answer');
                if (answer) {
                    answer.style.maxHeight = null;
                }
                this.setAttribute('aria-expanded', 'false');
            } else {
                faqItem.classList.add('active');
                const answer = faqItem.querySelector('.faq-answer');
                if (answer) {
                    answer.style.maxHeight = answer.scrollHeight + 'px';
                }
                this.setAttribute('aria-expanded', 'true');
            }
        });
    });

    // ============================================
    // Smooth Scroll for Anchor Links
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if it's just "#"
            if (href === '#' || href === '') {
                return;
            }
            
            const target = document.querySelector(href);
            
            if (target) {
                e.preventDefault();
                const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ============================================
    // Intersection Observer for Fade-in Animations
    // ============================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements for subtle animations
    const animateElements = document.querySelectorAll('.feature-card, .pricing-card, .testimonial-card');
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // ============================================
    // RTL Text Direction Fixes
    // ============================================
    function fixRTLLayout() {
        const isRTL = document.documentElement.getAttribute('dir') === 'rtl';
        
        // Adjust any elements that need special RTL handling
        if (isRTL) {
            // Add any RTL-specific adjustments here if needed
        }
    }
    
    // Call on language change
    const originalSetLanguage = setLanguage;
    setLanguage = function(lang) {
        originalSetLanguage(lang);
        setTimeout(fixRTLLayout, 100);
    };

    // ============================================
    // Console Welcome Message
    // ============================================
    console.log('%cmr. sarafi | آقای صرافی', 'color: #FFD700; font-size: 20px; font-weight: bold;');
    console.log('%cPremium Exchange Management System', 'color: #cccccc; font-size: 14px;');
    console.log('%cWelcome! This page supports English and Persian (RTL).', 'color: #888888; font-size: 12px;');

})();
