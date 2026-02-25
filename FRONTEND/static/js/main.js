/**
 * SkillVerse Main JavaScript
 * Refactored & Consolidated
 */

'use strict';

// ============================================================================
// 1. UTILITY FUNCTIONS
// ============================================================================

/**
 * Debounce function to limit execution rate
 */
window.debounce = function (func, wait) {
    let timeout;
    return function (...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
};

/**
 * Throttle function to limit execution frequency
 */
window.throttle = function (func, limit) {
    let inThrottle;
    return function (...args) {
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
};

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show Toast Notification (Bootstrap 5)
 */
window.showToast = function (message, type = 'success') {
    let toastContainer = document.getElementById('toast-container');

    // Create container if missing
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1090';
        document.body.appendChild(toastContainer);
    }

    const toastId = 'toast-' + Date.now();
    // Map types to Bootstrap colors and icons
    let icon = 'bi-info-circle-fill';
    let colorClass = 'text-primary';

    if (type === 'success') {
        icon = 'bi-check-circle-fill';
        colorClass = 'text-success';
    } else if (type === 'danger' || type === 'error') {
        icon = 'bi-exclamation-octagon-fill';
        colorClass = 'text-danger';
        type = 'danger'; // Normalize
    } else if (type === 'warning') {
        icon = 'bi-exclamation-triangle-fill';
        colorClass = 'text-warning';
    }

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center border-0 shadow-lg mb-3" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <i class="bi ${icon} ${colorClass} fs-5"></i>
                    <span class="fw-medium">${message}</span>
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    // Insert and initialize
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = document.getElementById(toastId);
    // Ensure Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
        bsToast.show();
        // Clean up DOM after hide
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    } else {
        // Fallback if Bootstrap JS not loaded
        toastEl.classList.add('show');
        setTimeout(() => toastEl.remove(), 5000);
    }
};

/**
 * Modal Focus Trap
 */
function setupModalFocusTrap(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const firstFocusableElement = modal.querySelectorAll(focusableElements)[0];
    const focusableContent = modal.querySelectorAll(focusableElements);
    const lastFocusableElement = focusableContent[focusableContent.length - 1];

    modal.addEventListener('keydown', function (e) {
        const isTabPressed = e.key === 'Tab' || e.keyCode === 9;
        if (!isTabPressed) return;

        if (e.shiftKey) { // Shift + Tab
            if (document.activeElement === firstFocusableElement) {
                lastFocusableElement.focus();
                e.preventDefault();
            }
        } else { // Tab
            if (document.activeElement === lastFocusableElement) {
                firstFocusableElement.focus();
                e.preventDefault();
            }
        }
    });
}

/**
 * Toggle Skeleton Loader
 */
window.toggleSkeleton = function (containerId, show) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (show) {
        container.classList.add('skeleton-loading');
        // Hide actual content
        Array.from(container.children).forEach(el => {
            if (!el.classList.contains('skeleton-loader')) {
                el.style.visibility = 'hidden';
            }
        });
    } else {
        container.classList.remove('skeleton-loading');
        Array.from(container.children).forEach(el => el.style.visibility = 'visible');
        container.classList.add('fade-in');
    }
};

// ============================================================================
// 2. CORE FEATURES
// ============================================================================

/**
 * Search Autocomplete
 */
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchSuggestions = document.getElementById('searchSuggestions');

    if (!searchInput || !searchSuggestions) return;

    const performSearch = window.debounce(async (query) => {
        if (query.length < 2) {
            searchSuggestions.innerHTML = '';
            searchSuggestions.classList.remove('show');
            return;
        }

        try {
            const response = await fetch(`/api/search/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.suggestions && data.suggestions.length > 0) {
                searchSuggestions.innerHTML = data.suggestions
                    .map(s => `<div class="suggestion-item p-2 px-3 hover-bg-light cursor-pointer">${escapeHtml(s)}</div>`)
                    .join('');
                searchSuggestions.classList.add('show');

                document.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', function () {
                        searchInput.value = this.textContent;
                        searchSuggestions.classList.remove('show');
                        searchInput.closest('form').submit();
                    });
                });
            } else {
                searchSuggestions.classList.remove('show');
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }, 300);

    searchInput.addEventListener('input', function () {
        performSearch(this.value.trim());
    });

    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !searchSuggestions.contains(e.target)) {
            searchSuggestions.classList.remove('show');
        }
    });

    // Keyboard navigation
    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown') {
            const firstItem = searchSuggestions.querySelector('.suggestion-item');
            if (firstItem) {
                e.preventDefault();
                // We can't really focus div unless tabindex, but we could highlight
            }
        }
    });
}

/**
 * Toggle Favorite
 */
window.toggleFavorite = async function (serviceId, button) {
    try {
        const response = await fetch(`/service/${serviceId}/favorite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            if (button) {
                const icon = button.querySelector('i');
                if (data.status === 'added') {
                    button.classList.add('active');
                    icon.classList.remove('bi-heart');
                    icon.classList.add('bi-heart-fill');
                    window.showToast('Added to favorites!', 'success');
                } else {
                    button.classList.remove('active');
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                    window.showToast('Removed from favorites', 'info');
                }
            }
        } else if (response.status === 401) {
            window.showToast('Please log in to add favorites', 'warning');
            setTimeout(() => { window.location.href = '/auth/login'; }, 1500);
        } else {
            window.showToast('Error updating favorite', 'danger');
        }
    } catch (error) {
        console.error('Favorite error:', error);
        window.showToast('An error occurred. Please try again.', 'danger');
    }
};

/**
 * Form Validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Validate Helpers
 */
window.validateEmail = function (email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Lazy Image Loading
 */
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        images.forEach(img => imageObserver.observe(img));
    } else {
        images.forEach(img => { img.src = img.dataset.src; });
    }
}

/**
 * Scroll Reveal Animation
 */
function initScrollAnimations() {
    const targets = document.querySelectorAll('.fade-in-up, .reveal-up, .reveal-left, .reveal-right');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    targets.forEach(target => observer.observe(target));
}

// ============================================================================
// 3. UI INTERACTIONS
// ============================================================================

/**
 * Initialize all UI listeners
 */
document.addEventListener('DOMContentLoaded', () => {
    // Core inits
    initializeSearch();
    initializeFormValidation();
    initializeLazyLoading();
    initScrollAnimations();

    // --- Navbar Scroll Effect (Throttled) ---
    const navbar = document.getElementById('mainHelper');
    if (navbar) {
        let lastScrollState = false;
        const updateNavbar = window.throttle(() => {
            const scrolled = window.scrollY > 20;
            if (scrolled !== lastScrollState) {
                lastScrollState = scrolled;
                if (scrolled) {
                    navbar.classList.add('scrolled', 'shadow-sm');
                } else {
                    navbar.classList.remove('scrolled', 'shadow-sm');
                }
            }
        }, 100);
        window.addEventListener('scroll', updateNavbar, { passive: true });
        updateNavbar();
    }

    // --- Theme Toggle ---
    const htmlElement = document.documentElement;
    const themeToggles = document.querySelectorAll('.theme-toggle');
    const themeSwitchInputs = document.querySelectorAll('.theme-switch-input');

    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    function setTheme(theme) {
        htmlElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);

        // Update Icons
        const icons = document.querySelectorAll('.theme-icon');
        icons.forEach(icon => {
            if (theme === 'dark') {
                if (icon.classList.contains('bi-moon-stars-fill')) {
                    icon.classList.replace('bi-moon-stars-fill', 'bi-sun-fill');
                } else if (icon.classList.contains('bi-moon-stars')) {
                    icon.classList.replace('bi-moon-stars', 'bi-sun');
                }
            } else {
                if (icon.classList.contains('bi-sun-fill')) {
                    icon.classList.replace('bi-sun-fill', 'bi-moon-stars-fill');
                } else if (icon.classList.contains('bi-sun')) {
                    icon.classList.replace('bi-sun', 'bi-moon-stars');
                }
            }
        });

        // Update Inputs
        themeSwitchInputs.forEach(input => {
            input.checked = (theme === 'dark');
        });
    }

    // Init Theme
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        setTheme('dark');
    } else {
        setTheme('light');
    }

    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });
    });

    themeSwitchInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            setTheme(e.target.checked ? 'dark' : 'light');
        });
    });

    // --- Skill Filtering (Home Page) ---
    const filterBtns = document.querySelectorAll('.filter-btn');
    const skillItems = document.querySelectorAll('.skill-item');

    if (filterBtns.length > 0) {
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => {
                    b.classList.remove('active', 'btn-primary');
                    b.classList.add('btn-outline-secondary');
                });
                btn.classList.remove('btn-outline-secondary');
                btn.classList.add('active', 'btn-primary');

                const filterValue = btn.getAttribute('data-filter');

                skillItems.forEach(item => {
                    if (filterValue === 'All' || item.getAttribute('data-category') === filterValue) {
                        item.style.display = 'block';
                        // Re-trigger animation
                        item.classList.remove('visible');
                        void item.offsetWidth; // Trigger reflow
                        item.classList.add('visible');
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
    }

    // --- Lightweight Glare Effect (no expensive 3D transforms) ---
    const skillCards = document.querySelectorAll('.skill-card');
    skillCards.forEach(card => {
        if (!card.querySelector('.glare')) {
            const glare = document.createElement('div');
            glare.classList.add('glare');
            card.appendChild(glare);
        }

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const mouseX = ((e.clientX - rect.left) / rect.width) * 100;
            const mouseY = ((e.clientY - rect.top) / rect.height) * 100;
            card.style.setProperty('--mouse-x', `${mouseX}%`);
            card.style.setProperty('--mouse-y', `${mouseY}%`);
        });
    });

    // --- Timeline Animation ---
    const stepBtns = document.querySelectorAll('.step-btn');
    if (stepBtns.length > 0) {
        const stepContents = document.querySelectorAll('.step-content');
        const stepLabels = document.querySelectorAll('.step-label');
        const progressLine = document.getElementById('progressLine');
        let currentStep = 0;
        let stepInterval;

        function activateStep(index) {
            const progressPercentage = (index / (stepBtns.length - 1)) * 100;
            if (progressLine) progressLine.style.width = `${progressPercentage}%`;

            stepBtns.forEach((btn, i) => {
                i <= index ? btn.classList.add('active') : btn.classList.remove('active');
            });

            stepLabels.forEach((lbl, i) => {
                i === index ? lbl.classList.add('active', 'text-primary') : lbl.classList.remove('active', 'text-primary');
            });

            stepContents.forEach(content => {
                content.classList.add('d-none');
                content.classList.remove('active');
            });

            const targetContent = document.querySelector(`.step-content[data-content="${index}"]`);
            if (targetContent) {
                targetContent.classList.remove('d-none');
                setTimeout(() => targetContent.classList.add('active'), 10);
            }
            currentStep = index;
        }

        stepBtns.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                activateStep(index);
                clearInterval(stepInterval);
            });
        });

        const howItWorksSection = document.getElementById('how-it-works');
        if (howItWorksSection) {
            const observer = new IntersectionObserver((entries) => {
                if (entries[0].isIntersecting) {
                    setTimeout(() => {
                        stepInterval = setInterval(() => {
                            let nextStep = (currentStep + 1) % stepBtns.length;
                            activateStep(nextStep);
                        }, 3000);
                    }, 500);
                    observer.disconnect();
                }
            });
            observer.observe(howItWorksSection);
        }
    }

    // --- Cookie Banner ---
    const cookieBanner = document.getElementById('cookieBanner');
    if (cookieBanner && !localStorage.getItem('cookieConsent')) {
        setTimeout(() => {
            cookieBanner.classList.remove('d-none');
        }, 2000);
        document.getElementById('cookieAccept')?.addEventListener('click', () => {
            localStorage.setItem('cookieConsent', 'accepted');
            cookieBanner.classList.add('d-none');
        });
        document.getElementById('cookieDecline')?.addEventListener('click', () => {
            localStorage.setItem('cookieConsent', 'declined');
            cookieBanner.classList.add('d-none');
        });
    }

    // --- Newsletter ---
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const emailInput = this.querySelector('input[type="email"]');
            if (window.validateEmail(emailInput.value.trim())) {
                window.showToast('Thank you for subscribing!', 'success');
                emailInput.value = '';
            } else {
                window.showToast('Please enter a valid email address', 'danger');
            }
        });
    }

    console.log('SkillVerse JS Initialized');
});
