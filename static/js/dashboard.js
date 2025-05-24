/**
 * Dashboard JavaScript functionality
 * Handles interactive elements, data refresh, and UI interactions
 */

// Global variables
let refreshTimeout;
let isRefreshing = false;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    setupAutoRefresh();
});

/**
 * Initialize dashboard components
 */
function initializeDashboard() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add animation classes to metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });

    // Add animation to campaign cards
    const campaignCards = document.querySelectorAll('.campaign-card');
    campaignCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, (index + metricCards.length) * 100);
    });

    console.log('Dashboard initialized successfully');
}

/**
 * Setup event listeners for interactive elements
 */
function setupEventListeners() {
    // Refresh button click handler
    const refreshButtons = document.querySelectorAll('[onclick="refreshData()"]');
    refreshButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            refreshData();
        });
    });

    // CSV upload file change handler
    const csvUpload = document.getElementById('csv-upload');
    if (csvUpload) {
        csvUpload.addEventListener('change', function() {
            if (this.files.length > 0) {
                showUploadProgress();
            }
        });
    }

    // Campaign filter buttons
    const filterButtons = document.querySelectorAll('.campaign-filters .btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterCampaigns(this.textContent.trim());
        });
    });

    // Platform filter buttons
    const platformButtons = document.querySelectorAll('.platform-filter-buttons .btn');
    platformButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterByPlatform(this.textContent.trim());
        });
    });

    // Favorite button handlers
    const favoriteButtons = document.querySelectorAll('.favorite-btn');
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleFavorite(this);
        });
    });

    // Campaign card click handlers
    const campaignCards = document.querySelectorAll('.campaign-card');
    campaignCards.forEach(card => {
        card.addEventListener('click', function() {
            const campaignName = this.querySelector('.campaign-name');
            if (campaignName) {
                showCampaignDetails(campaignName.textContent);
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + R for refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            refreshData();
        }
        
        // Ctrl/Cmd + U for upload
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            document.getElementById('csv-upload').click();
        }
    });
}

/**
 * Setup automatic data refresh
 */
function setupAutoRefresh() {
    // Auto-refresh every 5 minutes
    setInterval(() => {
        if (!isRefreshing) {
            refreshDataSilently();
        }
    }, 5 * 60 * 1000);
}

/**
 * Refresh data with user feedback
 */
function refreshData() {
    if (isRefreshing) {
        return;
    }

    isRefreshing = true;
    const refreshButtons = document.querySelectorAll('[onclick="refreshData()"]');
    
    // Update button states
    refreshButtons.forEach(button => {
        const icon = button.querySelector('i');
        if (icon) {
            icon.classList.add('fa-spin');
        }
        button.disabled = true;
    });

    // Show loading indicator
    showNotification('Refreshing data...', 'info', 2000);

    // Submit the refresh form
    const refreshForm = document.getElementById('refresh-form');
    if (refreshForm) {
        refreshForm.submit();
    } else {
        // Fallback: reload the page
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

/**
 * Silent data refresh without user feedback
 */
function refreshDataSilently() {
    if (isRefreshing) {
        return;
    }

    isRefreshing = true;
    
    // Use fetch to silently refresh data
    fetch('/refresh_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.ok) {
            // Optionally update specific elements without full page reload
            updateMetricValues();
        }
    })
    .catch(error => {
        console.error('Silent refresh failed:', error);
    })
    .finally(() => {
        isRefreshing = false;
    });
}

/**
 * Update metric values on the dashboard
 */
function updateMetricValues() {
    // This would typically fetch new data and update the metrics
    // For now, we'll just add a subtle animation to indicate refresh
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach(card => {
        card.style.transition = 'transform 0.3s ease';
        card.style.transform = 'scale(1.02)';
        
        setTimeout(() => {
            card.style.transform = 'scale(1)';
        }, 300);
    });
}

/**
 * Show upload progress
 */
function showUploadProgress() {
    const progressHtml = `
        <div class="upload-progress" id="upload-progress">
            <div class="progress mb-2">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%"></div>
            </div>
            <small class="text-muted">Uploading CSV file...</small>
        </div>
    `;
    
    showNotification(progressHtml, 'info', 0);
    
    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        
        const progressBar = document.querySelector('#upload-progress .progress-bar');
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 200);
}

/**
 * Filter campaigns by platform or type
 */
function filterCampaigns(filterType) {
    const campaignCards = document.querySelectorAll('.campaign-card');
    const filterButtons = document.querySelectorAll('.campaign-filters .btn');
    
    // Update button states
    filterButtons.forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-secondary');
    });
    
    event.target.classList.remove('btn-outline-secondary');
    event.target.classList.add('btn-primary');
    
    // Filter campaigns
    campaignCards.forEach(card => {
        const platform = card.querySelector('.campaign-platform').textContent;
        
        if (filterType === 'All' || platform.includes(filterType)) {
            card.style.display = 'block';
            card.classList.add('fade-in');
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Filter campaigns by platform (for reports page)
 */
function filterByPlatform(platform) {
    // This function is used in reports.html
    if (typeof window.location !== 'undefined') {
        const url = new URL(window.location);
        if (platform === 'All') {
            url.searchParams.delete('platform');
        } else {
            url.searchParams.set('platform', platform);
        }
        window.location.href = url.toString();
    }
}

/**
 * Toggle favorite status
 */
function toggleFavorite(button) {
    const icon = button.querySelector('i');
    
    if (icon.classList.contains('far')) {
        // Add to favorites
        icon.classList.remove('far', 'fa-heart');
        icon.classList.add('fas', 'fa-heart');
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-danger');
        showNotification('Added to favorites', 'success', 2000);
    } else {
        // Remove from favorites
        icon.classList.remove('fas', 'fa-heart');
        icon.classList.add('far', 'fa-heart');
        button.classList.remove('btn-danger');
        button.classList.add('btn-outline-secondary');
        showNotification('Removed from favorites', 'info', 2000);
    }
}

/**
 * Show campaign details modal
 */
function showCampaignDetails(campaignName) {
    // This would typically fetch campaign details via AJAX
    // For now, show a simple modal with the campaign name
    const modalHtml = `
        <div class="modal fade" id="campaignDetailsModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Campaign Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <h6>${campaignName}</h6>
                        <p>Campaign details would be loaded here.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('campaignDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add new modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('campaignDetailsModal'));
    modal.show();
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notificationHtml = `
        <div class="alert alert-${type} alert-dismissible fade show notification-toast" 
             role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', notificationHtml);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            const notification = document.querySelector('.notification-toast');
            if (notification) {
                const alert = new bootstrap.Alert(notification);
                alert.close();
            }
        }, duration);
    }
}

/**
 * Format numbers with thousands separators
 */
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

/**
 * Format currency values
 */
function formatCurrency(amount, currency = 'BDT') {
    if (currency === 'BDT') {
        return `৳ ${formatNumber(Math.round(amount))}`;
    }
    return `${currency} ${formatNumber(Math.round(amount))}`;
}

/**
 * Calculate percentage change
 */
function calculatePercentageChange(current, previous) {
    if (previous === 0) return 0;
    return ((current - previous) / previous) * 100;
}

/**
 * Get trend indicator HTML
 */
function getTrendIndicator(change) {
    const isPositive = change >= 0;
    const iconClass = isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
    const textClass = isPositive ? 'text-success' : 'text-danger';
    
    return `
        <span class="${textClass}">
            <i class="fas ${iconClass}"></i>
            ${Math.abs(change).toFixed(1)}%
        </span>
    `;
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard', 'success', 2000);
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Copied to clipboard', 'success', 2000);
    }
}

/**
 * Generate shareable link
 */
function generateShareableLink() {
    const url = window.location.href;
    copyToClipboard(url);
}

/**
 * Print dashboard
 */
function printDashboard() {
    window.print();
}

/**
 * Export dashboard data
 */
function exportDashboard(format = 'pdf') {
    showNotification(`Exporting dashboard as ${format.toUpperCase()}...`, 'info', 3000);
    
    // Create a form to submit the export request
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/export_dashboard';
    
    const formatInput = document.createElement('input');
    formatInput.type = 'hidden';
    formatInput.name = 'format';
    formatInput.value = format;
    form.appendChild(formatInput);
    
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

/**
 * Handle responsive sidebar toggle
 */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('show');
    }
}

/**
 * Initialize mobile menu if needed
 */
function initializeMobileMenu() {
    if (window.innerWidth <= 992) {
        const menuToggle = document.createElement('button');
        menuToggle.className = 'btn btn-outline-secondary d-lg-none';
        menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        menuToggle.onclick = toggleSidebar;
        
        const headerActions = document.querySelector('.header-actions');
        if (headerActions) {
            headerActions.insertBefore(menuToggle, headerActions.firstChild);
        }
    }
}

// Handle window resize
window.addEventListener('resize', function() {
    initializeMobileMenu();
});

// Initialize mobile menu on load
initializeMobileMenu();

// Global functions that can be called from HTML
window.refreshData = refreshData;
window.filterByPlatform = filterByPlatform;
window.toggleSidebar = toggleSidebar;
window.exportDashboard = exportDashboard;
window.printDashboard = printDashboard;
window.generateShareableLink = generateShareableLink;
