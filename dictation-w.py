"""
Whisper Dictation - A speech-to-text application using OpenAI's Whisper model
This version hides the console window when run directly
"""
# This is a wrapper script that runs the main dictation.py script using pythonw.exe
# which doesn't show a console window

import os
import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = Path(__file__).parent.absolute()
    
    # Path to the main dictation.py script
    main_script = script_dir / "dictation.py"
    
    # Path to pythonw.exe (same directory as the current Python interpreter)
    python_dir = Path(sys.executable).parent
    pythonw_exe = python_dir / "pythonw.exe"
    
    if not pythonw_exe.exists():
        # Fallback to regular python if pythonw doesn't exist
        pythonw_exe = python_dir / "python.exe"
    
    # Run the main script with pythonw.exe
    subprocess.Popen([str(pythonw_exe), str(main_script)])
