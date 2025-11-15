"""
Python module for sending web push notifications to the frontend.
This module provides a simple interface for Python code to send notifications
that will be displayed in the browser using the notification-utils.js system.

Usage:
    from NotificationSender import send_notification
    
    # Send a simple notification
    send_notification("Hello", "This is a test notification")
    
    # Send a notification with custom options
    send_notification(
        title="Task Complete",
        body="Your task has been completed successfully",
        tag="task-completion",
        data={"taskId": "12345"}
    )
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

# Global WebSocket connections manager
_websocket_connections = set()


def register_websocket(websocket):
    """Register a WebSocket connection to receive notifications."""
    _websocket_connections.add(websocket)
    print(f"WebSocket registered. Total connections: {len(_websocket_connections)}")


def unregister_websocket(websocket):
    """Unregister a WebSocket connection."""
    _websocket_connections.discard(websocket)
    print(f"WebSocket unregistered. Total connections: {len(_websocket_connections)}")


async def _send_notification_async(
    title: str,
    body: str = "",
    tag: Optional[str] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    require_interaction: bool = False,
    data: Optional[Dict[str, Any]] = None,
    vibrate: Optional[List[int]] = None,
    actions: Optional[List[Dict[str, str]]] = None
):
    """
    Internal async function to send notification to all connected clients.
    
    Args:
        title: Notification title (required)
        body: Notification body text
        tag: Notification tag for grouping
        icon: URL to notification icon
        badge: URL to notification badge
        require_interaction: Whether notification requires user interaction
        data: Custom data object to attach to notification
        vibrate: Vibration pattern array
        actions: Array of action buttons
    """
    if not title:
        raise ValueError("Notification title is required")
    
    # Prepare notification payload
    notification_data = {
        "type": "NOTIFICATION",
        "title": title,
        "body": body or "You have a new notification",
        "tag": tag or f"notification-{datetime.now().timestamp()}",
        "timestamp": datetime.now().isoformat()
    }
    
    # Add optional fields
    if icon:
        notification_data["icon"] = icon
    if badge:
        notification_data["badge"] = badge
    if require_interaction:
        notification_data["requireInteraction"] = require_interaction
    if data:
        notification_data["data"] = data
    if vibrate:
        notification_data["vibrate"] = vibrate
    if actions:
        notification_data["actions"] = actions
    
    # Send to all connected WebSocket clients
    if not _websocket_connections:
        print("Warning: No WebSocket connections available. Notification not sent.")
        return False
    
    message = json.dumps(notification_data)
    disconnected = set()
    
    for websocket in _websocket_connections:
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending notification to WebSocket: {e}")
            disconnected.add(websocket)
    
    # Clean up disconnected websockets
    for ws in disconnected:
        unregister_websocket(ws)
    
    return len(_websocket_connections) > 0


def send_notification(
    title: str,
    body: str = "",
    tag: Optional[str] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    require_interaction: bool = False,
    data: Optional[Dict[str, Any]] = None,
    vibrate: Optional[List[int]] = None,
    actions: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    Send a web push notification to all connected frontend clients.
    
    This is a synchronous wrapper around the async function. It will work
    if called from an async context or will create a new event loop if needed.
    
    Args:
        title: Notification title (required)
        body: Notification body text
        tag: Notification tag for grouping (default: auto-generated)
        icon: URL to notification icon
        badge: URL to notification badge
        require_interaction: Whether notification requires user interaction
        data: Custom data dictionary to attach to notification
        vibrate: Vibration pattern array (e.g., [200, 100, 200])
        actions: Array of action button dictionaries with 'action' and 'title' keys
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
        
    Example:
        # Simple notification
        send_notification("Hello", "World")
        
        # Notification with custom data
        send_notification(
            title="Task Complete",
            body="Your task has been completed",
            tag="task-123",
            data={"taskId": "123", "status": "complete"}
        )
        
        # Notification with actions
        send_notification(
            title="New Message",
            body="You have a new message",
            actions=[
                {"action": "view", "title": "View"},
                {"action": "dismiss", "title": "Dismiss"}
            ]
        )
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, schedule the coroutine
            asyncio.create_task(_send_notification_async(
                title, body, tag, icon, badge, require_interaction, data, vibrate, actions
            ))
            return True
        else:
            # If loop exists but not running, run the coroutine
            return loop.run_until_complete(_send_notification_async(
                title, body, tag, icon, badge, require_interaction, data, vibrate, actions
            ))
    except RuntimeError:
        # No event loop exists, create a new one
        try:
            return asyncio.run(_send_notification_async(
                title, body, tag, icon, badge, require_interaction, data, vibrate, actions
            ))
        except RuntimeError as e:
            print(f"Error sending notification: {e}")
            print("Note: If you're calling this from a synchronous context, "
                  "consider using send_notification_async() instead")
            return False


async def send_notification_async(
    title: str,
    body: str = "",
    tag: Optional[str] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    require_interaction: bool = False,
    data: Optional[Dict[str, Any]] = None,
    vibrate: Optional[List[int]] = None,
    actions: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    Async version of send_notification. Use this when calling from async functions.
    
    Args:
        title: Notification title (required)
        body: Notification body text
        tag: Notification tag for grouping
        icon: URL to notification icon
        badge: URL to notification badge
        require_interaction: Whether notification requires user interaction
        data: Custom data dictionary to attach to notification
        vibrate: Vibration pattern array
        actions: Array of action button dictionaries
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    return await _send_notification_async(
        title, body, tag, icon, badge, require_interaction, data, vibrate, actions
    )


def get_connection_count() -> int:
    """Get the number of currently connected WebSocket clients."""
    return len(_websocket_connections)


def has_connections() -> bool:
    """Check if there are any connected WebSocket clients."""
    return len(_websocket_connections) > 0

