import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as patches
#FIXme
"""""
from EmotionDetection import emotion_counts

distracted = 35

emotion_sum = emotion_counts["focused"] + emotion_counts["stressed"] 
+ emotion_counts["angry"] + emotion_counts["sad"] + emotion_counts["happy"]

categories = ["Focused", "Stressed", "Angry", "Sad", "Happy"]
values = [100 * emotion_counts["focused"] / emotion_sum, 
          100 * emotion_counts["stressed"] / emotion_sum, 
          100 * emotion_counts["angry"] / emotion_sum, 
          100 * emotion_counts["sad"] / emotion_sum, 
          100 * emotion_counts["happy"] / emotion_sum]
"""
categories = ["Focused", "Stressed", "Angry", "Sad", "Happy"]
values = [40, 
          20, 
          30, 
          20, 
          10]

# import distractions from mysql
distracted = 35.0                                 #FIXme
distraction_vector = {1, 2, 3, 1,}                  #FIXme
average = sum(distraction_vector) / len(distraction_vector)

big_value = distracted
big_value_description = "In this session\nyou were distracted:"
big_value_end = " times"


# --------------------
fantasy_colors = [
    "#6B5B95",  
    "#88B04B",  
    "#FF6F61",  
    "#92A8D1", 
    "#955251"   
]


# --------------------
# Create the figure
# --------------------
fig = plt.figure(figsize=(12, 6))
gs = GridSpec(1, 2, width_ratios=[1, 2], figure=fig)


# Parchment background
fig.patch.set_facecolor("#F4EAD5")


# --------------------
# Left: Single clean text
# --------------------
ax_left = fig.add_subplot(gs[0])
ax_left.axis("off")

#curr val - avg
difference = distracted - average
if difference >= 0:
    end_message = "You were distracted\nmore than your average today,\ntry to focus more"
else:
    end_message = "You were distracted\nless than your average today,\ngood job!"

ax_left.text(
    0.5, 0.5,
    f"{big_value_description}\n{big_value}{big_value_end}\n\n{end_message}",
    fontsize=25,
    color="#4A2C2A",       
    fontweight="bold",
    ha="center", va="center"
)

# --------------------
# Right: Clean fantasy bar chart
# --------------------
ax_right = fig.add_subplot(gs[1])
ax_right.set_facecolor("#F4EAD5")   # parchment interior


# Draw bars (simple, no glow)
for i, (cat, val, base_color) in enumerate(zip(categories, values, fantasy_colors)):
    ax_right.add_patch(
        patches.FancyBboxPatch(
            (i - 0.3, 0),
            0.6,
            val,
            boxstyle="round,pad=0.12",
            facecolor=base_color,
            edgecolor="black",
            linewidth=1.3
        )
    )


ax_right.set_xlim(-0.5, len(categories)-0.5)
ax_right.set_ylim(0, max(values) * 1.3)


ax_right.set_xticks(range(len(categories)))
ax_right.set_xticklabels(
    categories,
    fontsize=12,
    fontweight="bold",
    color="#3B2F2F"
)


ax_right.set_ylabel(
    "Percent (%)",
    fontsize=14,
    fontweight="bold",
    color="#3B2F2F"
)


# Clean title
ax_right.set_title(
    "Session Summary",
    fontsize=24,
    color="#4A2C2A",
    pad=15,
    fontweight="bold"
)


# Rune-style dashed grid
ax_right.yaxis.grid(True, linestyle="--", alpha=0.3, color="#6B5B95")
ax_right.set_axisbelow(True)


# --------------------
# Save figure
# --------------------
plt.tight_layout()
plt.savefig("session_summary.png", dpi=150)
plt.close()


print("Fantasy dashboard saved as session_summary.png")
print(average, distracted)
