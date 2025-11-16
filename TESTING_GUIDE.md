# Testing Guide for Focus Rest Reminders

This guide explains how to test the Focus Rest Reminders system, including natural language parsing, timer settings, and notifications.

## Prerequisites

1. **Start the FastAPI server:**
   ```bash
   cd .frontend
   python main.py
   ```
   The server will run on `http://localhost:8000`

2. **Open the frontend in a browser:**
   - Navigate to `http://localhost:8000`
   - Grant notification permissions when prompted
   - Keep the browser tab open (you can minimize it)

3. **Verify WebSocket connection:**
   - Open browser console (F12)
   - You should see: "WebSocket connected for notifications"
   - Or check: `http://localhost:8000/api/notifications/status`

## Testing Methods

### Method 1: Automated Test Script (Recommended)

Run the comprehensive test script:

```bash
cd .backend
python test_focus_reminders.py
```

This will test:
- ✅ Natural language parsing via Gemini
- ✅ Timer settings extraction and validation
- ✅ Notification connection status
- ✅ Quick notification test (with short times)

**What to expect:**
- The script will test multiple natural language prompts
- It will verify that Gemini correctly parses focus/rest/repeat times
- It will check that timer settings are correctly applied
- Optionally run a quick test with 10-second focus periods

### Method 2: Manual Testing via Frontend

1. **Test Natural Language Parsing:**
   - Open `http://localhost:8000` in your browser
   - Enter a natural language prompt in the query box, for example:
     - "I want to focus for 25 minutes with 5 minute breaks every 5 minutes"
     - "Set up a pomodoro timer: 25 min focus, 5 min breaks"
     - "Focus for 30 minutes, take a 10 minute break every 10 minutes"
   - Click "Submit Query"
   - Check the response - it should show JSON with parsed times

2. **Verify Timer Settings:**
   - After submitting a query, check the timer status:
     ```bash
     curl http://localhost:8000/api/timer/status
     ```
   - Or visit: `http://localhost:8000/api/timer/status`
   - Verify the times match what you requested

3. **Start the Timer:**
   - Send a POST request to start the timer:
     ```bash
     curl -X POST http://localhost:8000/api/timer/start
     ```
   - Or add a button in the frontend to call this endpoint
   - Watch for notifications in your browser

### Method 3: Direct Python Testing

Test the components directly:

```python
# Test 1: Natural Language Parsing
from main import get_gemini_response, _parse_focus_settings

prompt = "I want to focus for 25 minutes with 5 minute breaks every 5 minutes"
gemini_output = get_gemini_response(prompt)
settings = _parse_focus_settings(gemini_output)
print(f"Parsed: {settings}")

# Test 2: Timer Settings
from FocusRestReminders import setFocusRestRepeatTimes, FocusTime, RestTime, RepeatTime

setFocusRestRepeatTimes(25*60, 5*60, 5*60)
print(f"Focus: {FocusTime}s, Rest: {RestTime}s, Repeat: {RepeatTime}s")

# Test 3: Quick Notification Test (10 seconds focus, 5 seconds rest)
from FocusRestReminders import startFocusRestTimer

setFocusRestRepeatTimes(10, 5, 5)  # Very short for quick testing
startFocusRestTimer()  # Watch for notifications!
```

## Expected Notifications

When the timer runs, you should receive these notifications in order:

1. **"Focus Period Started"** - When a focus period begins
2. **"Focus Progress"** - Progress update during focus (at ~5/6 of repeat time)
3. **"Focus Period Complete"** - When focus period ends
4. **"Rest Progress"** - Progress update during rest (at ~5/6 of rest time)
5. **"Rest Period Complete"** - When rest period ends
6. *(Repeats for each cycle)*

## Troubleshooting

### No Notifications Appearing

1. **Check WebSocket connection:**
   ```bash
   curl http://localhost:8000/api/notifications/status
   ```
   Should return `{"connected": true, "connection_count": 1}`

2. **Check browser console:**
   - Open DevTools (F12)
   - Look for WebSocket connection messages
   - Check for any errors

3. **Verify notification permissions:**
   - Check browser settings
   - Make sure notifications are allowed for `localhost:8000`

### Timer Not Starting

1. **Check if timer is configured:**
   ```bash
   curl http://localhost:8000/api/timer/status
   ```
   Should show non-zero values for all times

2. **Check server logs:**
   - Look for error messages in the terminal where the server is running

### Natural Language Parsing Issues

1. **Check Gemini API key:**
   - Verify the API key in `.backend/main.py` is valid

2. **Check Gemini response:**
   - The response should contain valid JSON
   - Check the console output for the raw Gemini response

3. **Test with simpler prompts:**
   - Try: "25 minutes focus, 5 minutes rest, 5 minutes repeat"
   - Or: "Focus 20 minutes, rest 3 minutes, check every 4 minutes"

## Quick Test Example

For a quick end-to-end test:

1. Start server: `python .frontend/main.py`
2. Open browser: `http://localhost:8000`
3. Grant notifications
4. Run test script: `python .backend/test_focus_reminders.py`
5. When prompted, choose 'y' for quick notification test
6. Watch for notifications (should take ~30 seconds total)

## Testing Checklist

- [ ] Server starts without errors
- [ ] Frontend loads in browser
- [ ] WebSocket connects (check console)
- [ ] Notification permission granted
- [ ] Natural language prompt parses correctly
- [ ] Timer settings are set correctly
- [ ] Notifications appear when timer starts
- [ ] All notification types appear (start, progress, complete)
- [ ] Timer completes full cycles

