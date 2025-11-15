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
    await websocket.accept()
    notification_sender.register_websocket(websocket)
    
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
            except json.JSONDecodeError:
                # If not JSON, just ignore (could be plain text)
                pass
    except WebSocketDisconnect:
        notification_sender.unregister_websocket(websocket)
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        notification_sender.unregister_websocket(websocket)

# Endpoint to check notification connection status
@app.get("/api/notifications/status")
async def get_notification_status():
    """Get the status of notification connections."""
    return {
        "connected": notification_sender.has_connections(),
        "connection_count": notification_sender.get_connection_count()
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
