Mochi AI Deskmate

An AI-powered desktop companion integrating Arduino hardware with Python-based AI processing. Features touch-sensor navigation, OLED feedback, and real-time environmental monitoring.

Setup Instructions

1. Hardware
Read connections.txt to understand how to connect your DeskMate components on a breadboard.

2. Firmware
Upload new_ai_mochi.ino to your Arduino board.

3. Software
Download mochi_stream.py.

Open the file in your favorite IDE.

Locate the api_key variable (in line 50) and replace the placeholder with your own Groq API key:

Python
# Replace with your own key!

api_key = "YOUR_GROQ_API_KEY_HERE"

Run the script in your terminal to begin the AI stream.
