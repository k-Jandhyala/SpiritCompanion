// Service Worker for Web Push Notifications
// This service worker handles push notifications and can be called from any file

const CACHE_NAME = 'spirit-companion-v1';

// Install event - cache resources
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim(); // Take control of all pages immediately
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('Push notification received:', event);
    
    let notificationData = {
        title: 'Spirit Companion',
        body: 'You have a new notification',
        icon: '/icon-192x192.png', // You can add an icon later
        badge: '/badge-72x72.png', // You can add a badge later
        tag: 'default',
        requireInteraction: false,
        data: {}
    };

    // If the push event has data, use it
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = {
                ...notificationData,
                ...data,
                data: data.data || {}
            };
        } catch (e) {
            // If not JSON, treat as text
            notificationData.body = event.data.text();
        }
    }

    const promiseChain = self.registration.showNotification(
        notificationData.title,
        {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            requireInteraction: notificationData.requireInteraction,
            data: notificationData.data,
            vibrate: [200, 100, 200],
            actions: notificationData.actions || []
        }
    );

    event.waitUntil(promiseChain);
});

// Notification click event - handle when user clicks on notification
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    
    event.notification.close();

    const notificationData = event.notification.data || {};
    const urlToOpen = notificationData.url || '/';

    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // Check if there's already a window/tab open with the target URL
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            // If not, open a new window/tab
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Message event - handle messages from the main thread
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    if (event.data && event.data.type === 'SHOW_NOTIFICATION') {
        const { title, options } = event.data;
        
        event.waitUntil(
            self.registration.showNotification(title, {
                body: options.body || 'You have a new notification',
                icon: options.icon || '/icon-192x192.png',
                badge: options.badge || '/badge-72x72.png',
                tag: options.tag || 'default',
                requireInteraction: options.requireInteraction || false,
                data: options.data || {},
                vibrate: options.vibrate || [200, 100, 200],
                actions: options.actions || []
            })
        );
    }
});

