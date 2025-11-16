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

# Import EmotionDetection after adding backend to path
from EmotionDetection import start_emotion_detection, stop_emotion_detection, set_video_websocket
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

# Store the event loop for use in threads
_main_event_loop = None

# Set the event loop for NotificationSender to use from threads
@app.on_event("startup")
async def startup_event():
    import asyncio
    global _main_event_loop
    try:
        loop = asyncio.get_event_loop()
        _main_event_loop = loop
        notification_sender.set_event_loop(loop)
        
        # Also set event loop for EmotionDetection
        try:
            from EmotionDetection import set_event_loop as set_emotion_loop
            set_emotion_loop(loop)
        except:
            pass
        
        print("Event loop set for NotificationSender and EmotionDetection")
    except Exception as e:
        print(f"Error setting event loop: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop emotion detection and release camera when server shuts down."""
    try:
        print("🛑 Server shutting down, stopping emotion detection...")
        stop_emotion_detection()
        print("✅ Emotion detection stopped on server shutdown")
    except Exception as e:
        print(f"⚠️ Error stopping emotion detection on shutdown: {e}")

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
        
        # Start emotion detection in a separate thread to avoid blocking
        emotion_thread = threading.Thread(target=start_emotion_detection, daemon=True)
        emotion_thread.start()
        
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

@app.get("/api/sessions")
async def get_sessions():
    """Get all session data from Memory.db for trends dashboard."""
    try:
        import sqlite3
        import os
        
        # Get database path
        backend_path = os.path.join(os.path.dirname(__file__), '..', '.backend')
        db_file = os.path.join(backend_path, "Memory.db")
        
        if not os.path.exists(db_file):
            return {
                "sessions": [],
                "message": "No sessions found"
            }
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get all sessions (not limited to 5)
        cursor.execute('''
        SELECT id, angry, stressed, happy, sad, focused, distractions
        FROM sessions
        ORDER BY id DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        # Format sessions data
        sessions = []
        for row in rows:
            sessions.append({
                "id": row[0],
                "angry": row[1],
                "stressed": row[2],
                "happy": row[3],
                "sad": row[4],
                "focused": row[5],
                "distractions": row[6]
            })
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/advice")
async def get_productivity_advice(sessions_data: dict):
    """Get productivity advice from Gemini based on all session data."""
    try:
        import sys
        import os
        
        # Add backend to path to import Gemini model
        backend_path = os.path.join(os.path.dirname(__file__), '..', '.backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        # Import Gemini model from backend
        import google.generativeai as genai
        genai.configure(api_key="AIzaSyB8YWnoZe-Ry3_eFp8yYlvRCgd6_aY1YoA")
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        sessions = sessions_data.get("sessions", [])
        
        if not sessions:
            return {
                "advice": "No session data available yet. Complete a few focus sessions to get personalized productivity advice!",
                "error": False
            }
        
        # Format session data for Gemini
        session_summary = []
        total_emotions = {
            "angry": 0,
            "stressed": 0,
            "happy": 0,
            "sad": 0,
            "focused": 0
        }
        total_distractions = 0
        
        for i, session in enumerate(sessions, 1):
            session_summary.append(
                f"Session {i}: "
                f"Angry={session.get('angry', 0)}, "
                f"Stressed={session.get('stressed', 0)}, "
                f"Happy={session.get('happy', 0)}, "
                f"Sad={session.get('sad', 0)}, "
                f"Focused={session.get('focused', 0)}, "
                f"Distractions={session.get('distractions', 0)}"
            )
            total_emotions["angry"] += session.get('angry', 0)
            total_emotions["stressed"] += session.get('stressed', 0)
            total_emotions["happy"] += session.get('happy', 0)
            total_emotions["sad"] += session.get('sad', 0)
            total_emotions["focused"] += session.get('focused', 0)
            total_distractions += session.get('distractions', 0)
        
        # Create prompt for Gemini
        prompt = f"""You are a productivity coach analyzing focus session data. Based on the following session data from a focus tracking app, provide specific, actionable advice on how the user can improve their productivity and focus. Respond 1 consise, detailed and insighful 3 sentences without markdown or any fancy typography.

Session Data (Total Sessions: {len(sessions)}):
{chr(10).join(session_summary)}

Aggregate Totals Across All Sessions:
- Angry: {total_emotions['angry']}
- Stressed: {total_emotions['stressed']}
- Happy: {total_emotions['happy']}
- Sad: {total_emotions['sad']}
- Focused: {total_emotions['focused']}
- Total Distractions: {total_distractions}
- Average Distractions per Session: {total_distractions / len(sessions):.1f}

Please provide:
1. A brief analysis of their focus patterns
2. Specific, actionable recommendations to improve productivity
3. Suggestions for reducing distractions
4. Tips for maintaining better emotional state during focus sessions

Keep the advice friendly, encouraging, and practical. Format it in a way that's easy to read with clear sections."""
        
        # Get advice from Gemini
        response = model.generate_content(prompt)
        advice = response.text
        
        return {
            "advice": advice,
            "error": False
        }
    except Exception as e:
        print(f"Error getting productivity advice: {e}")
        import traceback
        traceback.print_exc()
        return {
            "advice": f"Unable to generate advice at this time. Error: {str(e)}",
            "error": True
        }

# WebSocket endpoint for video streaming
@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    """
    WebSocket endpoint for streaming video frames from emotion detection.
    """
    client_host = websocket.client.host if hasattr(websocket, 'client') else 'unknown'
    print(f"Video WebSocket connection attempt from {client_host}")
    
    await websocket.accept()
    set_video_websocket(websocket)
    print(f"✅ Video WebSocket client connected and registered")
    
    # Check if emotion detection is running and inform it
    try:
        from EmotionDetection import running as emotion_running
        if emotion_running:
            print("✅ Emotion detection is running, video streaming should start now")
        else:
            print("⚠️ Emotion detection is not running yet")
    except:
        pass
    
    try:
        # Keep connection alive
        while True:
            # Wait for any message from client (ping/pong for keepalive)
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle ping messages
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        set_video_websocket(None)
        print(f"❌ Video WebSocket client disconnected")
    except Exception as e:
        print(f"❌ Video WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        set_video_websocket(None)

app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
