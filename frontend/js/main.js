// main.js - Global functionality for OceanGuardian application

document.addEventListener('DOMContentLoaded', function () {
    // Initialize global functionality
    initializeGlobalComponents();
    initializeAuthButtons();
    initializeGenericTabSwitching();
    
    console.log('🌊 OceanGuardian Main JS Loaded');
});

// Initialize global UI components
function initializeGlobalComponents() {
    // Global notification system (if not already initialized by dashboard.js)
    if (typeof window.showNotification === 'undefined') {
        window.showNotification = function(message, type = 'info') {
            // Fallback notification system for non-dashboard pages
            const notification = document.createElement('div');
            notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' || type === 'danger' ? 'danger' : type === 'warning' ? 'warning' : 'info'} alert-dismissible fade show`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1050;
                min-width: 300px;
                max-width: 400px;
            `;
            
            notification.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px;">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' || type === 'danger' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                    <span>${escapeHtml(message)}</span>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove after 5 seconds for non-danger alerts
            if (type !== 'danger' && type !== 'error') {
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 5000);
            }
        };
    }

    // Global HTML escaping function
    if (typeof window.escapeHtml === 'undefined') {
        window.escapeHtml = function(unsafe) {
            if (unsafe === undefined || unsafe === null) return '';
            return String(unsafe)
                .replaceAll('&','&amp;')
                .replaceAll('<','&lt;')
                .replaceAll('>','&gt;')
                .replaceAll('"','&quot;')
                .replaceAll("'", '&#039;');
        };
    }
}

// Initialize authentication buttons
function initializeAuthButtons() {
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }

    if (signupBtn) {
        signupBtn.addEventListener('click', handleSignup);
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// Handle login functionality
function handleLogin() {
    // Check if we're on dashboard page (dashboard.js handles its own modals)
    if (isDashboardPage()) {
        showNotification('Login functionality integrated with dashboard', 'info');
        return;
    }

    // For other pages, show basic login prompt or redirect
    const shouldRedirect = confirm('Redirect to login page?');
    if (shouldRedirect) {
        // Replace with actual login page URL
        window.location.href = 'login.html';
    } else {
        showNotification('Login modal would open here', 'info');
    }
}

// Handle signup functionality  
function handleSignup() {
    // Check if we're on dashboard page
    if (isDashboardPage()) {
        showNotification('Signup functionality integrated with dashboard', 'info');
        return;
    }

    // For other pages, show basic signup prompt or redirect
    const shouldRedirect = confirm('Redirect to signup page?');
    if (shouldRedirect) {
        // Replace with actual signup page URL
        window.location.href = 'signup.html';
    } else {
        showNotification('Signup modal would open here', 'info');
    }
}

// Handle logout functionality
function handleLogout() {
    const confirmLogout = confirm('Are you sure you want to logout?');
    if (confirmLogout) {
        // Clear any stored user data
        clearUserSession();
        
        showNotification('Logged out successfully', 'success');
        
        // Redirect to homepage after a short delay
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1500);
    }
}

// Clear user session data
function clearUserSession() {
    // Clear localStorage/sessionStorage if used
    try {
        localStorage.removeItem('userToken');
        localStorage.removeItem('userData');
        sessionStorage.clear();
    } catch (e) {
        console.warn('Unable to clear session storage:', e);
    }
    
    // Clear any cookies if used
    document.cookie.split(";").forEach(function(c) { 
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
    });
}

// Generic tab switching for non-dashboard pages
function initializeGenericTabSwitching() {
    // Only initialize if we're NOT on the dashboard page
    // Dashboard.js handles its own tab switching
    if (isDashboardPage()) {
        return; // Let dashboard.js handle tab switching
    }

    const tabBtns = document.querySelectorAll('.tab-btn:not([data-dashboard-managed])');
    
    if (tabBtns.length > 0) {
        tabBtns.forEach(button => {
            button.addEventListener('click', function() {
                handleGenericTabSwitch(this);
            });
        });
    }
}

// Handle generic tab switching (for non-dashboard pages)
function handleGenericTabSwitch(clickedButton) {
    const tabContainer = clickedButton.closest('.tab-container') || document;
    
    // Remove active class from all buttons in the same container
    tabContainer.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Remove active class from all tab content in the same container
    tabContainer.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Add active class to clicked button
    clickedButton.classList.add('active');

    // Show corresponding content
    const tabName = clickedButton.getAttribute('data-tab');
    const tabContent = tabContainer.querySelector(`#${tabName}Tab`) || 
                      document.getElementById(`${tabName}Tab`);
    
    if (tabContent) {
        tabContent.classList.add('active');
        
        // Trigger custom event for other scripts to listen to
        const tabSwitchEvent = new CustomEvent('tabSwitched', {
            detail: { tabName: tabName, button: clickedButton, content: tabContent }
        });
        document.dispatchEvent(tabSwitchEvent);
        
        showNotification(`Switched to ${tabName} tab`, 'info');
    } else {
        console.warn(`Tab content not found for: ${tabName}`);
    }
}

// Check if we're currently on the dashboard page
function isDashboardPage() {
    return document.getElementById('map') !== null || 
           document.querySelector('.main-container') !== null ||
           document.title.includes('Dashboard') ||
           window.location.pathname.includes('dashboard');
}

// Global utility functions
window.OceanGuardianUtils = {
    // Format timestamp for display
    formatTimestamp: function(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        if (isNaN(date.getTime())) return timestamp;
        
        return new Intl.DateTimeFormat('en-IN', {
            timeZone: 'Asia/Kolkata',
            dateStyle: 'medium',
            timeStyle: 'short'
        }).format(date);
    },

    // Validate email format
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validate phone number (Indian format)
    isValidPhone: function(phone) {
        const phoneRegex = /^[+]?[0-9]{10,15}$/;
        return phoneRegex.test(phone.replace(/\s|-/g, ''));
    },

    // Get user's location (if permitted)
    getUserLocation: function() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser.'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                position => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    });
                },
                error => {
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        });
    },

    // Debounce function for search/input handling
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function for scroll/resize events
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Global event listeners for common functionality
document.addEventListener('click', function(e) {
    // Handle external links
    if (e.target.matches('a[href^="http"]:not([target="_blank"])')) {
        e.target.setAttribute('target', '_blank');
        e.target.setAttribute('rel', 'noopener noreferrer');
    }
    
    // Handle back buttons
    if (e.target.matches('.back-btn, [data-action="back"]')) {
        e.preventDefault();
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = 'index.html';
        }
    }
});

// Handle form submissions globally (basic validation)
document.addEventListener('submit', function(e) {
    const form = e.target;
    
    // Skip if form has data-no-validation attribute
    if (form.hasAttribute('data-no-validation')) {
        return;
    }
    
    // Skip if we're on dashboard (dashboard.js handles its forms)
    if (isDashboardPage()) {
        return;
    }
    
    // Basic validation for email fields
    const emailInputs = form.querySelectorAll('input[type="email"]');
    for (let input of emailInputs) {
        if (input.value && !OceanGuardianUtils.isValidEmail(input.value)) {
            e.preventDefault();
            showNotification('Please enter a valid email address', 'error');
            input.focus();
            return;
        }
    }
    
    // Basic validation for phone fields
    const phoneInputs = form.querySelectorAll('input[type="tel"], input[name*="phone"]');
    for (let input of phoneInputs) {
        if (input.value && !OceanGuardianUtils.isValidPhone(input.value)) {
            e.preventDefault();
            showNotification('Please enter a valid phone number', 'error');
            input.focus();
            return;
        }
    }
});

// Global error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    
    // Don't show error notifications on dashboard (it has its own error handling)
    if (!isDashboardPage()) {
        showNotification('An unexpected error occurred', 'error');
    }
});

// Handle offline/online status
window.addEventListener('online', function() {
    showNotification('Connection restored', 'success');
});

window.addEventListener('offline', function() {
    showNotification('You are offline. Some features may not work.', 'warning');
});

// Expose some functions globally for backward compatibility
window.toggleUserMenu = function() {
    if (typeof window.showNotification === 'function') {
        showNotification('User menu functionality will be implemented here', 'info');
    }
};