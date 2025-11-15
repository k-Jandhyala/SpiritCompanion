import os
import sys
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add the backend directory to the path so we can import it
backend_path = os.path.join(os.path.dirname(__file__), '..', '.backend')
sys.path.insert(0, backend_path)
# Import backend module explicitly to avoid conflicts
import importlib.util
backend_spec = importlib.util.spec_from_file_location("backend_main", os.path.join(backend_path, "main.py"))
backend_main = importlib.util.module_from_spec(backend_spec)
backend_spec.loader.exec_module(backend_main)
get_gemini_response = backend_main.get_gemini_response

# Import NotificationSender for WebSocket management
notification_sender_spec = importlib.util.spec_from_file_location(
    "notification_sender", 
    os.path.join(backend_path, "NotificationSender.py")
)
notification_sender = importlib.util.module_from_spec(notification_sender_spec)
notification_sender_spec.loader.exec_module(notification_sender)

app = FastAPI(title="Gemini Test API")

# Set the event loop for NotificationSender to use from threads
@app.on_event("startup")
async def startup_event():
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        notification_sender.set_event_loop(loop)
        print("Event loop set for NotificationSender")
    except Exception as e:
        print(f"Error setting event loop: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class QueryRequest(BaseModel):
    query: str

# Response model
class QueryResponse(BaseModel):
    response: str
    status: str

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="No query provided")
        
        # Call the backend function to get Gemini response
        gemini_output = get_gemini_response(request.query)
        
        # Parse the settings from the backend and set them in this server's module instance
        # The backend's get_gemini_response already parsed and set them, but we need to
        # set them in our module instance too (they're separate module instances)
        _parse_focus_settings = backend_main._parse_focus_settings
        focus_settings = _parse_focus_settings(gemini_output)
        
        # Set the timer in the FastAPI server's module instance
        focus_reminders.setFocusRestRepeatTimes(
            focus_settings["focus_time"],
            focus_settings["break_duration"],  # RestTime
            focus_settings["break_frequency"]    # RepeatTime
        )
        
        print(f"Timer configured: Focus={focus_settings['focus_time']}s, "
              f"Rest={focus_settings['break_duration']}s, "
              f"Repeat={focus_settings['break_frequency']}s")
        
        return QueryResponse(
            response=gemini_output,
            status="success"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for notifications
@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for receiving notifications from the backend.
    The frontend connects to this endpoint to receive real-time notifications.
    """
    client_host = websocket.client.host if hasattr(websocket, 'client') else 'unknown'
    print(f"WebSocket connection attempt from {client_host}")
    
    await websocket.accept()
    notification_sender.register_websocket(websocket)
    print(f"✅ WebSocket client connected and registered. Total connections: {notification_sender.get_connection_count()}")
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong for keepalive)
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle ping messages
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
                    print("Received ping, sent pong")
            except json.JSONDecodeError:
                # If not JSON, just ignore (could be plain text)
                pass
    except WebSocketDisconnect:
        notification_sender.unregister_websocket(websocket)
        print(f"❌ WebSocket client disconnected. Remaining connections: {notification_sender.get_connection_count()}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        notification_sender.unregister_websocket(websocket)

# Endpoint to check notification connection status
@app.get("/api/notifications/status")
async def get_notification_status():
    """Get the status of notification connections."""
    return {
        "connected": notification_sender.has_connections(),
        "connection_count": notification_sender.get_connection_count()
    }

# Import FocusRestReminders for timer control
focus_reminders_spec = importlib.util.spec_from_file_location(
    "focus_reminders",
    os.path.join(backend_path, "FocusRestReminders.py")
)
focus_reminders = importlib.util.module_from_spec(focus_reminders_spec)
focus_reminders_spec.loader.exec_module(focus_reminders)

@app.post("/api/timer/start")
async def start_timer():
    """Start the focus/rest timer."""
    try:
        # Check if times are set
        if focus_reminders.FocusTime == 0 or focus_reminders.RestTime == 0 or focus_reminders.RepeatTime == 0:
            raise HTTPException(
                status_code=400, 
                detail="Timer not configured. Please set focus, rest, and repeat times first."
            )
        
        # Start timer in background (non-blocking)
        import threading
        
        # Run timer in a separate thread to avoid blocking
        def run_timer():
            try:
                focus_reminders.startFocusRestTimer()
            except Exception as e:
                print(f"Error in timer thread: {e}")
        
        timer_thread = threading.Thread(target=run_timer, daemon=True)
        timer_thread.start()
        
        return {
            "status": "success",
            "message": "Timer started",
            "settings": {
                "focus_time": focus_reminders.FocusTime,
                "rest_time": focus_reminders.RestTime,
                "repeat_time": focus_reminders.RepeatTime
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/timer/status")
async def get_timer_status():
    """Get the current timer configuration."""
    return {
        "focus_time": focus_reminders.FocusTime,
        "rest_time": focus_reminders.RestTime,
        "repeat_time": focus_reminders.RepeatTime,
        "configured": not (focus_reminders.FocusTime == 0 or focus_reminders.RestTime == 0 or focus_reminders.RepeatTime == 0)
    }

@app.get("/api/timer/state")
async def get_timer_state():
    """Get the current timer state for polling."""
    state = focus_reminders.get_timer_state()
    return state

app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
