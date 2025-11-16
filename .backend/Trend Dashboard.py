import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

#read mysql data

distractions1 = 2
distractions2 = 1
distractions3 = 0
distractions4 = 5
distractions5 = 2

total_focus = 70
total_stress = 30
total_anger = 20
total_sadness = 25
total_happiness = 80

emotion_sum = total_focus + total_stress + total_anger + total_sadness + total_happiness

# --- Top-left graph: Emotions ---
emotions = ["Focused", "Stressed", "Angry", "Sad", "Happy"]
emotion_values = [
    100 * total_focus / emotion_sum,
    100 * total_stress / emotion_sum,
    100 * total_anger / emotion_sum,
    100 * total_sadness / emotion_sum,
    100 * total_happiness / emotion_sum
]

# --- Top-right graph: Sessions ---
session_numbers = [1, 2, 3, 4, 5]
session_values = [distractions1, distractions2, distractions3, distractions4, distractions5]

# --- Bottom-left text ---
max_emotion_index = np.argmax(emotion_values)
big_desc_1 = f"Highest Emotion: {emotions[max_emotion_index]}"

# --- Bottom-right text ---
big_value_2 = round(np.mean(session_values), 1)
big_desc_2 = "Average Distractions:"

# Create figure
fig = plt.figure(figsize=(12, 8))
gs = GridSpec(2, 2, figure=fig, height_ratios=[1.5, 1])  
plt.subplots_adjust(hspace=0.4, wspace=0.3)  

# --- Top-left: Emotions bar chart ---
ax_tl = fig.add_subplot(gs[0, 0])
ax_tl.bar(emotions, emotion_values, color="skyblue", width=0.5)  
ax_tl.set_title("Weekly Emotions", fontsize=20, fontweight="bold")  
ax_tl.set_ylabel("Percentage (%)")
ax_tl.margins(x=0.1)

# --- Top-right: Session line chart ---
ax_tr = fig.add_subplot(gs[0, 1])
ax_tr.plot(session_numbers, session_values, marker="o", color="orange", markersize=8, linewidth=2)
ax_tr.set_title("Distraction Trends", fontsize=20, fontweight="bold")  
ax_tr.set_xlabel("Session Number")
ax_tr.set_ylabel("Distractions")
ax_tr.margins(x=0.05)

# --- Bottom-left: Description ---
ax_bl = fig.add_subplot(gs[1, 0])
ax_bl.axis("off")
ax_bl.text(
    0.5, 0.5,
    big_desc_1,
    fontsize=28,
    ha="center",
    va="center",
    wrap=True
)

# --- Bottom-right: Large text with value ---
ax_br = fig.add_subplot(gs[1, 1])
ax_br.axis("off")
ax_br.text(
    0.5, 0.5,
    f"{big_desc_2}\n{big_value_2}",
    fontsize=32,
    ha="center",
    va="center",
    wrap=True
)

# Save figure
plt.tight_layout()
plt.savefig("trend_dashboard.png", dpi=150)
plt.close()

print("Dashboard saved as trend_dashboard.png")