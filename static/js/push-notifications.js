/**
 * CoChain.ai Push Notifications Service
 * Handles browser push notifications using existing notification system
 */

class PushNotificationService {
    constructor() {
        this.registration = null;
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.isSubscribed = false;
        this.applicationServerKey = this.urlB64ToUint8Array('BNQ-Yj4vRbGUJN8Yv3oT2qJvF8I7mXaC_aL5dN9ZvQ7pFkL3tY6sH2aE1nR8bC4vQ'); // Replace with actual VAPID key
        
        this.init();
    }

    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications not supported');
            this.updateUI();
            return;
        }

        try {
            // Register service worker
            this.registration = await navigator.serviceWorker.register('/static/js/sw.js');
            console.log('Service Worker registered');

            // Check if already subscribed
            const subscription = await this.registration.pushManager.getSubscription();
            this.isSubscribed = !(subscription === null);

            // Update UI based on subscription status
            this.updateUI();

            // Listen for messages from service worker
            navigator.serviceWorker.addEventListener('message', this.handleServiceWorkerMessage.bind(this));

        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }

    urlB64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    async subscribeUser() {
        if (!this.registration) {
            console.error('Service Worker not registered');
            return false;
        }

        try {
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.applicationServerKey
            });

            console.log('User subscribed to push notifications');
            this.isSubscribed = true;

            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
            
            this.updateUI();
            this.showSuccessMessage('Push notifications enabled! You\'ll receive updates about your projects.');
            
            return true;
        } catch (error) {
            console.error('Failed to subscribe user:', error);
            this.showErrorMessage('Failed to enable push notifications. Please try again.');
            return false;
        }
    }

    async unsubscribeUser() {
        const subscription = await this.registration.pushManager.getSubscription();
        
        if (subscription) {
            try {
                await subscription.unsubscribe();
                await this.removeSubscriptionFromServer(subscription);
                
                this.isSubscribed = false;
                this.updateUI();
                this.showSuccessMessage('Push notifications disabled.');
                
                return true;
            } catch (error) {
                console.error('Failed to unsubscribe user:', error);
                return false;
            }
        }
    }

    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/notifications/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    subscription: subscription,
                    user_agent: navigator.userAgent,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send subscription to server');
            }

            const result = await response.json();
            console.log('Subscription sent to server:', result);
        } catch (error) {
            console.error('Error sending subscription to server:', error);
            throw error;
        }
    }

    async removeSubscriptionFromServer(subscription) {
        try {
            await fetch('/api/notifications/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    subscription: subscription
                })
            });
        } catch (error) {
            console.error('Error removing subscription from server:', error);
        }
    }

    updateUI() {
        const subscribeBtn = document.getElementById('subscribe-notifications-btn');
        const unsubscribeBtn = document.getElementById('unsubscribe-notifications-btn');
        const notificationStatus = document.getElementById('notification-status');

        if (!subscribeBtn) return; // Not on a page with notification controls

        if (!this.isSupported) {
            if (subscribeBtn) subscribeBtn.style.display = 'none';
            if (unsubscribeBtn) unsubscribeBtn.style.display = 'none';
            if (notificationStatus) {
                notificationStatus.innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i> Not supported';
            }
            return;
        }

        if (this.isSubscribed) {
            if (subscribeBtn) subscribeBtn.style.display = 'none';
            if (unsubscribeBtn) unsubscribeBtn.style.display = 'inline-block';
            if (notificationStatus) {
                notificationStatus.innerHTML = '<i class="fas fa-bell text-success"></i> Push notifications enabled';
            }
        } else {
            if (subscribeBtn) subscribeBtn.style.display = 'inline-block';
            if (unsubscribeBtn) unsubscribeBtn.style.display = 'none';
            if (notificationStatus) {
                notificationStatus.innerHTML = '<i class="fas fa-bell-slash text-muted"></i> Push notifications disabled';
            }
        }
    }

    handleServiceWorkerMessage(event) {
        const { type, data } = event.data;
        
        switch (type) {
            case 'NOTIFICATION_CLICKED':
                this.handleNotificationClick(data);
                break;
            case 'NOTIFICATION_CLOSED':
                this.handleNotificationClosed(data);
                break;
        }
    }

    handleNotificationClick(data) {
        // Track notification click
        fetch('/api/notifications/track-click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                notification_id: data.notificationId,
                action: 'click'
            })
        });

        // Navigate to relevant page based on notification type
        if (data.url) {
            window.location.href = data.url;
        }
    }

    handleNotificationClosed(data) {
        // Track notification dismissal
        fetch('/api/notifications/track-click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                notification_id: data.notificationId,
                action: 'dismiss'
            })
        });
    }

    showSuccessMessage(message) {
        this.showToast(message, 'success');
    }

    showErrorMessage(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    // Request permission and show notification prompt
    async requestPermission() {
        if (!this.isSupported) {
            this.showErrorMessage('Push notifications are not supported in your browser.');
            return false;
        }

        if (Notification.permission === 'granted') {
            return await this.subscribeUser();
        } else if (Notification.permission === 'denied') {
            this.showErrorMessage('Push notifications are blocked. Please enable them in your browser settings.');
            return false;
        } else {
            // Request permission
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                return await this.subscribeUser();
            } else {
                this.showErrorMessage('Push notifications permission denied.');
                return false;
            }
        }
    }

    // Check for unread notifications and show browser notification
    async checkForNewNotifications() {
        try {
            const response = await fetch('/api/notifications/unread-count');
            const data = await response.json();
            
            if (data.success && data.count > 0) {
                this.showBrowserNotification(
                    'CoChain.ai',
                    `You have ${data.count} new notification${data.count > 1 ? 's' : ''}`,
                    '/notifications'
                );
            }
        } catch (error) {
            console.error('Error checking for notifications:', error);
        }
    }

    showBrowserNotification(title, body, url, icon) {
        if (this.isSubscribed && Notification.permission === 'granted') {
            const notification = new Notification(title, {
                body: body,
                icon: icon || '/static/images/favicon.webp',
                badge: '/static/images/badge-icon.png',
                tag: 'cochain-notification',
                requireInteraction: false
            });

            notification.onclick = function() {
                window.focus();
                if (url) {
                    window.location.href = url;
                }
                notification.close();
            };
        }
    }
}

// Initialize push notification service
const pushNotificationService = new PushNotificationService();

// Export for global use
window.pushNotificationService = pushNotificationService;

// Auto-check for notifications every 5 minutes for active users
setInterval(() => {
    if (document.visibilityState === 'visible') {
        pushNotificationService.checkForNewNotifications();
    }
}, 5 * 60 * 1000);