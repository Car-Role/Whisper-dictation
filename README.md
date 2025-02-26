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

## Configuration

The application can be configured by editing the `config.json` file which is automatically created on first run:

```json
{
    "model": "tiny",
    "language": "en",
    "hotkey": {
        "ctrl": true,
        "shift": true,
        "key": "d"
    },
    "audio": {
        "chunk": 1024,
        "format": "paInt16",
        "channels": 1,
        "rate": 16000
    },
    "ui": {
        "indicator_size": 12,
        "indicator_color": "red",
        "transparency": 0.7
    },
    "typing": {
        "word_delay": 0.1
    }
}
```

### Configuration Options

#### Model Settings
- `model`: Whisper model to use ("tiny", "base", "small", "medium", "large")
- `language`: Language code for transcription (e.g., "en", "fr", "es")

#### Hotkey Settings
- `hotkey.ctrl`: Whether Ctrl key is required (true/false)
- `hotkey.shift`: Whether Shift key is required (true/false)
- `hotkey.key`: The main key to use (e.g., "d", "r", "t")

#### Audio Settings
- `audio.chunk`: Audio chunk size in bytes
- `audio.format`: Audio format (paInt16, paFloat32, etc.)
- `audio.channels`: Number of audio channels (1=mono, 2=stereo)
- `audio.rate`: Sample rate in Hz

#### UI Settings
- `ui.indicator_size`: Size of the recording indicator in pixels
- `ui.indicator_color`: Color of the recording indicator (standard color names)
- `ui.transparency`: Opacity of the indicator (0.0-1.0)

#### Typing Settings
- `typing.word_delay`: Delay between typed words in seconds

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
- openai-whisper
- pyaudio
- keyboard
- pyperclip
- pystray
- pillow
- torch
- torchaudio
- numpy
- imageio-ffmpeg
- psutil

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
