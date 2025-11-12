// static/js/event_tracking.js
/**
 * Frontend Event Tracking for CoChain.ai
 * Tracks user interactions and sends them to backend
 */

class EventTracker {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
        this.userId = this.getUserId();
        this.initializeTracking();
    }

    /**
     * Get or create session ID from sessionStorage
     */
    getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('cochain_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('cochain_session_id', sessionId);
        }
        return sessionId;
    }

    /**
     * Get user ID from page (set by server in template)
     */
    getUserId() {
        const userIdElement = document.getElementById('user-id-data');
        return userIdElement ? userIdElement.dataset.userId : null;
    }

    /**
     * Initialize all event tracking
     */
    initializeTracking() {
        this.trackPageView();
        this.trackRecommendationInteractions();
        this.trackScrollDepth();
        this.trackTimeOnPage();
        this.trackLinkClicks();
    }

    /**
     * Send event to backend
     */
    async sendEvent(eventType, eventData) {
        try {
            const payload = {
                event_type: eventType,
                user_id: this.userId,
                session_id: this.sessionId,
                timestamp: new Date().toISOString(),
                ...eventData
            };

            // Use sendBeacon for events that should fire even when leaving page
            if (navigator.sendBeacon && (eventType === 'page_exit' || eventType === 'recommendation_click')) {
                const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                navigator.sendBeacon('/api/events/track', blob);
            } else {
                // Use fetch for other events
                await fetch('/api/events/track', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                    keepalive: true
                });
            }

            console.log('📊 Event tracked:', eventType, eventData);
        } catch (error) {
            console.error('Failed to track event:', error);
        }
    }

    /**
     * Track page view
     */
    trackPageView() {
        const pageName = document.body.dataset.page || window.location.pathname;
        const referrer = document.referrer;

        this.sendEvent('page_view', {
            page_name: pageName,
            referrer: referrer,
            url: window.location.href,
            viewport_width: window.innerWidth,
            viewport_height: window.innerHeight
        });
    }

    /**
     * Track recommendation card interactions
     */
    trackRecommendationInteractions() {
        // Track recommendation impressions (visible in viewport)
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.5 // 50% visible
        };

        const impressionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const card = entry.target;
                    const projectId = card.dataset.projectId;
                    const position = card.dataset.position;
                    const similarity = card.dataset.similarity;

                    if (!card.dataset.impressionTracked) {
                        this.sendEvent('recommendation_impression', {
                            project_id: projectId,
                            position: parseInt(position),
                            similarity: parseFloat(similarity)
                        });
                        card.dataset.impressionTracked = 'true';
                    }
                }
            });
        }, observerOptions);

        // Observe all recommendation cards
        document.querySelectorAll('.recommendation-card').forEach(card => {
            observerObserver(card);
        });

        // Track hovers (dwell time)
        document.querySelectorAll('.recommendation-card').forEach(card => {
            let hoverStartTime = null;

            card.addEventListener('mouseenter', () => {
                hoverStartTime = Date.now();
            });

            card.addEventListener('mouseleave', () => {
                if (hoverStartTime) {
                    const hoverDuration = Date.now() - hoverStartTime;
                    if (hoverDuration > 1000) { // Only track if hovered for more than 1 second
                        this.sendEvent('recommendation_hover', {
                            project_id: card.dataset.projectId,
                            position: parseInt(card.dataset.position),
                            hover_duration_ms: hoverDuration
                        });
                    }
                    hoverStartTime = null;
                }
            });
        });

        // Track clicks on recommendation cards
        document.querySelectorAll('.recommendation-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't track if clicking on a button inside the card
                if (e.target.closest('button') || e.target.closest('a.btn')) {
                    return;
                }

                const projectId = card.dataset.projectId;
                const position = card.dataset.position;
                const similarity = card.dataset.similarity;

                this.sendEvent('recommendation_click', {
                    project_id: projectId,
                    position: parseInt(position),
                    similarity: parseFloat(similarity),
                    click_target: e.target.className
                });

                // Also send to backend API for database tracking
                fetch('/api/interactions/click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        github_reference_id: projectId,
                        rank_position: parseInt(position),
                        similarity_score: parseFloat(similarity),
                        session_id: this.sessionId
                    })
                });
            });
        });

        // Track "View More" clicks
        document.querySelectorAll('.view-project-details').forEach(button => {
            button.addEventListener('click', () => {
                const card = button.closest('.recommendation-card');
                this.sendEvent('recommendation_detail_view', {
                    project_id: card.dataset.projectId,
                    position: parseInt(card.dataset.position)
                });
            });
        });
    }

    /**
     * Track scroll depth
     */
    trackScrollDepth() {
        const scrollDepths = [25, 50, 75, 100];
        const trackedDepths = new Set();

        window.addEventListener('scroll', () => {
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollPercentage = (scrollTop / (documentHeight - windowHeight)) * 100;

            scrollDepths.forEach(depth => {
                if (scrollPercentage >= depth && !trackedDepths.has(depth)) {
                    trackedDepths.add(depth);
                    this.sendEvent('scroll_depth', {
                        depth: depth,
                        page: document.body.dataset.page || window.location.pathname
                    });
                }
            });
        });
    }

    /**
     * Track time spent on page
     */
    trackTimeOnPage() {
        const startTime = Date.now();
        let lastActivityTime = startTime;
        let isActive = true;

        // Track user activity
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                lastActivityTime = Date.now();
                isActive = true;
            }, { passive: true });
        });

        // Check for inactivity every 30 seconds
        setInterval(() => {
            const now = Date.now();
            const timeSinceLastActivity = now - lastActivityTime;
            
            // Consider user inactive after 2 minutes of no activity
            if (timeSinceLastActivity > 120000 && isActive) {
                isActive = false;
                this.sendEvent('user_inactive', {
                    time_until_inactive_ms: timeSinceLastActivity,
                    total_time_on_page_ms: now - startTime
                });
            }
        }, 30000);

        // Track on page exit
        window.addEventListener('beforeunload', () => {
            const totalTime = Date.now() - startTime;
            const activeTime = isActive ? totalTime : (lastActivityTime - startTime);

            this.sendEvent('page_exit', {
                total_time_ms: totalTime,
                active_time_ms: activeTime,
                page: document.body.dataset.page || window.location.pathname
            });
        });
    }

    /**
     * Track external link clicks
     */
    trackLinkClicks() {
        document.querySelectorAll('a[href^="http"]').forEach(link => {
            link.addEventListener('click', () => {
                this.sendEvent('external_link_click', {
                    url: link.href,
                    text: link.textContent.trim(),
                    page: document.body.dataset.page || window.location.pathname
                });
            });
        });

        // Track GitHub repository link clicks
        document.querySelectorAll('.github-repo-link').forEach(link => {
            link.addEventListener('click', () => {
                const card = link.closest('.recommendation-card');
                this.sendEvent('github_repo_click', {
                    project_id: card ? card.dataset.projectId : null,
                    repo_url: link.href
                });
            });
        });
    }

    /**
     * Track bookmark actions (called from bookmark button handler)
     */
    trackBookmarkAction(projectId, action, notes = null) {
        this.sendEvent('bookmark_action', {
            project_id: projectId,
            action: action, // 'add' or 'remove'
            notes: notes
        });
    }

    /**
     * Track feedback submission
     */
    trackFeedback(projectId, rating, feedbackText = null) {
        this.sendEvent('feedback_submit', {
            project_id: projectId,
            rating: rating,
            feedback_text: feedbackText
        });
    }

    /**
     * Track search/filter actions
     */
    trackSearch(searchQuery, filters = {}) {
        this.sendEvent('search', {
            query: searchQuery,
            filters: filters,
            results_count: document.querySelectorAll('.recommendation-card').length
        });
    }

    /**
     * Track button clicks with custom data
     */
    trackButtonClick(buttonName, additionalData = {}) {
        this.sendEvent('button_click', {
            button_name: buttonName,
            ...additionalData
        });
    }
}

// Initialize event tracker when DOM is ready
let eventTracker;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        eventTracker = new EventTracker();
        window.eventTracker = eventTracker; // Make globally accessible
    });
} else {
    eventTracker = new EventTracker();
    window.eventTracker = eventTracker;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EventTracker;
}