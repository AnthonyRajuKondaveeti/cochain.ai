/**
 * Service Worker for Push Notifications
 * Handles background push messages and notification display
 */

const CACHE_NAME = 'cochain-notifications-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
    '/static/js/main.js',
    '/static/images/favicon.webp'
];

// Install service worker
self.addEventListener('install', (event) => {
    console.log('Service Worker installing');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
            .then(() => self.skipWaiting())
    );
});

// Activate service worker
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Handle push messages
self.addEventListener('push', (event) => {
    console.log('Push message received');
    
    let notificationData = {
        title: 'CoChain.ai',
        body: 'You have a new notification',
        icon: '/static/images/notification-icon.png',
        badge: '/static/images/badge-icon.png',
        tag: 'cochain-notification',
        data: {
            url: '/notifications',
            notificationId: Date.now()
        }
    };

    if (event.data) {
        try {
            const payload = event.data.json();
            notificationData = {
                ...notificationData,
                ...payload
            };
        } catch (error) {
            console.error('Error parsing push payload:', error);
            notificationData.body = event.data.text() || notificationData.body;
        }
    }

    // Customize notification based on type
    if (notificationData.type) {
        switch (notificationData.type) {
            case 'join_request':
                notificationData.icon = '/static/images/collaboration-icon.png';
                notificationData.actions = [
                    { action: 'view', title: 'View Request', icon: '/static/images/view-icon.png' },
                    { action: 'dismiss', title: 'Dismiss', icon: '/static/images/dismiss-icon.png' }
                ];
                break;
            case 'request_accepted':
                notificationData.icon = '/static/images/success-icon.png';
                notificationData.requireInteraction = true;
                notificationData.actions = [
                    { action: 'view', title: 'View Project', icon: '/static/images/project-icon.png' }
                ];
                break;
            case 'request_rejected':
                notificationData.icon = '/static/images/info-icon.png';
                notificationData.actions = [
                    { action: 'view', title: 'Browse Projects', icon: '/static/images/browse-icon.png' }
                ];
                break;
            case 'project_update':
                notificationData.icon = '/static/images/project-icon.png';
                notificationData.actions = [
                    { action: 'view', title: 'View Project', icon: '/static/images/view-icon.png' }
                ];
                break;
            case 'new_recommendation':
                notificationData.icon = '/static/images/recommendation-icon.png';
                notificationData.actions = [
                    { action: 'view', title: 'View Dashboard', icon: '/static/images/dashboard-icon.png' }
                ];
                break;
        }
    }

    const notificationPromise = self.registration.showNotification(
        notificationData.title,
        {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            data: notificationData.data,
            actions: notificationData.actions || [],
            requireInteraction: notificationData.requireInteraction || false,
            silent: notificationData.silent || false,
            vibrate: notificationData.vibrate || [200, 100, 200]
        }
    );

    event.waitUntil(notificationPromise);
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    
    event.notification.close();

    const notificationData = event.notification.data || {};
    const action = event.action;

    // Send message to client about notification click
    const messagePromise = self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
            client.postMessage({
                type: 'NOTIFICATION_CLICKED',
                data: {
                    ...notificationData,
                    action: action
                }
            });
        });
    });

    let navigationPromise = Promise.resolve();

    if (action === 'dismiss') {
        // Just close the notification
        return;
    }

    // Default action or specific actions
    let urlToOpen = notificationData.url || '/notifications';
    
    // Handle specific actions
    switch (action) {
        case 'view':
            // Use the URL from notification data
            break;
        default:
            // Default click - use notification URL
            break;
    }
    
    navigationPromise = self.clients.matchAll({
        type: 'window',
        includeUncontrolled: true
    }).then((clients) => {
        // Check if there's already a window/tab open with the target URL
        for (let client of clients) {
            if (client.url.includes(urlToOpen.split('?')[0]) && 'focus' in client) {
                return client.focus();
            }
        }
        
        // If not found, open new window/tab
        if (self.clients.openWindow) {
            return self.clients.openWindow(urlToOpen);
        }
    });

    event.waitUntil(
        Promise.all([messagePromise, navigationPromise])
    );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
    console.log('Notification closed:', event);
    
    const notificationData = event.notification.data || {};
    
    // Send message to client about notification close
    event.waitUntil(
        self.clients.matchAll().then((clients) => {
            clients.forEach((client) => {
                client.postMessage({
                    type: 'NOTIFICATION_CLOSED',
                    data: notificationData
                });
            });
        })
    );
});

// Handle background sync
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync-notifications') {
        event.waitUntil(
            fetch('/api/notifications/sync')
                .then((response) => response.json())
                .then((data) => {
                    if (data.notifications) {
                        data.notifications.forEach((notification) => {
                            self.registration.showNotification(
                                notification.title,
                                {
                                    body: notification.body,
                                    icon: notification.icon || '/static/images/notification-icon.png',
                                    data: notification.data
                                }
                            );
                        });
                    }
                })
                .catch((error) => {
                    console.error('Background sync failed:', error);
                })
        );
    }
});