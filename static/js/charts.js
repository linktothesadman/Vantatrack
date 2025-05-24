/**
 * Charts JavaScript functionality
 * Handles Chart.js initialization and data visualization
 */

// Global chart instances
let impressionClickChart = null;
let platformChart = null;
let trendsChart = null;

// Chart.js default configuration
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#6b7280';

/**
 * Initialize the main Impression vs Click chart
 */
function initializeImpressionClickChart(data) {
    const ctx = document.getElementById('impressionClickChart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (impressionClickChart) {
        impressionClickChart.destroy();
    }

    // Prepare data
    const labels = data.dates || [];
    const impressionsData = data.impressions || [];
    const clicksData = data.clicks || [];

    // Chart configuration
    const config = {
        type: 'line',
        data: {
            labels: labels.map(date => {
                const d = new Date(date);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }),
            datasets: [
                {
                    label: 'Impressions',
                    data: impressionsData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Clicks',
                    data: clicksData,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#f59e0b',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false // We use custom legend
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        title: function(context) {
                            return labels[context[0].dataIndex];
                        },
                        label: function(context) {
                            const label = context.dataset.label;
                            const value = context.parsed.y;
                            return `${label}: ${formatNumber(value)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(229, 231, 235, 0.5)',
                        drawBorder: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            },
            elements: {
                point: {
                    hoverBorderWidth: 3
                }
            }
        }
    };

    // Create chart
    impressionClickChart = new Chart(ctx, config);
}

/**
 * Initialize platform distribution chart
 */
function initializePlatformChart(data) {
    const ctx = document.getElementById('platformChart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (platformChart) {
        platformChart.destroy();
    }

    const config = {
        type: 'doughnut',
        data: {
            labels: data.labels || ['Facebook', 'Google', 'ShareIT'],
            datasets: [{
                data: data.values || [0, 0, 0],
                backgroundColor: [
                    '#1877f2',
                    '#4285f4',
                    '#8b5cf6'
                ],
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const label = context.label;
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${formatNumber(value)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };

    platformChart = new Chart(ctx, config);
}

/**
 * Initialize trends chart
 */
function initializeTrendsChart(data) {
    const ctx = document.getElementById('trendsChart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (trendsChart) {
        trendsChart.destroy();
    }

    const config = {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Spend',
                data: data.spend || [],
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                borderColor: '#6366f1',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return `Spend: ৳${formatNumber(context.parsed.y)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(229, 231, 235, 0.5)',
                        drawBorder: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return '৳' + formatNumber(value);
                        }
                    }
                }
            }
        }
    };

    trendsChart = new Chart(ctx, config);
}

/**
 * Initialize mini charts for metric cards
 */
function initializeMiniCharts() {
    const miniChartElements = document.querySelectorAll('.mini-chart');
    
    miniChartElements.forEach(element => {
        const data = JSON.parse(element.dataset.chartData || '[]');
        
        const config = {
            type: 'line',
            data: {
                labels: data.map((_, index) => index),
                datasets: [{
                    data: data,
                    borderColor: element.dataset.color || '#6366f1',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: false
                    }
                },
                elements: {
                    point: {
                        radius: 0
                    }
                }
            }
        };

        new Chart(element, config);
    });
}

/**
 * Update chart data dynamically
 */
function updateChartData(chart, newData) {
    if (!chart || !newData) return;

    chart.data.datasets.forEach((dataset, index) => {
        if (newData.datasets && newData.datasets[index]) {
            dataset.data = newData.datasets[index].data;
        }
    });

    if (newData.labels) {
        chart.data.labels = newData.labels;
    }

    chart.update('active');
}

/**
 * Animate chart on scroll
 */
function animateChartsOnScroll() {
    const charts = document.querySelectorAll('canvas');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const chart = Chart.getChart(entry.target);
                if (chart) {
                    chart.update('active');
                }
            }
        });
    }, {
        threshold: 0.3
    });

    charts.forEach(chart => {
        observer.observe(chart);
    });
}

/**
 * Create chart download functionality
 */
function downloadChart(chartId, filename = 'chart') {
    const chart = Chart.getChart(chartId);
    if (!chart) return;

    const url = chart.toBase64Image();
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = url;
    link.click();
}

/**
 * Format numbers for charts
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Generate chart colors
 */
function generateChartColors(count) {
    const colors = [
        '#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
        '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6366f1'
    ];
    
    return colors.slice(0, count);
}

/**
 * Create responsive chart configuration
 */
function createResponsiveConfig(baseConfig) {
    return {
        ...baseConfig,
        options: {
            ...baseConfig.options,
            responsive: true,
            maintainAspectRatio: false,
            onResize: function(chart, size) {
                // Adjust font sizes for mobile
                if (size.width < 400) {
                    chart.options.plugins.legend.labels.font.size = 10;
                    chart.options.scales.x.ticks.font.size = 10;
                    chart.options.scales.y.ticks.font.size = 10;
                } else {
                    chart.options.plugins.legend.labels.font.size = 12;
                    chart.options.scales.x.ticks.font.size = 12;
                    chart.options.scales.y.ticks.font.size = 12;
                }
            }
        }
    };
}

/**
 * Export chart data as CSV
 */
function exportChartDataAsCSV(chart, filename = 'chart-data') {
    if (!chart) return;

    const labels = chart.data.labels;
    const datasets = chart.data.datasets;
    
    let csv = 'Date';
    datasets.forEach(dataset => {
        csv += ',' + dataset.label;
    });
    csv += '\n';

    labels.forEach((label, index) => {
        csv += label;
        datasets.forEach(dataset => {
            csv += ',' + (dataset.data[index] || 0);
        });
        csv += '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${filename}.csv`;
    link.href = url;
    link.click();
    window.URL.revokeObjectURL(url);
}

/**
 * Initialize all charts when called
 */
function initializeAllCharts() {
    // Initialize mini charts
    initializeMiniCharts();
    
    // Setup scroll animations
    animateChartsOnScroll();
    
    console.log('All charts initialized');
}

// Auto-initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAllCharts();
});

// Global functions
window.initializeImpressionClickChart = initializeImpressionClickChart;
window.initializePlatformChart = initializePlatformChart;
window.initializeTrendsChart = initializeTrendsChart;
window.updateChartData = updateChartData;
window.downloadChart = downloadChart;
window.exportChartDataAsCSV = exportChartDataAsCSV;
