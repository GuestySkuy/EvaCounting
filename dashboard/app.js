// Global Chart Object
let occupancyChart = null;

// API endpoints
const API_OCCUPANCY = '/api/occupancy';
const API_EVENTS = '/api/events';
const API_SUMMARY = '/api/summary';
const API_RESET = '/api/reset';

// Configuration
const REFRESH_RATE_STATS = 2000;   // 2s
const REFRESH_RATE_LOGS = 5000;    // 5s
const REFRESH_RATE_CHART = 10000;  // 10s

// DOM elements
const valCurrent = document.getElementById('val-current');
const valIn = document.getElementById('val-in');
const valOut = document.getElementById('val-out');
const progressBar = document.getElementById('progress-bar');
const logsTbody = document.getElementById('logs-tbody');
const btnReset = document.getElementById('btn-reset');
const statusText = document.querySelector('.system-status span');
const statusIndicator = document.querySelector('.status-indicator');

// Initialize the Application
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    
    // Fetch initial data
    fetchStats();
    fetchLogs();
    fetchSummary();
    
    // Setup Intervals
    setInterval(fetchStats, REFRESH_RATE_STATS);
    setInterval(fetchLogs, REFRESH_RATE_LOGS);
    setInterval(fetchSummary, REFRESH_RATE_CHART);
    
    // Event Listeners
    btnReset.addEventListener('click', handleReset);
});

// Update Status Bar
function updateConnectionStatus(online) {
    if (online) {
        statusIndicator.className = 'status-indicator online';
        statusText.innerText = 'System Connected';
    } else {
        statusIndicator.className = 'status-indicator offline';
        statusText.innerText = 'Server Offline';
    }
}

// Fetch stats (current occupancy, total in, total out)
async function fetchStats() {
    try {
        const response = await fetch(API_OCCUPANCY);
        if (!response.ok) throw new Error('Network error');
        
        const data = await response.json();
        
        // Update DOM
        if (valCurrent) valCurrent.innerText = data.current_occupancy;
        if (valIn) valIn.innerText = data.total_in;
        if (valOut) valOut.innerText = data.total_out;
        
        // Update progress bar width
        // Max capacity helper representation (e.g. 50 capacity cap for visual)
        const capCeiling = 50;
        const progressPercentage = Math.min(100, (data.current_occupancy / capCeiling) * 100);
        progressBar.style.width = `${progressPercentage}%`;
        
        // Style changes if getting near capacity
        const occupancyCard = document.getElementById('card-occupancy');
        if (progressPercentage >= 90) {
            occupancyCard.style.borderTop = '4px solid #EF4444'; // Red if full
        } else if (progressPercentage >= 70) {
            occupancyCard.style.borderTop = '4px solid #F59E0B'; // Orange if warning
        } else {
            occupancyCard.style.borderTop = '4px solid #8B5CF6'; // Standard Violet
        }

        updateConnectionStatus(true);
    } catch (error) {
        console.error('Error fetching occupancy stats:', error);
        updateConnectionStatus(false);
    }
}

// Fetch recent event logs
async function fetchLogs() {
    try {
        const response = await fetch(API_EVENTS);
        if (!response.ok) throw new Error('Network error');
        
        const data = await response.json();
        renderLogs(data);
    } catch (error) {
        console.error('Error fetching event logs:', error);
    }
}

// Render crossing log records into table
function renderLogs(logs) {
    if (!logs || logs.length === 0) {
        logsTbody.innerHTML = `<tr><td colspan="4" class="no-data">No events recorded yet.</td></tr>`;
        return;
    }
    
    logsTbody.innerHTML = logs.map(log => {
        const date = new Date(log.timestamp);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        const badgeClass = log.direction.toLowerCase() === 'in' ? 'badge-direction in' : 'badge-direction out';
        const directionIcon = log.direction.toLowerCase() === 'in' ? '↓ IN' : '↑ OUT';
        const confidencePct = `${Math.round(log.confidence * 100)}%`;
        
        return `
            <tr>
                <td><strong>#${log.track_id}</strong></td>
                <td><span class="${badgeClass}">${directionIcon}</span></td>
                <td>${confidencePct}</td>
                <td>${timeStr}</td>
            </tr>
        `;
    }).join('');
}

// Fetch hourly summary for chart
async function fetchSummary() {
    try {
        const response = await fetch(API_SUMMARY);
        if (!response.ok) throw new Error('Network error');
        
        const data = await response.json();
        updateChartData(data);
    } catch (error) {
        console.error('Error fetching hourly summary:', error);
    }
}

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('occupancy-chart').getContext('2d');
    
    // Create elegant grid gradients
    const gradientOccupancy = ctx.createLinearGradient(0, 0, 0, 300);
    gradientOccupancy.addColorStop(0, 'rgba(139, 92, 246, 0.25)');
    gradientOccupancy.addColorStop(1, 'rgba(139, 92, 246, 0.00)');

    occupancyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], // Hourly labels, e.g. 09:00, 10:00
            datasets: [
                {
                    label: 'People Inside (Occupancy)',
                    data: [],
                    borderColor: '#8B5CF6',
                    backgroundColor: gradientOccupancy,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: '#8B5CF6',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#9CA3AF',
                        font: {
                            family: 'Outfit',
                            size: 12,
                            weight: 500
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#1F2937',
                    titleColor: '#F9FAFB',
                    bodyColor: '#D1D5DB',
                    titleFont: { family: 'Outfit', weight: 600 },
                    bodyFont: { family: 'Outfit' },
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.03)'
                    },
                    ticks: {
                        color: '#9CA3AF',
                        font: { family: 'Outfit' }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.03)'
                    },
                    ticks: {
                        color: '#9CA3AF',
                        font: { family: 'Outfit' },
                        precision: 0
                    },
                    min: 0
                }
            }
        }
    });
}

// Update dataset for Chart
function updateChartData(summary) {
    if (!occupancyChart) return;
    
    // Sort array by hour just in case
    summary.sort((a, b) => a.hour.localeCompare(b.hour));
    
    const labels = summary.map(item => item.hour);
    
    // Calculate running/cumulative occupancy throughout the day
    let current = 0;
    const dataOccupancy = summary.map(item => {
        current += (item.in - item.out);
        return Math.max(0, current);
    });
    
    occupancyChart.data.labels = labels;
    occupancyChart.data.datasets[0].data = dataOccupancy;
    
    occupancyChart.update();
}

// Handle Reset Button Click
async function handleReset() {
    const confirmation = confirm("Are you sure you want to reset all occupancy stats and database logs? This action is permanent.");
    
    if (!confirmation) return;
    
    try {
        const response = await fetch(API_RESET, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Reset failed');
        
        alert("System stats successfully reset.");
        
        // Fetch new state immediately
        fetchStats();
        fetchLogs();
        fetchSummary();
        
    } catch (error) {
        console.error('Error resetting statistics:', error);
        alert(`Reset failed: ${error.message}`);
    }
}
