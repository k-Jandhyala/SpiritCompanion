import cv2
from deepface import DeepFace
from collections import Counter, deque

# ---------------- CONFIG ---------------- 
# Your 5 emotions
emotion_counts = {"angry":0, "stressed":0,"happy":0, "sad":0, "focused":0}
WINDOW_SIZE = 5
emotion_window = deque(maxlen=WINDOW_SIZE)

# Map DeepFace emotions to custom emotions
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

# Smooth emotion over last few frames
def smooth_emotion(new_emotion):
    emotion_window.append(new_emotion)
    return Counter(emotion_window).most_common(1)[0][0]

# ---------------- MAIN LOOP ----------------
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    try:
        # Analyze frame for emotion
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=True)
        
        if isinstance(result, list):
            # DeepFace may return a list for multiple faces
            result = result[0]

        dominant_emotion = result.get('dominant_emotion', None)

        if dominant_emotion:
            dominant_emotion = dominant_emotion.lower()
            custom_emotion = map_emotion(dominant_emotion)
            stable_emotion = smooth_emotion(custom_emotion)
            emotion_counts[stable_emotion] += 1

            # Draw bounding box and label
            face_region = result.get('region', None)
            if face_region:
                x, y, w, h = face_region['x'], face_region['y'], face_region['w'], face_region['h']
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, stable_emotion, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    except Exception as e:
        # Ignore frames where no face is detected
        pass

    # Display emotion counts on screen
    y0 = 50
    for emo, count in emotion_counts.items():
        cv2.putText(frame, f"{emo}: {count}", (10, y0),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180,255,180), 2)
        y0 += 25

    cv2.imshow("Spirit Companion Emotion Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
print("Final emotion counts:", emotion_counts)
