import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any

# Import NotificationSender for sending web push notifications
try:
    from NotificationSender import send_notification
except ImportError:
    # Fallback if NotificationSender is not available
    def send_notification(title, body="", **kwargs):
        print(f"Notification: {title} - {body}")
    print("Warning: NotificationSender not available, notifications will be printed to console")

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
    "focus_time_remaining": 0,  # Total focus time remaining
    "notifications_sent": {
        "timer_started": False,
        "break_starting_10s": False,
        "break_started": False,
        "break_ending_5s": False,
        "break_ended": False,
        "timer_complete": False
    }
}

# Thread control
_timer_thread = None
_timer_stop_event = threading.Event()


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
    
    # Calculate focus time remaining if in focus phase
    if timer_state["phase"] == "focus":
        # Focus time remaining is already being tracked in the timer loop
        pass
    
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
        "focus_time_remaining": 0,
        "notifications_sent": {
            "timer_started": False,
            "break_starting_10s": False,
            "break_started": False,
            "break_ending_5s": False,
            "break_ended": False,
            "timer_complete": False
        }
    }


def _run_timer():
    """
    Internal function that runs the timer in a separate thread.
    This implements the timer logic: count focus time, pause for breaks, resume after breaks.
    """
    global FocusTime, RestTime, RepeatTime, timer_state, _timer_stop_event
    
    # Validate that times are set
    if FocusTime == 0 or RestTime == 0 or RepeatTime == 0:
        print("Error: Focus, Rest, and Repeat times must be set before starting the timer.")
        return
    
    # Reset and initialize timer state
    reset_timer_state()
    timer_state["is_running"] = True
    timer_state["start_time"] = datetime.now()
    timer_state["focus_time_remaining"] = FocusTime  # Total focus time remaining
    
    # Send notification when timer starts
    if not timer_state["notifications_sent"]["timer_started"]:
        timer_state["notifications_sent"]["timer_started"] = True
        send_notification(
            "⏰ Timer Started!",
            f"Focusing for {FocusTime} seconds with {RestTime} second breaks every {RepeatTime} seconds!",
            tag="timer-started"
        )
    
    # Main timer loop: continue until all focus time is used up
    while timer_state["focus_time_remaining"] > 0 and not _timer_stop_event.is_set():
        # Calculate how much focus time to use in this cycle
        # Use RepeatTime, but don't exceed remaining focus time
        focus_duration = min(RepeatTime, timer_state["focus_time_remaining"])
        
        # FOCUS PHASE
        timer_state["phase"] = "focus"
        timer_state["phase_start_time"] = datetime.now()
        timer_state["phase_duration"] = focus_duration
        timer_state["time_remaining"] = focus_duration
        timer_state["notifications_sent"]["break_starting_10s"] = False
        
        # Run focus period
        focus_elapsed = 0
        while focus_elapsed < focus_duration and not _timer_stop_event.is_set():
            time.sleep(1)
            focus_elapsed += 1
            timer_state["focus_time_remaining"] -= 1
            timer_state["time_remaining"] = focus_duration - focus_elapsed
            timer_state["elapsed_time"] = focus_elapsed
            
            # Check for 10 seconds before break starts (only if there's still focus time remaining after this cycle)
            # We're 10 seconds away from the end of this focus period
            # Send notification if: we're at the 10-second mark AND there's still focus time remaining after this cycle
            # (i.e., focus_time_remaining will be > 0 after this cycle ends, meaning a break will follow)
            if (not timer_state["notifications_sent"]["break_starting_10s"] and 
                focus_elapsed == focus_duration - 10 and 
                timer_state["focus_time_remaining"] > 10):
                timer_state["notifications_sent"]["break_starting_10s"] = True
                send_notification(
                    "⏳ Rest Starting Soon!",
                    "Your break will begin in 10 seconds!",
                    tag="break-starting-10s"
                )
        
        if _timer_stop_event.is_set():
            break
        
        # Check if we've completed all focus time
        if timer_state["focus_time_remaining"] <= 0:
            # Timer complete - send notification
            if not timer_state["notifications_sent"]["timer_complete"]:
                timer_state["notifications_sent"]["timer_complete"] = True
                send_notification(
                    "🎉 Timer Complete!",
                    f"You've completed {FocusTime} seconds of focused work! Great job!",
                    tag="timer-complete"
                )
            break
        
        # REST PHASE - only if there's still focus time remaining
        if timer_state["focus_time_remaining"] > 0:
            timer_state["phase"] = "rest"
            timer_state["phase_start_time"] = datetime.now()
            timer_state["phase_duration"] = RestTime
            timer_state["time_remaining"] = RestTime
            timer_state["notifications_sent"]["break_started"] = False
            timer_state["notifications_sent"]["break_ending_5s"] = False
            timer_state["notifications_sent"]["break_ended"] = False
            
            # Send notification when rest starts
            if not timer_state["notifications_sent"]["break_started"]:
                timer_state["notifications_sent"]["break_started"] = True
                send_notification(
                    "🌿 Rest Period Started!",
                    f"Time for a {RestTime} second break!",
                    tag="break-started"
                )
            
            # Run rest period
            rest_elapsed = 0
            while rest_elapsed < RestTime and not _timer_stop_event.is_set():
                time.sleep(1)
                rest_elapsed += 1
                timer_state["time_remaining"] = RestTime - rest_elapsed
                timer_state["elapsed_time"] = rest_elapsed
                
                # Check for 5 seconds before break ends
                if (not timer_state["notifications_sent"]["break_ending_5s"] and 
                    rest_elapsed >= RestTime - 5):
                    timer_state["notifications_sent"]["break_ending_5s"] = True
                    send_notification(
                        "⏳ Break Ending Soon!",
                        "Your break will end in 5 seconds! Get ready to focus!",
                        tag="break-ending-5s"
                    )
            
            if _timer_stop_event.is_set():
                break
            
            # Send notification when rest ends
            if not timer_state["notifications_sent"]["break_ended"]:
                timer_state["notifications_sent"]["break_ended"] = True
                send_notification(
                    "✨ Break Finished!",
                    "Break complete! Ready to get back to work!",
                    tag="break-ended"
                )
            
            # Reset notification flags for next focus cycle
            timer_state["notifications_sent"]["break_starting_10s"] = False
    
    # Timer complete
    timer_state["is_running"] = False
    timer_state["phase"] = None
    _timer_stop_event.clear()


def startFocusRestTimer():
    """
    Start the focus/rest timer cycle in a separate thread.
    Timer state is tracked and can be polled via HTTP.
    """
    global _timer_thread, _timer_stop_event
    
    # Stop any existing timer
    if _timer_thread is not None and _timer_thread.is_alive():
        _timer_stop_event.set()
        _timer_thread.join(timeout=1)
    
    # Reset stop event
    _timer_stop_event.clear()
    
    # Start timer in a new thread
    _timer_thread = threading.Thread(target=_run_timer, daemon=True)
    _timer_thread.start()
    print("Timer started in background thread")


# Example usage (commented out to prevent running on import)
# if __name__ == "__main__":
#     # Set times (in seconds)
#     # Example: 25 minutes focus, 5 minutes rest, 5 minute intervals
#     setFocusRestRepeatTimes(FTime=25*60, RTime=5*60, ReTime=5*60)
#     startFocusRestTimer()