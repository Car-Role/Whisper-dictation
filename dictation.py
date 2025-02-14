import whisper
import pyaudio
import wave
import keyboard
import pyperclip
import time
import threading
import os
import numpy as np
import torch
import tkinter as tk
from tkinter import ttk

# Load Whisper model - using tiny model for speed
print("🔄 Loading Whisper model...")
model = whisper.load_model("tiny")
print("✅ Model loaded!")

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
AUDIO_FILE = "assets/dictation.wav"

# Global state
recording = False
audio_thread = None
stream = None
audio = None
frames = []

class RecordingIndicator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.7)
        
        # Create a small red circle
        self.canvas = tk.Canvas(self.root, width=10, height=10, 
                              bg='black', highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(2, 2, 8, 8, fill='red', outline='red')
        
        # Position in bottom right corner
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f'10x10+{screen_width-20}+{screen_height-40}')
        
        self.root.withdraw()
        
        # Schedule regular updates
        self.update()
    
    def show(self):
        self.root.deiconify()
        self.root.update()
    
    def hide(self):
        self.root.withdraw()
        self.root.update()
    
    def update(self):
        """Regular update to keep the window responsive"""
        self.root.update_idletasks()
        self.root.after(100, self.update)

def record_audio():
    """Records audio while hotkey is held."""
    global recording, frames, stream, audio
    
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                          rate=RATE, input=True,
                          frames_per_buffer=CHUNK)
        
        frames = []
        while recording:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
    except Exception as e:
        print(f"❌ Error during recording: {str(e)}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if audio:
            audio.terminate()
        
        if frames:  # Only save and transcribe if we have recorded frames
            # Save audio file
            with wave.open(AUDIO_FILE, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            # Start transcription in a separate thread
            threading.Thread(target=transcribe_audio, daemon=True).start()

def transcribe_audio():
    """Transcribes the recorded audio and outputs words."""
    try:
        print("📝 Transcribing...")
        
        # Load the audio file as a numpy array
        with wave.open(AUDIO_FILE, 'rb') as wf:
            audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        
        # Convert to float32 and normalize
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        # Transcribe using the audio data directly
        result = model.transcribe(audio_data, language='en')
        
        if result["text"].strip():
            # Split text into words and type them out
            words = result["text"].strip().split()
            for word in words:
                keyboard.write(word + " ")
                time.sleep(0.1)  # Small delay between words
            print("💬 Transcribed:", result["text"].strip())
        else:
            print("❌ No speech detected")
            
    except Exception as e:
        print(f"❌ Error during transcription: {str(e)}")

def on_hotkey_press():
    """Handles hotkey press event."""
    global recording, audio_thread
    if not recording:
        recording = True
        print("🎤 Recording... (Release hotkey to stop)")
        indicator.show()
        audio_thread = threading.Thread(target=record_audio, daemon=True)
        audio_thread.start()

def on_hotkey_release():
    """Handles hotkey release event."""
    global recording
    if recording:
        recording = False
        indicator.hide()
        print("✅ Stopped recording.")

print("\n🎙️  Whisper Dictation")
print("====================")
print("✨ Using 'tiny' model for faster transcription")
print("🔴 Hold 'Ctrl + Shift + D' to dictate. Release to stop recording.")
print("📝 Words will be typed out automatically after processing.")
print("❌ Press 'Ctrl + C' to exit")

# Create the recording indicator
indicator = RecordingIndicator()

# Set up the hotkey
keyboard.on_press_key("d", lambda _: 
    on_hotkey_press() if keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift") else None)
keyboard.on_release_key("d", lambda _: 
    on_hotkey_release() if not keyboard.is_pressed("d") else None)

# Start the main loop
indicator.root.mainloop()
