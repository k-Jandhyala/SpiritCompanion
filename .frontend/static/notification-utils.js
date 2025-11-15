// Notification Utility Module
// This module can be imported by any file to send web push notifications

class NotificationManager {
    constructor() {
        this.permission = null;
        this.serviceWorkerRegistration = null;
        this.isInitialized = false;
        this.websocket = null;
        this.websocketConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3 seconds
    }

    /**
     * Initialize the notification manager
     * Registers the service worker and requests notification permission
     * @returns {Promise<boolean>} True if initialization successful
     */
    async initialize() {
        if (this.isInitialized) {
            return true;
        }

        if (!('serviceWorker' in navigator)) {
            console.error('Service Workers are not supported in this browser');
            return false;
        }

        if (!('Notification' in window)) {
            console.error('Notifications are not supported in this browser');
            return false;
        }

        try {
            // Register service worker
            this.serviceWorkerRegistration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            });
            console.log('Service Worker registered:', this.serviceWorkerRegistration);

            // Wait for service worker to be ready
            await navigator.serviceWorker.ready;
            console.log('Service Worker ready');

            // Check current permission status
            this.permission = Notification.permission;

            // Connect to WebSocket for backend notifications
            this.connectWebSocket();

            this.isInitialized = true;
            return true;
        } catch (error) {
            console.error('Error initializing notification manager:', error);
            return false;
        }
    }

    /**
     * Connect to WebSocket for receiving notifications from backend
     */
    connectWebSocket() {
        // Determine WebSocket URL based on current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/notifications`;

        try {
            console.log('🔌 Attempting to connect WebSocket to:', wsUrl);
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected for notifications');
                this.websocketConnected = true;
                this.reconnectAttempts = 0;
                
                // Send a ping to keep connection alive
                this.startWebSocketPing();
                
                // Send initial ping to verify connection
                try {
                    this.websocket.send(JSON.stringify({ type: 'ping' }));
                } catch (e) {
                    console.error('Error sending initial ping:', e);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                console.error('WebSocket URL was:', wsUrl);
                console.error('WebSocket readyState:', this.websocket?.readyState);
                this.websocketConnected = false;
            };

            this.websocket.onclose = (event) => {
                console.log('❌ WebSocket disconnected', {
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean
                });
                this.websocketConnected = false;
                this.stopWebSocketPing();
                
                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                    setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
                } else {
                    console.error('❌ Max reconnection attempts reached');
                }
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Handle pong responses
                    if (data.type === 'pong') {
                        console.log('📨 Received pong from server');
                        return;
                    }
                    
                    // Handle notification messages from backend
                    if (data.type === 'NOTIFICATION') {
                        console.log('📬 Received notification from backend:', data);
                        this.handleBackendNotification(data);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
        }
    }

    /**
     * Handle notification received from backend via WebSocket
     * @param {Object} data - Notification data from backend
     */
    async handleBackendNotification(data) {
        try {
            // Ensure permission is granted
            if (this.permission !== 'granted') {
                const permission = await this.requestPermission();
                if (permission !== 'granted') {
                    console.log('Notification permission not granted, skipping notification');
                    return;
                }
            }

            // Send notification using the service worker
            await this.sendNotification(data.title, {
                body: data.body,
                tag: data.tag,
                icon: data.icon,
                badge: data.badge,
                requireInteraction: data.requireInteraction || false,
                data: data.data || {},
                vibrate: data.vibrate || [200, 100, 200],
                actions: data.actions || []
            });
        } catch (error) {
            console.error('Error handling backend notification:', error);
        }
    }

    /**
     * Start sending ping messages to keep WebSocket alive
     */
    startWebSocketPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
        }
        
        this.pingInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Send ping every 30 seconds
    }

    /**
     * Stop sending ping messages
     */
    stopWebSocketPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    /**
     * Check if WebSocket is connected
     * @returns {boolean}
     */
    isWebSocketConnected() {
        return this.websocketConnected && 
               this.websocket && 
               this.websocket.readyState === WebSocket.OPEN;
    }

    /**
     * Request notification permission from the user
     * @returns {Promise<string>} 'granted', 'denied', or 'default'
     */
    async requestPermission() {
        if (!('Notification' in window)) {
            throw new Error('Notifications are not supported in this browser');
        }

        if (Notification.permission === 'granted') {
            this.permission = 'granted';
            return 'granted';
        }

        if (Notification.permission === 'denied') {
            this.permission = 'denied';
            return 'denied';
        }

        // Request permission
        const permission = await Notification.requestPermission();
        this.permission = permission;
        return permission;
    }

    /**
     * Send a notification using the service worker
     * @param {string} title - Notification title
     * @param {Object} options - Notification options
     * @param {string} options.body - Notification body text
     * @param {string} options.icon - URL to notification icon
     * @param {string} options.badge - URL to notification badge
     * @param {string} options.tag - Notification tag (for grouping)
     * @param {boolean} options.requireInteraction - Require user interaction to dismiss
     * @param {Object} options.data - Custom data to attach to notification
     * @param {Array} options.actions - Array of action buttons
     * @param {Array} options.vibrate - Vibration pattern
     * @returns {Promise<void>}
     */
    async sendNotification(title, options = {}) {
        // Ensure initialized
        if (!this.isInitialized) {
            const initialized = await this.initialize();
            if (!initialized) {
                throw new Error('Failed to initialize notification manager');
            }
        }

        // Check permission
        if (this.permission !== 'granted') {
            const permission = await this.requestPermission();
            if (permission !== 'granted') {
                throw new Error('Notification permission not granted');
            }
        }

        // Ensure service worker is ready
        if (!this.serviceWorkerRegistration) {
            this.serviceWorkerRegistration = await navigator.serviceWorker.ready;
        }

        // Send message to service worker to show notification
        if (this.serviceWorkerRegistration.active) {
            this.serviceWorkerRegistration.active.postMessage({
                type: 'SHOW_NOTIFICATION',
                title: title,
                options: {
                    body: options.body || 'You have a new notification',
                    icon: options.icon,
                    badge: options.badge,
                    tag: options.tag || 'default',
                    requireInteraction: options.requireInteraction || false,
                    data: options.data || {},
                    vibrate: options.vibrate || [200, 100, 200],
                    actions: options.actions || []
                }
            });
        } else {
            // Fallback: use Notification API directly if service worker not active
            new Notification(title, {
                body: options.body || 'You have a new notification',
                icon: options.icon,
                badge: options.badge,
                tag: options.tag || 'default',
                requireInteraction: options.requireInteraction || false,
                data: options.data || {},
                vibrate: options.vibrate || [200, 100, 200],
                actions: options.actions || []
            });
        }
    }

    /**
     * Check if notifications are supported and permission is granted
     * @returns {boolean}
     */
    isSupported() {
        return 'Notification' in window && 'serviceWorker' in navigator;
    }

    /**
     * Get current permission status
     * @returns {string} 'granted', 'denied', or 'default'
     */
    getPermission() {
        if (!('Notification' in window)) {
            return null;
        }
        return Notification.permission;
    }
}

// Create a singleton instance
const notificationManager = new NotificationManager();

// Auto-initialize when the module is loaded
if (typeof window !== 'undefined') {
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            notificationManager.initialize().catch(console.error);
        });
    } else {
        notificationManager.initialize().catch(console.error);
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = notificationManager;
}

// Make available globally
if (typeof window !== 'undefined') {
    window.NotificationManager = notificationManager;
    window.sendNotification = (title, options) => notificationManager.sendNotification(title, options);
}

