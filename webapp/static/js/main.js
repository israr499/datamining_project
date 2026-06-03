// ============================================
// ElectroGuard Main JavaScript
// ============================================

// Global variables
let currentPage = 'dashboard';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('ElectroGuard Web Application Loaded');
    
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Add tooltips to elements with data-tooltip attribute
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = el.dataset.tooltip;
        el.addEventListener('mouseenter', () => {
            tooltip.style.display = 'block';
            document.body.appendChild(tooltip);
            const rect = el.getBoundingClientRect();
            tooltip.style.top = rect.bottom + 5 + 'px';
            tooltip.style.left = rect.left + 'px';
        });
        el.addEventListener('mouseleave', () => tooltip.remove());
    });
});

// Utility function to format numbers
function formatNumber(num, decimals = 2) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(num);
}

// Utility function to format dates
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }, 10);
}

// Utility function to download data as CSV
function downloadCSV(data, filename = 'electroguard_export.csv') {
    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => Object.values(row).join(','));
    const csv = [headers, ...rows].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Utility function to get query parameters
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// Theme management (if implemented)
function setTheme(theme) {
    localStorage.setItem('electroguard-theme', theme);
    if (theme === 'dark') {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }
}

function getTheme() {
    return localStorage.getItem('electroguard-theme') || 'light';
}

// Error handling wrapper for fetch requests
async function fetchWithErrorHandling(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        showToast(error.message, 'error');
        return null;
    }
}

// Auto-refresh functionality for dashboards
let refreshInterval = null;

function startAutoRefresh(intervalMs = 30000, refreshCallback) {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(refreshCallback, intervalMs);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Page visibility API handling
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, reduce polling frequency
        console.log('Page hidden - reducing updates');
    } else {
        // Page is visible again, refresh data
        console.log('Page visible - refreshing data');
        window.location.reload();
    }
});

// Export utilities globally
window.electroguard = {
    formatNumber,
    formatDate,
    showToast,
    downloadCSV,
    getQueryParam,
    setTheme,
    getTheme,
    startAutoRefresh,
    stopAutoRefresh
};