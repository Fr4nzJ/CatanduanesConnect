// Dashboard utilities for real-time updates
class DashboardUpdater {
    constructor(options) {
        this.updateInterval = options.updateInterval || 30000;
        this.endpoints = options.endpoints || {};
        this.updateCallbacks = options.updateCallbacks || {};
        this.loadingElements = options.loadingElements || {};
        this.activeTimers = new Set();
    }

    startUpdates() {
        // Clear any existing timers
        this.stopUpdates();

        // Start new update loops for each endpoint
        Object.keys(this.endpoints).forEach(key => {
            this.updateData(key);
            const timerId = setInterval(() => this.updateData(key), this.updateInterval);
            this.activeTimers.add(timerId);
        });
    }

    stopUpdates() {
        // Clear all active timers
        this.activeTimers.forEach(timerId => clearInterval(timerId));
        this.activeTimers.clear();
    }

    showLoading(key) {
        const loadingEl = this.loadingElements[key];
        if (loadingEl) {
            loadingEl.classList.remove('d-none');
        }
    }

    hideLoading(key) {
        const loadingEl = this.loadingElements[key];
        if (loadingEl) {
            loadingEl.classList.add('d-none');
        }
    }

    async updateData(key) {
        try {
            this.showLoading(key);
            const response = await fetch(this.endpoints[key]);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Call the appropriate update callback
            if (this.updateCallbacks[key]) {
                this.updateCallbacks[key](data);
            }
        } catch (error) {
            console.error(`Error updating ${key}:`, error);
        } finally {
            this.hideLoading(key);
        }
    }
}

// Utility function to create a loading spinner
function createLoadingSpinner(containerId, size = 'sm') {
    const container = document.getElementById(containerId);
    if (container) {
        const spinner = document.createElement('div');
        spinner.className = `spinner-border spinner-border-${size} text-primary d-none`;
        spinner.setAttribute('role', 'status');
        spinner.innerHTML = '<span class="visually-hidden">Loading...</span>';
        container.appendChild(spinner);
        return spinner;
    }
    return null;
}