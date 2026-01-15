/**
 * GaragePi - Frontend Application
 * 
 * Handles the web UI for controlling the garage door.
 */

(function() {
    'use strict';

    // DOM Elements
    const triggerBtn = document.getElementById('trigger-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = statusIndicator.querySelector('.status-text');
    const feedback = document.getElementById('feedback');
    const feedbackIcon = feedback.querySelector('.feedback-icon');
    const feedbackText = feedback.querySelector('.feedback-text');
    const simulationBadge = document.getElementById('simulation-badge');
    const gpioInfo = document.getElementById('gpio-info');

    // Configuration
    const API_BASE = '';  // Same origin
    const FEEDBACK_DISPLAY_TIME = 3000;  // ms

    let feedbackTimeout = null;

    /**
     * Initialize the application
     */
    async function init() {
        // Check connection status
        await checkStatus();

        // Set up event listeners
        triggerBtn.addEventListener('click', handleTrigger);

        // Periodically check status
        setInterval(checkStatus, 30000);  // Every 30 seconds
    }

    /**
     * Check the API status and update UI
     */
    async function checkStatus() {
        try {
            const response = await fetch(`${API_BASE}/api/garage/status`);
            
            if (response.ok) {
                const data = await response.json();
                setConnected(true);
                
                // Update simulation badge
                if (data.simulation_mode) {
                    simulationBadge.classList.remove('hidden');
                } else {
                    simulationBadge.classList.add('hidden');
                }
                
                // Update GPIO info
                gpioInfo.textContent = `GPIO${data.gpio_pin}`;
                
                // Enable button
                triggerBtn.disabled = false;
            } else {
                setConnected(false);
            }
        } catch (error) {
            console.error('Status check failed:', error);
            setConnected(false);
        }
    }

    /**
     * Update connection status indicator
     */
    function setConnected(connected) {
        if (connected) {
            statusIndicator.className = 'status-indicator connected';
            statusText.textContent = 'Connected';
            triggerBtn.disabled = false;
        } else {
            statusIndicator.className = 'status-indicator error';
            statusText.textContent = 'Disconnected';
            triggerBtn.disabled = true;
        }
    }

    /**
     * Handle trigger button click
     */
    async function handleTrigger() {
        if (triggerBtn.disabled || triggerBtn.classList.contains('loading')) {
            return;
        }

        // Set loading state
        triggerBtn.classList.add('loading');
        hideFeedback();

        try {
            const response = await fetch(`${API_BASE}/api/garage/trigger`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                showFeedback('success', '✓', data.message || 'Garage door triggered!');
            } else if (response.status === 429) {
                // Rate limited
                const data = await response.json();
                showFeedback('error', '⏱', data.detail || 'Please wait before trying again');
            } else if (response.status === 401) {
                showFeedback('error', '🔒', 'Authentication required');
            } else {
                const data = await response.json().catch(() => ({}));
                showFeedback('error', '✗', data.detail || 'Failed to trigger garage door');
            }
        } catch (error) {
            console.error('Trigger failed:', error);
            showFeedback('error', '✗', 'Connection error. Please try again.');
            setConnected(false);
        } finally {
            triggerBtn.classList.remove('loading');
        }
    }

    /**
     * Show feedback message
     */
    function showFeedback(type, icon, message) {
        // Clear any existing timeout
        if (feedbackTimeout) {
            clearTimeout(feedbackTimeout);
        }

        // Update feedback element
        feedback.className = `feedback ${type}`;
        feedbackIcon.textContent = icon;
        feedbackText.textContent = message;

        // Auto-hide after delay
        feedbackTimeout = setTimeout(hideFeedback, FEEDBACK_DISPLAY_TIME);
    }

    /**
     * Hide feedback message
     */
    function hideFeedback() {
        feedback.classList.add('hidden');
    }

    // Prevent double-tap zoom on button
    triggerBtn.addEventListener('touchend', function(e) {
        e.preventDefault();
        this.click();
    });

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
