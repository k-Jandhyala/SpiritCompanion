import cv2
import time
from deepface import DeepFace
from ultralytics import YOLO
from collections import Counter, deque
import csv
import sqlite3
import os

# ---------------- CONFIG ----------------
emotion_counts = {
    "angry": 0,
    "stressed": 0,
    "happy": 0,
    "sad": 0,
    "focused": 0,
    "distractions": 0     # <--- NEW KEY HERE
}

WINDOW_SIZE = 5
emotion_window = deque(maxlen=WINDOW_SIZE)

phone_visible_start = None
DISTRACTION_THRESHOLD = 10  # seconds

yolo_model = YOLO("yolov8n.pt")

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

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

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

            region = result.get("region", None)
            if region:
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, stable_emotion, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    except:
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

                x1, y1, x2, y2 = box.xyxy[0]
                cv2.rectangle(frame,
                              (int(x1), int(y1)), (int(x2), int(y2)),
                              (0,255,255), 2)
                cv2.putText(frame,
                            f"PHONE {conf:.2f}",
                            (int(x1), int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0,255,255), 2)

    # ---------------- DISTRACTION LOGIC ----------------
    if phone_detected:
        if phone_visible_start is None:
            phone_visible_start = time.time()
        else:
            elapsed = time.time() - phone_visible_start
            if elapsed >= DISTRACTION_THRESHOLD:
                emotion_counts["distractions"] += 1   # <--- INCREMENT HERE
                print("⚠ You're distracted by your phone!")

                phone_visible_start = None
    else:
        phone_visible_start = None

    # ---------------- DISPLAY COUNTERS ----------------
    y_pos = 30
    for emo, count in emotion_counts.items():
        cv2.putText(frame, f"{emo}: {count}", (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180,255,180), 2)
        y_pos += 25

    cv2.imshow("Spirit Companion - Emotion + Distraction", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("\nFinal results:", emotion_counts)

# ---------------- CONFIG ----------------
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Memory.db")

# Create DB and table if not exists
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

# ---------------- SAVE CURRENT SESSION ----------------
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

# ---------------- KEEP ONLY LAST 5 SESSIONS ----------------
cursor.execute('SELECT COUNT(*) FROM sessions')
count = cursor.fetchone()[0]
if count > 5:
    # Delete oldest sessions beyond 5
    cursor.execute('''
    DELETE FROM sessions WHERE id IN (
        SELECT id FROM sessions ORDER BY id ASC LIMIT ?
    )
    ''', (count - 5,))
    conn.commit()

# ---------------- PRINT LAST 5 SESSIONS (NEWEST FIRST) ----------------
cursor.execute('''
SELECT angry, stressed, happy, sad, focused, distractions
FROM sessions
ORDER BY id DESC
LIMIT 5
''')
rows = cursor.fetchall()
print("\nLast 5 sessions (newest first):")
for i, row in enumerate(rows, 1):
    print(f"Session {i}: Angry={row[0]}, Stressed={row[1]}, Happy={row[2]}, Sad={row[3]}, Focused={row[4]}, Distractions={row[5]}")

conn.close()

print("Session saved to database:", DB_FILE)