import time
from datetime import datetime
from typing import Optional, Dict, Any

FocusTime = 0
RestTime = 0
RepeatTime = 0

# Timer state tracking
timer_state = {
    "is_running": False,
    "phase": None,  # "focus" or "rest"
    "cycle": 0,
    "total_cycles": 0,
    "start_time": None,
    "phase_start_time": None,
    "elapsed_time": 0,
    "phase_duration": 0,
    "time_remaining": 0,
    "notifications_sent": {
        "break_starting_10s": False,
        "break_started": False,
        "break_ending_5s": False,
        "break_ended": False,
        "timer_ending_5s": False,
        "timer_ended": False
    }
}


def setFocusRestRepeatTimes(FTime: int, RTime: int, ReTime: int):
    """
    Set the focus, rest, and repeat times for the timer.
    
    Args:
        FTime: Focus time in seconds
        RTime: Rest time in seconds
        ReTime: Repeat interval in seconds (how often to check progress)
    """
    global FocusTime, RestTime, RepeatTime
    FocusTime = FTime
    RestTime = RTime
    RepeatTime = ReTime


def get_timer_state() -> Dict[str, Any]:
    """Get the current timer state."""
    global timer_state
    if not timer_state["is_running"]:
        return timer_state.copy()
    
    # Calculate current state
    now = datetime.now()
    if timer_state["phase_start_time"]:
        elapsed = (now - timer_state["phase_start_time"]).total_seconds()
        timer_state["elapsed_time"] = elapsed
        timer_state["time_remaining"] = max(0, timer_state["phase_duration"] - elapsed)
    
    return timer_state.copy()


def reset_timer_state():
    """Reset the timer state."""
    global timer_state
    timer_state = {
        "is_running": False,
        "phase": None,
        "cycle": 0,
        "total_cycles": 0,
        "start_time": None,
        "phase_start_time": None,
        "elapsed_time": 0,
        "phase_duration": 0,
        "time_remaining": 0,
        "notifications_sent": {
            "break_starting_10s": False,
            "break_started": False,
            "break_ending_5s": False,
            "break_ended": False,
            "timer_ending_5s": False,
            "timer_ended": False
        }
    }


def startFocusRestTimer():
    """
    Start the focus/rest timer cycle.
    Timer state is tracked and can be polled via HTTP.
    """
    global FocusTime, RestTime, RepeatTime, timer_state
    
    # Validate that times are set
    if FocusTime == 0 or RestTime == 0 or RepeatTime == 0:
        print("Error: Focus, Rest, and Repeat times must be set before starting the timer.")
        return
    
    # Reset and initialize timer state
    reset_timer_state()
    timer_state["is_running"] = True
    timer_state["start_time"] = datetime.now()
    timer_state["total_cycles"] = int(FocusTime / RepeatTime) if RepeatTime > 0 else 1
    
    # Calculate total timer duration
    total_duration = FocusTime  # Total focus time
    
    for i in range(timer_state["total_cycles"]):
        timer_state["cycle"] = i + 1
        
        # FOCUS PHASE
        timer_state["phase"] = "focus"
        timer_state["phase_start_time"] = datetime.now()
        timer_state["phase_duration"] = RepeatTime
        timer_state["notifications_sent"]["break_starting_10s"] = False
        timer_state["notifications_sent"]["break_started"] = False
        
        # Run focus period
        focus_elapsed = 0
        while focus_elapsed < RepeatTime:
            time.sleep(1)
            focus_elapsed += 1
            
            # Check for 10 seconds before break starts
            if not timer_state["notifications_sent"]["break_starting_10s"] and focus_elapsed >= RepeatTime - 10:
                timer_state["notifications_sent"]["break_starting_10s"] = True
            
            # Check for 5 seconds before timer ends (if this is the last cycle)
            if i == timer_state["total_cycles"] - 1:
                total_elapsed = (datetime.now() - timer_state["start_time"]).total_seconds()
                if not timer_state["notifications_sent"]["timer_ending_5s"] and total_elapsed >= total_duration - 5:
                    timer_state["notifications_sent"]["timer_ending_5s"] = True
        
        # REST PHASE
        timer_state["phase"] = "rest"
        timer_state["phase_start_time"] = datetime.now()
        timer_state["phase_duration"] = RestTime
        timer_state["notifications_sent"]["break_started"] = True
        timer_state["notifications_sent"]["break_ending_5s"] = False
        timer_state["notifications_sent"]["break_ended"] = False
        
        # Run rest period
        rest_elapsed = 0
        while rest_elapsed < RestTime:
            time.sleep(1)
            rest_elapsed += 1
            
            # Check for 5 seconds before break ends
            if not timer_state["notifications_sent"]["break_ending_5s"] and rest_elapsed >= RestTime - 5:
                timer_state["notifications_sent"]["break_ending_5s"] = True
        
        timer_state["notifications_sent"]["break_ended"] = True
    
    # Timer complete
    timer_state["is_running"] = False
    timer_state["phase"] = None
    timer_state["notifications_sent"]["timer_ended"] = True


# Example usage (commented out to prevent running on import)
# if __name__ == "__main__":
#     # Set times (in seconds)
#     # Example: 25 minutes focus, 5 minutes rest, 5 minute intervals
#     setFocusRestRepeatTimes(FTime=25*60, RTime=5*60, ReTime=5*60)
#     startFocusRestTimer()