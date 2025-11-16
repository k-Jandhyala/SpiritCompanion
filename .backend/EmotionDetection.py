import cv2
import time
import base64
import threading
from deepface import DeepFace
from ultralytics import YOLO
from collections import Counter, deque
import sqlite3
import os

global cap

# ---------------- CONFIG ----------------
emotion_counts = {
    "angry": 0,
    "stressed": 0,
    "happy": 0,
    "sad": 0,
    "focused": 0,
    "distractions": 0
}

WINDOW_SIZE = 5
emotion_window = deque(maxlen=WINDOW_SIZE)

phone_visible_start = None
DISTRACTION_THRESHOLD = 4  # seconds

yolo_model = YOLO("yolov8n.pt")

# Global control & resources
running = False
session_active = False
cap = None
video_websocket = None  # WebSocket connection for streaming video
current_emotion = None
current_phone_detected = False
_main_event_loop = None  # Main FastAPI event loop

# ---------------- HELPERS ----------------
def map_emotion(df_emotion):
    df_emotion = df_emotion.lower()
    if df_emotion == "angry":
        return "angry"
    elif df_emotion in ["fear", "disgust"]:
        return "stressed"
    elif df_emotion == "happy":
        return "happy"
    elif df_emotion == "sad":
        return "sad"
    elif df_emotion in ["neutral", "surprise"]:
        return "focused"
    else:
        return "stressed"

def smooth_emotion(new_emotion):
    emotion_window.append(new_emotion)
    return Counter(emotion_window).most_common(1)[0][0]

# ---------------- DATABASE HELPERS ----------------
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Memory.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        angry INTEGER,
        stressed INTEGER,
        happy INTEGER,
        sad INTEGER,
        focused INTEGER,
        distractions INTEGER
    )
    ''')
    conn.commit()
    conn.close()

def save_session_to_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # SAVE CURRENT SESSION
    cursor.execute('''
    INSERT INTO sessions (angry, stressed, happy, sad, focused, distractions)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        emotion_counts["angry"],
        emotion_counts["stressed"],
        emotion_counts["happy"],
        emotion_counts["sad"],
        emotion_counts["focused"],
        emotion_counts["distractions"]
    ))
    conn.commit()

    # KEEP ONLY LAST 5 SESSIONS
    cursor.execute('SELECT COUNT(*) FROM sessions')
    count = cursor.fetchone()[0]
    if count > 5:
        cursor.execute('''
        DELETE FROM sessions WHERE id IN (
            SELECT id FROM sessions ORDER BY id ASC LIMIT ?
        )
        ''', (count - 5,))
        conn.commit()

    # PRINT LAST 5 SESSIONS (NEWEST FIRST)
    cursor.execute('''
    SELECT angry, stressed, happy, sad, focused, distractions
    FROM sessions
    ORDER BY id DESC
    LIMIT 5
    ''')
    rows = cursor.fetchall()
    print("\nLast 5 sessions (newest first):")
    for i, row in enumerate(rows, 1):
        print(f"Session {i}: Angry={row[0]}, Stressed={row[1]}, "
              f"Happy={row[2]}, Sad={row[3]}, Focused={row[4]}, "
              f"Distractions={row[5]}")

    conn.close()
    print("Session saved to database:", DB_FILE)

# ---------------- START / STOP FUNCTIONS ----------------
def start_emotion_detection():
    """
    Starts the webcam emotion + phone distraction detection loop.
    Everything is saved when stop_emotion_detection() is called
    (including via ESC key).
    """
    global running, cap, phone_visible_start, emotion_counts, emotion_window, session_active

    # Reset per-session state
    emotion_counts = {k: 0 for k in emotion_counts}
    emotion_window.clear()
    phone_visible_start = None

    init_db()

    # Try to open camera - try multiple indices
    cap = None
    for camera_index in [0, 1, 2]:
        print(f"Attempting to open camera index {camera_index}...")
        test_cap = cv2.VideoCapture(camera_index)
        if test_cap.isOpened():
            # Test if we can actually read a frame
            ret, test_frame = test_cap.read()
            if ret and test_frame is not None:
                cap = test_cap
                print(f"✅ Successfully opened camera index {camera_index}")
                break
            else:
                test_cap.release()
                print(f"❌ Camera index {camera_index} opened but cannot read frames")
        else:
            print(f"❌ Could not open camera index {camera_index}")
    
    if cap is None or not cap.isOpened():
        print("❌ Error: Could not open any camera")
        running = False
        session_active = False
        return
    
    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    running = True
    session_active = True
    print("✅ Emotion detection started, waiting for WebSocket connection...")

    frame_count = 0
    try:
        while running:
            # Check if camera is still available
            if cap is None or not cap.isOpened():
                print("❌ Camera no longer available, stopping detection")
                break
            
            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"⚠️ Failed to read frame from camera (attempt {frame_count})")
                frame_count += 1
                if frame_count > 10:
                    print("❌ Camera stopped providing frames, stopping detection")
                    break
                time.sleep(0.1)  # Wait a bit before retrying
                continue
            
            frame_count = 0  # Reset counter on successful read

            # ---------------- EMOTION DETECTION ----------------
            try:
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=True)

                if isinstance(result, list):
                    result = result[0]

                dominant_emotion = result.get("dominant_emotion", None)

                if dominant_emotion:
                    mapped = map_emotion(dominant_emotion)
                    stable_emotion = smooth_emotion(mapped)
                    emotion_counts[stable_emotion] += 1
                    current_emotion = stable_emotion

                    region = result.get("region", None)
                    if region:
                        x, y, w, h = region['x'], region['y'], region['w'], region['h']
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, stable_emotion, (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            except Exception:
                current_emotion = None
                pass

            # ---------------- PHONE DETECTION (YOLO) ----------------
            phone_detected = False
            results = yolo_model(frame, verbose=False)

            for r in results:
                for box in r.boxes:
                    cls = int(box.cls)
                    conf = float(box.conf)
                    label = yolo_model.names[cls]

                    if label == "cell phone" and conf > 0.5:
                        phone_detected = True
                        current_phone_detected = True

                        x1, y1, x2, y2 = box.xyxy[0]
                        cv2.rectangle(frame,
                                      (int(x1), int(y1)), (int(x2), int(y2)),
                                      (0, 255, 255), 2)
                        cv2.putText(frame,
                                    f"PHONE {conf:.2f}",
                                    (int(x1), int(y1) - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7, (0, 255, 255), 2)
            
            if not phone_detected:
                current_phone_detected = False

            # ---------------- DISTRACTION LOGIC ----------------
            global DISTRACTION_THRESHOLD
            if phone_detected:
                if phone_visible_start is None:
                    phone_visible_start = time.time()
                else:
                    elapsed = time.time() - phone_visible_start
                    if elapsed >= DISTRACTION_THRESHOLD:
                        emotion_counts["distractions"] += 1
                        print("⚠ You're distracted by your phone!")
                        phone_visible_start = None
            else:
                phone_visible_start = None

            # ---------------- DISPLAY COUNTERS ----------------
            y_pos = 30
            for emo, count in emotion_counts.items():
                cv2.putText(frame, f"{emo}: {count}", (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 255, 180), 2)
                y_pos += 25

            # Stream frame to WebSocket if connected
            if video_websocket is not None:
                try:
                    # Check if frame is valid
                    if frame is None or frame.size == 0:
                        print("⚠️ Invalid frame, skipping")
                        continue
                    
                    # Encode frame as JPEG
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not success or buffer is None:
                        print("⚠️ Failed to encode frame as JPEG")
                        continue
                        
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    if not frame_base64:
                        print("⚠️ Failed to encode frame to base64")
                        continue
                    
                    # Send frame and classification data
                    import asyncio
                    import json
                    message = {
                        "type": "video_frame",
                        "frame": frame_base64,
                        "emotion": current_emotion,
                        "phone_detected": current_phone_detected,
                        "emotion_counts": emotion_counts.copy()
                    }
                    
                    # Send via WebSocket (need to handle async)
                    # Use the main event loop from FastAPI
                    loop = _main_event_loop
                    if loop is None:
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            print("⚠️ No event loop available for sending video frames")
                            continue
                    
                    if loop and loop.is_running():
                        # Use run_coroutine_threadsafe to send from background thread
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                _send_video_frame(video_websocket, json.dumps(message)),
                                loop
                            )
                            # Don't wait for result to avoid blocking, but check for exceptions
                            # future.result(timeout=0.1)  # Quick check if it failed immediately
                        except Exception as e:
                            print(f"⚠️ Error scheduling frame send: {e}")
                    else:
                        if video_websocket is not None:
                            print(f"⚠️ Event loop is not running (loop={loop}), cannot send video frame")
                except Exception as e:
                    print(f"Error sending video frame: {e}")
                    import traceback
                    traceback.print_exc()

            # Don't show cv2 window if streaming to web
        # cv2.imshow("Spirit Companion - Emotion + Distraction", frame)

        # Press ESC to stop (only if cv2 window is shown)
        # if cv2.waitKey(1) & 0xFF == 27:
        #     stop_emotion_detection()
        #     break
    
    except KeyboardInterrupt:
        print("⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error in emotion detection loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure camera is always released, even if loop exits unexpectedly
        if cap is not None:
            try:
                if cap.isOpened():
                    print("📹 Releasing camera in finally block...")
                    cap.release()
                    print("✅ Camera released in finally block")
                cap = None
                print("✅ Camera reference cleared in finally block")
            except Exception as e:
                print(f"⚠️ Error releasing camera in finally: {e}")
                import traceback
                traceback.print_exc()
                # Still try to clear the reference
                cap = None
        
        # Call stop_emotion_detection to clean up everything (but skip camera release since we just did it)
        if session_active:
            # Temporarily set cap to None to prevent double release
            temp_cap = cap
            cap = None
            stop_emotion_detection()
            # Restore cap if it wasn't None (shouldn't happen, but just in case)
            if temp_cap is not None:
                cap = temp_cap


async def _send_video_frame(websocket, message):
    """Helper function to send video frame via WebSocket."""
    try:
        await websocket.send_text(message)
    except Exception as e:
        print(f"Error sending video frame to WebSocket: {e}")

def set_video_websocket(websocket):
    """Set the WebSocket connection for video streaming."""
    global video_websocket
    video_websocket = websocket
    if websocket is not None:
        print("✅ Video WebSocket registered in EmotionDetection")
    else:
        print("❌ Video WebSocket cleared in EmotionDetection")

def set_event_loop(loop):
    """Set the main event loop for async operations."""
    global _main_event_loop
    _main_event_loop = loop
    if loop is not None:
        print("✅ Event loop set in EmotionDetection")


def stop_emotion_detection():
    """
    Stops the detection loop, releases resources, and
    saves everything to the DB (same behavior as original script).
    """
    global running, cap, session_active, video_websocket, current_emotion, current_phone_detected

    if not session_active:
        # Already stopped / saved, but still try to release camera if it exists
        if cap is not None:
            try:
                if cap.isOpened():
                    print("📹 Releasing camera (already stopped but camera still open)...")
                    cap.release()
                cap = None
            except Exception as e:
                print(f"⚠️ Error releasing camera: {e}")
        return

    print("🛑 Stopping emotion detection...")
    session_active = False
    running = False
    current_emotion = None
    current_phone_detected = False

    # Release camera properly - THIS IS CRITICAL
    # Always attempt to release, even if cap might be None
    camera_released = False
    if cap is not None:
        try:
            # Check if camera is opened before releasing
            is_opened = False
            try:
                is_opened = cap.isOpened()
            except:
                # If isOpened() fails, try to release anyway
                is_opened = True  # Assume it's open if we can't check
            
            if is_opened:
                print("📹 Releasing camera...")
                cap.release()
                camera_released = True
                print("✅ Camera released successfully")
            else:
                print("⚠️ Camera was not opened, but reference exists - clearing reference")
        except Exception as e:
            print(f"❌ Error releasing camera: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Always set to None to clear the reference, regardless of errors
            cap = None
            print("✅ Camera reference cleared")
            if not camera_released:
                print("⚠️ Warning: Camera may not have been properly released")
    else:
        print("⚠️ Camera reference was already None - nothing to release")

    # Close all OpenCV windows
    try:
        cv2.destroyAllWindows()
        print("✅ OpenCV windows closed")
    except Exception as e:
        print(f"⚠️ Error closing OpenCV windows: {e}")

    # Print final results (like original)
    print("\nFinal results:", emotion_counts)

    # Save to DB (same functionality as your original code)
    try:
        save_session_to_db()
        print("✅ Session saved to database")
    except Exception as e:
        print(f"⚠️ Error saving session to database: {e}")
    
    # Clear video websocket
    if video_websocket is not None:
        print("🔌 Clearing video WebSocket connection")
        video_websocket = None
    
    print("✅ Emotion detection stopped completely - camera is released")


# Optional: run directly
if __name__ == "__main__":
    start_emotion_detection()
