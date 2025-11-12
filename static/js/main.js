// static/js/main.js

/**
 * Toast Notification System
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type} rounded-lg p-4 mb-2 shadow-lg flex items-center justify-between`;
    
    const icon = getToastIcon(type);
    
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="${icon} mr-3 text-xl"></i>
            <span>${message}</span>
        </div>
        <button onclick="this.parentElement.remove()" class="ml-4 hover:opacity-75">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function getToastIcon(type) {
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    return icons[type] || icons.info;
}

/**
 * Loading Overlay
 */
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Form Validation
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('[required]');
    
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('border-red-500');
            showToast(`${input.name} is required`, 'error');
        } else {
            input.classList.remove('border-red-500');
        }
    });
    
    return isValid;
}

/**
 * Copy to Clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        showToast('Failed to copy', 'error');
    });
}

/**
 * Format Numbers
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Debounce Function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Smooth Scroll
 */
function smoothScroll(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Local Storage Helpers (Note: Not for artifacts, but for general use)
 */
const storage = {
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Storage set error:', e);
            return false;
        }
    },
    
    get: (key) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.error('Storage get error:', e);
            return null;
        }
    },
    
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('Storage remove error:', e);
            return false;
        }
    }
};

/**
 * API Helper Functions
 */
const api = {
    async get(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API GET error:', error);
            throw error;
        }
    },
    
    async post(url, data) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API POST error:', error);
            throw error;
        }
    },
    
    async delete(url) {
        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API DELETE error:', error);
            throw error;
        }
    }
};

/**
 * Bookmark Functions
 */
function bookmarkProject(projectId) {
    showLoading();
    
    api.post('/api/bookmark', {
        github_reference_id: projectId
    })
    .then(data => {
        hideLoading();
        if (data.success) {
            showToast('Project bookmarked!', 'success');
            
            // Update button state
            const btn = document.querySelector(`button[data-project-id="${projectId}"]`);
            if (btn) {
                btn.innerHTML = '<i class="fas fa-check mr-1"></i> Saved';
                btn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
                btn.classList.add('bg-green-500', 'hover:bg-green-600');
                btn.disabled = true;
            }
        } else {
            showToast(data.error || 'Failed to bookmark', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showToast('Error: ' + error.message, 'error');
    });
}

function removeBookmark(projectId) {
    if (!confirm('Remove this bookmark?')) return;
    
    showLoading();
    
    api.delete(`/api/bookmark/${projectId}`)
    .then(data => {
        hideLoading();
        if (data.success) {
            showToast('Bookmark removed', 'success');
            
            // Remove card from view
            const card = document.querySelector(`[data-project-id="${projectId}"]`);
            if (card) {
                const parentCard = card.closest('.bookmark-card');
                if (parentCard) {
                    parentCard.style.opacity = '0';
                    setTimeout(() => parentCard.remove(), 300);
                }
            }
        } else {
            showToast(data.error || 'Failed to remove bookmark', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showToast('Error: ' + error.message, 'error');
    });
}

function toggleFavorite(projectId, button) {
    // Favorites feature removed - this is deprecated
    showToast('Favorites feature has been removed. Use bookmarks instead.', 'info');
}

/**
 * Initialize tooltips
 */
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.classList.add('tooltip');
    });
}

/**
 * Character Counter for Textareas
 */
function initCharacterCounters() {
    const textareas = document.querySelectorAll('textarea[maxlength]');
    
    textareas.forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        const counterId = `${textarea.id}-counter`;
        
        // Create counter element if doesn't exist
        let counter = document.getElementById(counterId);
        if (!counter) {
            counter = document.createElement('div');
            counter.id = counterId;
            counter.className = 'text-sm text-gray-500 text-right mt-1';
            counter.textContent = `0 / ${maxLength}`;
            textarea.parentNode.appendChild(counter);
        }
        
        // Update counter on input
        textarea.addEventListener('input', function() {
            const currentLength = this.value.length;
            counter.textContent = `${currentLength} / ${maxLength}`;
            
            if (currentLength >= maxLength * 0.9) {
                counter.classList.add('text-red-500');
                counter.classList.remove('text-gray-500');
            } else {
                counter.classList.remove('text-red-500');
                counter.classList.add('text-gray-500');
            }
        });
    });
}

/**
 * Lazy Load Images
 */
function initLazyLoad() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
}

/**
 * Animate on Scroll
 */
function initScrollAnimations() {
    const elements = document.querySelectorAll('.fade-in-scroll');
    
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, {
            threshold: 0.1
        });
        
        elements.forEach(el => observer.observe(el));
    } else {
        // Fallback - show all elements
        elements.forEach(el => el.classList.add('fade-in'));
    }
}

/**
 * Export Data to CSV
 */
function exportToCSV(data, filename = 'export.csv') {
    const csvContent = convertToCSV(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, filename);
    } else {
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    }
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Add headers
    csvRows.push(headers.join(','));
    
    // Add data rows
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            return `"${value}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

/**
 * Mobile Menu Toggle
 */
function initMobileMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (menuBtn && mobileMenu) {
        menuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

/**
 * Password Toggle
 */
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    const icon = field.nextElementSibling?.querySelector('i');
    
    if (field.type === 'password') {
        field.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        field.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

/**
 * Initialize everything on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize character counters
    initCharacterCounters();
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize lazy loading
    initLazyLoad();
    
    // Initialize scroll animations
    initScrollAnimations();
    
    // Initialize mobile menu
    initMobileMenu();
    
    // Add fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    console.log('🚀 CoChain.ai initialized successfully!');
});

/**
 * Handle network errors gracefully
 */
window.addEventListener('online', () => {
    showToast('Connection restored', 'success');
});

window.addEventListener('offline', () => {
    showToast('No internet connection', 'error');
});

/**
 * Prevent form resubmission on page refresh
 */
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

/**
 * Global error handler
 */
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    // Optionally show user-friendly error message
    // showToast('An error occurred. Please try again.', 'error');
});

/**
 * Unhandled promise rejection handler
 */
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // Optionally show user-friendly error message
    // showToast('An error occurred. Please try again.', 'error');
});