import google.generativeai as genai
from FocusRestReminders import setFocusRestRepeatTimes, startFocusRestTimer
import re
import json

# Configure Gemini API
genai.configure(api_key="AIzaSyB8YWnoZe-Ry3_eFp8yYlvRCgd6_aY1YoA")
model = genai.GenerativeModel("models/gemini-2.5-flash")


def _parse_focus_settings(gemini_output: str) -> dict:
    """
    Take Gemini's raw text (which should be JSON in a code block)
    and return a dict with focus_time, break_frequency, break_duration.
    """

    # Remove ```json and ``` if they exist
    cleaned = re.sub(r"```json|```", "", gemini_output).strip()

    # Optionally: if there's random text around, pull out just the {...}
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0)

    data = json.loads(cleaned)

    # Handle multiple possible key names that Gemini might use
    # Try different variations of focus time (check if key exists, not just truthy value)
    focus_time = None
    for key in ["focus_time", "focus_duration", "focus_period", "focus"]:
        if key in data:
            focus_time = data[key]
            break
    if focus_time is None:
        focus_time = 600  # 10 min default
    
    # Try different variations of break frequency
    break_frequency = None
    for key in ["break_frequency", "break_interval", "repeat_interval", "check_interval", "interval"]:
        if key in data:
            break_frequency = data[key]
            break
    if break_frequency is None:
        break_frequency = 300  # 5 min default
    
    # Try different variations of break duration
    break_duration = None
    for key in ["break_duration", "rest_duration", "rest_time", "break_time", "rest"]:
        if key in data:
            break_duration = data[key]
            break
    if break_duration is None:
        break_duration = 120  # 2 min default

    # Convert to ints
    focus_time = int(focus_time)
    break_frequency = int(break_frequency)
    break_duration = int(break_duration)

    return {
        "focus_time": focus_time,
        "break_frequency": break_frequency,
        "break_duration": break_duration,
    }


def get_gemini_response(query: str) -> str:
    """
    Send a query to Gemini and return the response text.

    Args:
        query: The user's query string

    Returns:
        The Gemini response text

    Raises:
        Exception: If there's an error generating the response
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    print(f"Processing your focus request {query}")

    # Send query to Gemini with explicit JSON format
    query = (
        "Given the statement below, extract the focus timer settings and return ONLY a JSON object with these exact keys: "
        '"focus_time" (total focus duration in seconds), '
        '"break_frequency" (how often to take breaks in seconds), '
        '"break_duration" (length of each break in seconds). '
        "All values must be in seconds as integers. "
        "If any value is not specified, use these defaults: focus_time=600 (10 mins), break_frequency=300 (5 mins), break_duration=120 (2 mins). "
        "Return ONLY the JSON object, no other text. Example format: {\"focus_time\": 120, \"break_frequency\": 60, \"break_duration\": 5}\n\n"
        + query
    )
    response = model.generate_content(query)

    # Extract the text from the response
    gemini_output = response.text

    print(f"Gemini response received: {len(gemini_output)} characters")
    
    focus_settings = _parse_focus_settings(gemini_output)
    
    # Set the timer with parsed settings
    setFocusRestRepeatTimes(
        focus_settings["focus_time"], 
        focus_settings["break_duration"],  # Note: RestTime is break_duration
        focus_settings["break_frequency"]  # Note: RepeatTime is break_frequency
    )
    
    # Optionally start the timer automatically
    # Uncomment the line below if you want the timer to start automatically
    # startFocusRestTimer()
    
    return gemini_output
