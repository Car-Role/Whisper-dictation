"""
Whisper Dictation - A speech-to-text application using OpenAI's Whisper model
"""
import whisper
import pyaudio
import wave
import keyboard
import pyperclip
import time
import threading
import os
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path
import ctypes
from ctypes import wintypes
import sys
import pystray
from PIL import Image, ImageDraw
import warnings

# Hide console window when run from file explorer
if sys.executable.endswith('pythonw.exe') or (hasattr(sys, 'frozen') and sys.frozen):
    # Already hidden or frozen (e.g., PyInstaller)
    pass
else:
    # Check if script is run directly (not from terminal)
    try:
        # This will fail if run from a terminal
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        
        # Get the console window handle
        hwnd = kernel32.GetConsoleWindow()
        
        # Check if we have a console window
        if hwnd != 0:
            # Check if run from explorer (no parent console process)
            parent_pid = None
            try:
                # This is a simple heuristic - if we can get the parent process ID
                # and it's a cmd.exe or powershell.exe, we're likely in a terminal
                import psutil
                parent_pid = psutil.Process(os.getpid()).parent().name().lower()
                is_terminal = any(term in parent_pid for term in ['cmd.exe', 'powershell.exe', 'pwsh.exe', 'python.exe'])
                
                # Hide console only if not run from terminal
                if not is_terminal:
                    user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
            except (ImportError, psutil.NoSuchProcess, AttributeError):
                # If we can't determine, default to hiding the console
                user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
    except Exception:
        # If anything fails, continue with console visible
        pass

# Suppress specific warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# ============= Constants and Globals =============

# Available Whisper models (fastest to slowest)
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Configuration with defaults
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "model": "tiny",
    "language": "en", 
    "hotkey": {"ctrl": True, "shift": True, "key": "d"},
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
    }
}

# Global variables
config = {}
recording = False
audio_thread = None
stream = None
audio = None
frames = []
indicator = None
settings_window = None
hotkey_pressed = False
hotkey_active = False
last_keydown_time = 0
max_hotkey_duration = 30  # Maximum recording duration in seconds before auto-stop
model = None
model_name = None

# Virtual key codes and Windows constants
VK_CONTROL = 0x11
VK_SHIFT = 0x10
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

# Windows-specific user32.dll functions for keyboard interception
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Define correct argument types for user32 functions
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = (ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.CallNextHookEx.restype = ctypes.c_int
user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint)
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
user32.TranslateMessage.restype = ctypes.c_int
user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
user32.DispatchMessageW.restype = wintypes.LPARAM
user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
user32.GetAsyncKeyState.restype = ctypes.c_short

# Keyboard hook structure
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))
    ]

# Prototype for the hook function
LowLevelKeyboardProc = ctypes.CFUNCTYPE(
    ctypes.c_int,          # Return type
    ctypes.c_int,          # nCode
    wintypes.WPARAM,       # wParam
    wintypes.LPARAM        # lParam
)

# Keep a reference to prevent garbage collection
keyboard_hook = None
keyboard_hook_func = None

# ============= File and Configuration Functions =============

def ensure_directories():
    """Create necessary directories if they don't exist."""
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    return assets_dir

def load_config():
    """Load configuration from config file or create default."""
    global config
    
    config_path = Path(CONFIG_FILE)
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            print(f"✓ Configuration loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"! Error reading config file: {e}")
            config = DEFAULT_CONFIG
            save_config()
    else:
        config = DEFAULT_CONFIG
        save_config()
    
    return config

def save_config():
    """Save current configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"! Error saving config: {e}")

# ============= Audio Functions =============

def get_audio_format():
    """Convert string format from config to PyAudio format constant."""
    format_str = config["audio"]["format"]
    if format_str == "paInt16":
        return pyaudio.paInt16
    elif format_str == "paInt24":
        return pyaudio.paInt24
    elif format_str == "paInt32":
        return pyaudio.paInt32
    elif format_str == "paFloat32":
        return pyaudio.paFloat32
    else:
        return pyaudio.paInt16  # Default

def load_whisper_model():
    """Load the Whisper model specified in the configuration."""
    global model_name
    
    model_name = config.get("model", "tiny")
    print(f"→ Loading Whisper model: {model_name}...")
    
    # Load the model
    loaded_model = whisper.load_model(model_name)
    print(f"✓ Model loaded")
    
    return loaded_model

def record_audio():
    """Records audio while hotkey is held."""
    global recording, frames, stream, audio
    
    # Get audio settings from config
    chunk = config["audio"]["chunk"]
    channels = config["audio"]["channels"]
    rate = config["audio"]["rate"]
    audio_format = get_audio_format()
    
    frames = []  # Reset frames
    
    try:
        # Open audio stream
        stream = audio.open(
            format=audio_format,
            channels=channels,
            rate=rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        # Record audio while the hotkey is pressed
        while recording:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
            except OSError as e:
                print(f"! Audio buffer overflow: {str(e)}")
                time.sleep(0.01)
            
    except Exception as e:
        print(f"! Error during recording: {str(e)}")
    finally:
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                print(f"! Error closing stream: {str(e)}")
                
        if frames:  # Only save and transcribe if we have recorded frames
            assets_dir = ensure_directories()
            audio_file = assets_dir / "dictation.wav"
            
            try:
                # Save audio file
                with wave.open(str(audio_file), "wb") as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(audio_format))
                    wf.setframerate(rate)
                    wf.writeframes(b''.join(frames))
                
                # Start transcription in a separate thread
                threading.Thread(target=transcribe_audio, args=(audio_file,), daemon=True).start()
            except Exception as e:
                print(f"! Error saving audio: {str(e)}")

def transcribe_audio(audio_file):
    """Transcribes the recorded audio and outputs words."""
    global model
    
    try:
        if not os.path.exists(audio_file):
            print(f"! Audio file not found: {audio_file}")
            return
        
        print("→ Transcribing audio...")
        
        # Load the audio file as a numpy array
        with wave.open(str(audio_file), 'rb') as wf:
            audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        
        # Convert to float32 and normalize
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        # Transcribe using the audio data directly
        result = model.transcribe(audio_data, language=config["language"])
        
        transcribed_text = result["text"].strip()
        
        # Copy to clipboard
        pyperclip.copy(transcribed_text)
        
        if transcribed_text:
            # Type the text immediately without word-by-word delay
            print(f"✓ Transcribed: \"{transcribed_text}\"")
            
            # Type all at once - no delays
            keyboard.write(transcribed_text)
        else:
            print("! No speech detected")
            
    except Exception as e:
        print(f"! Error during transcription: {e}")
    finally:
        # Clean up the temporary audio file
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
        except Exception as e:
            print(f"! Error removing temporary file: {e}")

# ============= Recording Control Functions =============

def start_recording():
    """Start the recording process."""
    global recording, audio_thread, hotkey_pressed, last_keydown_time
    
    if not recording:
        recording = True
        hotkey_pressed = True
        last_keydown_time = time.time()
        print("→ Recording... (Release hotkey to stop)")
        indicator.show()
        audio_thread = threading.Thread(target=record_audio, daemon=True)
        audio_thread.start()

def stop_recording():
    """Stop the recording process."""
    global recording, hotkey_pressed
    
    if recording:
        recording = False
        hotkey_pressed = False
        indicator.hide()
        print("✓ Recording stopped")

# ============= Keyboard Hook Functions =============

def keyboard_callback(nCode, wParam, lParam):
    """Low-level keyboard hook callback function."""
    global hotkey_active, recording, last_keydown_time
    
    if nCode >= 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        
        # Get our key configuration
        hotkey_cfg = config["hotkey"]
        
        # Get the current state of CTRL and SHIFT
        ctrl_pressed = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000 != 0
        shift_pressed = user32.GetAsyncKeyState(VK_SHIFT) & 0x8000 != 0
        
        # Convert the configured key to a virtual key code
        target_key_code = ord(hotkey_cfg["key"].upper())
        
        # Detect if this is our hotkey combination
        is_our_hotkey = (
            ((not hotkey_cfg["ctrl"]) or ctrl_pressed) and
            ((not hotkey_cfg["shift"]) or shift_pressed) and
            kb.vkCode == target_key_code
        )
        
        # For key up events, we should check if any of the required keys are released
        is_key_released = (
            (hotkey_cfg["ctrl"] and kb.vkCode == VK_CONTROL and wParam == WM_KEYUP) or
            (hotkey_cfg["shift"] and kb.vkCode == VK_SHIFT and wParam == WM_KEYUP) or
            (kb.vkCode == target_key_code and wParam == WM_KEYUP)
        )
        
        # Handle the key events
        if is_our_hotkey:
            if wParam == WM_KEYDOWN and not hotkey_active:
                # Key down - start recording
                hotkey_active = True
                threading.Thread(target=start_recording, daemon=True).start()
                return -1  # Prevent the key from being processed further
                
            elif wParam == WM_KEYUP and hotkey_active:
                # Key up - stop recording
                hotkey_active = False
                threading.Thread(target=stop_recording, daemon=True).start()
                return -1  # Prevent the key from being processed further
            
            # Block the key if our hotkey is active
            if hotkey_active:
                return -1
        
        # If any part of the hotkey combination is released while recording, stop recording
        elif is_key_released and recording and hotkey_active:
            hotkey_active = False
            threading.Thread(target=stop_recording, daemon=True).start()
            # Let the key event pass through
    
    # Pass the key event to the next hook
    return user32.CallNextHookEx(keyboard_hook, nCode, wParam, lParam)

def setup_keyboard_hook():
    """Set up the low-level keyboard hook."""
    global keyboard_hook, keyboard_hook_func
    
    # Create the hook function
    keyboard_hook_func = LowLevelKeyboardProc(keyboard_callback)
    
    # Register the hook
    keyboard_hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, 
        keyboard_hook_func, 
        None, 
        0
    )
    
    if not keyboard_hook:
        print("! Failed to set keyboard hook")
        error = ctypes.get_last_error()
        print(f"  Error code: {error}")
        return False
    
    print("✓ Keyboard hook installed")
    return True

def remove_keyboard_hook():
    """Remove the keyboard hook when exiting."""
    global keyboard_hook
    
    if keyboard_hook:
        user32.UnhookWindowsHookEx(keyboard_hook)
        keyboard_hook = None

def message_loop():
    """Process Windows messages to keep the hook active."""
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

# ============= UI Components =============

class RecordingIndicator:
    """Visual indicator for recording status."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whisper Dictation")
        self.root.overrideredirect(False)  # Show window frame
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 1.0)  # Make fully opaque
        
        # Create main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)
        
        # Create model selection frame
        model_frame = tk.Frame(self.main_frame)
        model_frame.pack(fill=tk.X, pady=5)
        
        # Add model selection label
        model_label = tk.Label(model_frame, text="Model:")
        model_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add model selection dropdown
        self.model_var = tk.StringVar()
        self.model_var.set(config["model"])
        self.model_dropdown = ttk.Combobox(model_frame, textvariable=self.model_var, 
                                          values=AVAILABLE_MODELS, state="readonly", width=10)
        self.model_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.on_model_change)
        
        # Add status label
        self.status_label = tk.Label(self.main_frame, text="Ready")
        self.status_label.pack(pady=5)
        
        # Get indicator settings
        self.indicator_size = config["ui"]["indicator_size"]
        self.indicator_color = config["ui"]["indicator_color"]
        
        # Create a canvas for the indicator with border
        self.canvas = tk.Canvas(
            self.main_frame, 
            width=self.indicator_size + 4, 
            height=self.indicator_size + 4,
            bg='black', 
            highlightthickness=0
        )
        self.canvas.pack(pady=5)
        
        # Draw the indicator circle
        padding = 2
        self.indicator = self.canvas.create_oval(
            padding, 
            padding, 
            self.indicator_size + padding, 
            self.indicator_size + padding, 
            fill=self.indicator_color, 
            outline='white'
        )
        
        # Add hotkey info label
        hotkey_str = f"{config['hotkey']['ctrl'] and 'Ctrl+' or ''}{config['hotkey']['shift'] and 'Shift+' or ''}{config['hotkey']['key'].upper()}"
        self.hotkey_label = tk.Label(self.main_frame, text=f"Hotkey: {hotkey_str}")
        self.hotkey_label.pack(pady=5)
        
        # Add minimize to tray button
        self.minimize_button = tk.Button(self.main_frame, text="Minimize to Tray", command=self.minimize_to_tray)
        self.minimize_button.pack(pady=5)
        
        # Position in bottom right corner
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 200
        window_height = 200
        self.root.geometry(f'{window_width}x{window_height}+{screen_width - window_width - 20}+{screen_height - window_height - 40}')
        
        # Create system tray icon
        self.create_tray_icon()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Schedule regular updates
        self.update()
        
        # Start with window hidden
        self.root.withdraw()
    
    def create_tray_icon(self):
        """Create a system tray icon."""
        # Create an icon image
        icon_size = 64
        image = Image.new('RGBA', (icon_size, icon_size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a microphone icon (simplified)
        margin = 10
        draw.rectangle(
            [(margin, icon_size//2), (icon_size-margin, icon_size-margin)],
            fill='red', outline='white', width=2
        )
        draw.ellipse(
            [(margin, margin), (icon_size-margin, icon_size//2)],
            fill='red', outline='white', width=2
        )
        
        # Create menu with a default action for left-click
        menu = (
            pystray.MenuItem('Show', self.show_window, default=True),
            pystray.MenuItem('Exit', self.exit_app)
        )
        
        # Create the tray icon
        self.tray_icon = pystray.Icon("whisper_dictation", image, "Whisper Dictation", menu)
        
        # Start the icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window(self, icon=None, item=None):
        """Show the main window from tray."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def minimize_to_tray(self):
        """Minimize the application to system tray."""
        self.root.withdraw()
    
    def exit_app(self, icon=None, item=None):
        """Exit the application."""
        try:
            self.stop_recording()
            self.unhook_keyboard()
            if icon:
                icon.stop()
            self.root.quit()
            self.root.destroy()
            os._exit(0)  # Force terminate the process
        except Exception as e:
            print(f"Error during exit: {e}")
            os._exit(1)  # Force terminate even if there was an error
    
    def on_model_change(self, event):
        """Handle model selection change."""
        new_model = self.model_var.get()
        if new_model != config["model"]:
            # Show loading indicator
            self.status_label.config(text=f"Loading {new_model} model...")
            self.model_dropdown.config(state=tk.DISABLED)
            self.root.update()
            
            # Update config
            config["model"] = new_model
            save_config()
            
            # Load model in background thread
            threading.Thread(target=self.reload_model, daemon=True).start()
    
    def reload_model(self):
        """Reload the Whisper model with the new selection."""
        global model
        try:
            # Load the new model
            model = load_whisper_model()
            
            # Update UI
            self.root.after(0, lambda: self.status_label.config(text="Ready"))
            self.root.after(0, lambda: self.model_dropdown.config(state="readonly"))
        except Exception as e:
            print(f"! Error loading new model: {e}")
            # Revert to previous model
            config["model"] = model_name
            save_config()
            self.root.after(0, lambda: self.model_var.set(model_name))
            self.root.after(0, lambda: self.status_label.config(text="Ready"))
            self.root.after(0, lambda: self.model_dropdown.config(state="readonly"))
    
    def open_settings(self, icon=None, item=None):
        """Open the main window."""
        self.show_window(icon, item)
    
    def show(self):
        """Show the recording indicator."""
        self.canvas.itemconfig(self.indicator, fill="red")
        self.status_label.config(text="Recording...")
    
    def hide(self):
        """Hide the recording indicator."""
        self.canvas.itemconfig(self.indicator, fill=config["ui"]["indicator_color"])
        self.status_label.config(text="Ready")
    
    def update_model_info(self):
        """Update the model info label."""
        self.model_var.set(config["model"])
    
    def update(self):
        """Regular update to keep the window responsive."""
        self.root.after(100, self.update)
    
    def unhook_keyboard(self):
        """Remove the keyboard hook when exiting."""
        remove_keyboard_hook()
        
    def stop_recording(self):
        """Stop the recording process by calling the global stop_recording function."""
        stop_recording()

# ============= Main Function =============

def main():
    """Main application entry point."""
    global config, indicator, model, audio, stream, model_name
    
    # Initialize the configuration
    try:
        load_config()
    except Exception as e:
        print(f"! Error loading configuration: {e}")
        return
    
    # Create or get the data directory
    try:
        ensure_directories()
    except Exception as e:
        print(f"! Error creating directories: {e}")
        return
    
    # Initialize audio
    try:
        audio = pyaudio.PyAudio()
    except Exception as e:
        print(f"! Error initializing audio: {e}")
        return
    
    # Load whisper model
    try:
        model_name = config.get("model", "tiny")
        model = load_whisper_model()
    except Exception as e:
        print(f"! Error loading model: {e}")
        return
    
    # Initialize UI
    try:
        indicator = RecordingIndicator()
    except Exception as e:
        print(f"! Error creating UI: {e}")
        return
    
    # Print app info
    print("\n🎙️  Whisper Dictation")
    print("====================")
    print(f"• Model: {model_name}")
    
    # Set up keyboard hooks
    hook_successful = setup_keyboard_hook()
    
    if hook_successful:
        # Start the message loop to keep the hook active
        message_thread = threading.Thread(target=message_loop, daemon=True)
        message_thread.start()
    else:
        print("! Falling back to keyboard module")
        return
    
    # Show usage instructions
    hotkey_str = f"{config['hotkey']['ctrl'] and 'Ctrl+' or ''}{config['hotkey']['shift'] and 'Shift+' or ''}{config['hotkey']['key']}"
    print(f"• Hotkey: {hotkey_str}")
    print(f"• Config: {CONFIG_FILE}")
    print("• Press Ctrl+C to exit")
    
    # Start the main loop
    try:
        # Create a function to check for timeouts
        def check_timeout():
            if recording and time.time() - last_keydown_time > max_hotkey_duration:
                print(f"! Recording timed out after {max_hotkey_duration}s")
                stop_recording()
            indicator.root.after(1000, check_timeout)
        
        # Start the timeout checker
        indicator.root.after(1000, check_timeout)
        
        # Start the main loop
        indicator.root.mainloop()
    except KeyboardInterrupt:
        print("\n• Whisper Dictation terminated")
    except Exception as e:
        print(f"! Error in main loop: {e}")
    finally:
        # Clean up resources
        remove_keyboard_hook()
        
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
            
        if audio:
            try:
                audio.terminate()
            except:
                pass
            
        if indicator:
            try:
                indicator.root.destroy()
            except:
                pass

if __name__ == "__main__":
    main()
