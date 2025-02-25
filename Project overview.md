# Whisper Dictation

A Python-based dictation tool that uses OpenAI's Whisper model for real-time speech-to-text transcription.

## Features

### Global Hotkey (Ctrl+Shift+D)
- Press and hold to start dictation
- Release to stop and auto-transcribe
- Smart override: Only blocks other apps when full Ctrl+Shift+D is pressed
- Regular 'D' key functions normally
- **NEW:** Configurable hotkey combination via config.json

### Visual Feedback
- Minimalist red circle indicator in bottom-right corner
- Always-on-top display while recording
- Semi-transparent for minimal distraction
- Clear console messages for status updates
- **NEW:** Configurable indicator size and color

### Audio Recording
- Real-time microphone input
- Automatic save handling
- Temporary storage in `assets/dictation.wav`
- Clean resource management
- **NEW:** Automatic cleanup of temporary files

### Smart Transcription
- Powered by OpenAI's Whisper models
- Automatic start after recording
- Natural word-by-word typing
- Intelligent spacing preservation
- **NEW:** Configurable model selection and language settings

### Configuration
- **NEW:** User-friendly JSON configuration file
- **NEW:** Customizable audio settings
- **NEW:** Adjustable UI preferences
- **NEW:** Configurable typing behavior

## Usage Flow

1. **Launch Application**
   ```
   python dictation.py
   ```

2. **Record Speech**
   - Hold `Ctrl+Shift+D` (or your configured hotkey)
   - Speak clearly into your microphone
   - Watch for the red indicator
   - Release the hotkey when done

3. **Automatic Transcription**
   - Recording saves automatically
   - Transcription starts immediately
   - Text appears word by word
   - Success message shows full transcription
   - Temporary files are cleaned up

## Detailed User Flow

### Step-by-Step Process
1. **Initiate Recording**
   - Press and hold your configured hotkey
   - Red indicator appears in bottom-right corner
   - Console shows "🎤 Recording..." message

2. **During Recording**
   - Keep hotkey held down
   - Speak clearly into your microphone
   - Red indicator remains visible
   - Recording captures your speech

3. **Stop Recording**
   - Release the hotkey
   - Red indicator disappears
   - Console shows "✅ Stopped recording."
   - Audio file is saved temporarily

4. **Transcription Process**
   - Starts automatically after recording
   - Console shows "📝 Transcribing..."
   - Whisper model processes your speech
   - No user action required

5. **Text Output**
   - Text appears at your current cursor position
   - Words are typed out sequentially
   - Natural spacing is maintained
   - Works in any text input field

6. **Cleanup**
   - Temporary audio file is automatically removed
   - System resources are properly released
   - Ready for next dictation

### Expected Timing
- Recording: Instant start/stop
- Transcription: Brief processing delay
- Text Output: Word-by-word with small delays

### Visual Indicators
- Red Circle: Active recording
- Console Messages: Status updates
- Cursor Movement: Shows typing progress

## Technical Specifications

### Audio Settings
- Sample Rate: 16000 Hz (configurable)
- Format: WAV
- Channels: Mono (configurable)
- Buffer Size: 1024 bytes (configurable)

### Model Settings
- Model: Whisper (configurable from tiny to large)
- Language: English (configurable)
- Processing: Real-time
- Output: Word-by-word typing

### Error Handling
- Clear error messages
- Automatic resource cleanup
- Graceful recovery from failures
- No-speech detection
- Fallback to tiny model if requested model fails to load

## Dependencies
- whisper: OpenAI's speech recognition model
- pyaudio: Audio recording and playback
- keyboard: Global hotkey management
- numpy: Audio data processing
- tkinter: Visual indicator interface

## Project Structure
```
whisper-dictation/
├── dictation.py      # Main application
├── config.json       # User configuration
├── README.md         # Documentation
└── assets/           # Generated directory
    └── dictation.wav # Temporary audio file
```

## Known Behaviors
- The red indicator shows only while recording
- Brief delay between recording and transcription
- Small pauses between typed words for readability
- Hotkey override only affects configured key combination
- Configuration changes take effect on next program start
