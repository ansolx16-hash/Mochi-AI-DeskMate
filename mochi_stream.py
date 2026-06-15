import time
import os
import random
import serial
import pyautogui
import pygetwindow as gw
import threading
import textwrap
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr
import urllib.request
import urllib.parse
import re
import psutil
import pyttsx3
import json
import webbrowser
import tkinter as tk  # Native UI overlay for typing mode
from youtubesearchpython import VideosSearch
from groq import Groq
from PIL import Image, ImageSequence, ImageDraw, ImageFont
from pynput import keyboard
from collections import deque
from datetime import datetime
from ddgs import DDGS
# from mochi_vault import MochiVault

# =========================================================
# CONFIG & API
# =========================================================

SERIAL_PORT = 'COM6'
BAUD_RATE = 250000

GIF_FOLDER = r"where ever you saved the folder named Dasai in your pc"
EMOJI_SPRITE_FOLDER = r"whatever you want, this is bloatware not needed at all"

BOOT_GIF = "boot.gif"
LOVE_GIF = "love.gif"
INTERSTELLAR_GIF = "interstellar.gif"
IDLE_GIF = "sleepy1.gif"
ACTIVE_GIF = "active.gif"

IDLE_TIMEOUT = 300

# Groq Setup
client = Groq(
    api_key="enter your groq api key here")

# Chat History Memory Configuration
MEMORY_FILE = "memory.json"
conversation_history = []

# =========================================================
# BULLETPROOF MEMORY MANAGER & COMPRESSION PIPELINE
# =========================================================


def update_memory(new_entries):
    if not isinstance(new_entries, list):
        new_entries = [new_entries]

    if os.path.exists("memory.json") and os.path.getsize("memory.json") > 1073741824:
        os.remove("memory.json")

    history = []
    if os.path.exists("memory.json"):
        with open("memory.json", "r") as f:
            try:
                loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    history = loaded_data
            except:
                history = []

    for entry in new_entries:
        if isinstance(entry, dict) and "role" in entry and "content" in entry:
            history.append({
                "role": str(entry["role"]),
                "content": str(entry["content"]),
                "timestamp": entry.get("timestamp", datetime.now().isoformat())
            })

    try:
        with open("memory.json", "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Failed to write memory file: {e}")

    return history


def process_cleanup_chunk(entries_chunk):
    if not entries_chunk:
        return []

    prompt = (
        "You are an elite memory-optimization routine for an AI companion named Mochi.\n"
        "Analyze the following list of conversation objects. For EACH object, determine if it is "
        "'High Quality' (contains explicit user specifications, hardware context, custom preferences, plans, names, or critical files) "
        "or 'Low Quality' (generic greetings like 'hi', short replies like 'ok', basic filler chit-chat, or repetitive insults).\n\n"
        "Return a JSON object containing a key called 'processed_entries' which maps to an array of objects. "
        "Each object in the array MUST contain:\n"
        "- 'keep': true (for High Quality) or false (for Low Quality)\n"
        "- 'role': matching the original item's role\n"
        "- 'content': if kept, condense it down to only the absolute essential facts. If dropped, keep it empty.\n"
        "- 'timestamp': matching the original timestamp\n"
        "- 'quality_label': string 'High Quality' or 'Low Quality'\n\n"
        f"Data to evaluate:\n{json.dumps(entries_chunk)}"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        response_text = chat_completion.choices[0].message.content
        data = json.loads(response_text)

        if "processed_entries" in data:
            data = data["processed_entries"]

        cleaned_results = []
        if isinstance(data, list):
            for item in data:
                quality = item.get("quality_label", "Unknown Quality")
                content_preview = item.get("content", "")[:30]
                print(
                    f"[Memory Diagnostics] Entry labeled as: {quality} -> Keep Status: {item.get('keep')} ({content_preview}...)")

                if item.get("keep") is True:
                    cleaned_results.append({
                        "role": item.get("role", "user"),
                        "content": item.get("content", ""),
                        "timestamp": item.get("timestamp", datetime.now().isoformat())
                    })
            return cleaned_results
    except Exception as e:
        print(f"Error during memory chunk analysis execution: {e}")

    return entries_chunk


def optimize_and_clean_memory_file():
    while True:
        try:
            if not os.path.exists("memory.json"):
                time.sleep(3600)
                continue

            print("[Memory Diagnostics] Initializing dynamic maintenance scans...")
            with open("memory.json", "r") as f:
                history = json.load(f)

            if not isinstance(history, list) or not history:
                time.sleep(3600)
                continue

            now = datetime.now()
            old_entries = []
            new_entries = []

            for entry in history:
                ts_str = entry.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if (now - ts).days >= 5:
                            old_entries.append(entry)
                        else:
                            new_entries.append(entry)
                    except:
                        new_entries.append(entry)
                else:
                    entry["timestamp"] = now.isoformat()
                    new_entries.append(entry)

            if not old_entries:
                print(
                    "[Memory Diagnostics] Maintenance check complete. No entries are older than 5 days.")
                time.sleep(3600)
                continue

            estimated_credits = len(json.dumps(old_entries)) / 3.6
            print(
                f"[Memory Diagnostics] Found old entries. Estimated credit consumption size: {estimated_credits:.1f} credits.")

            processed_old = []
            if estimated_credits > 500:
                print(
                    "[Memory Diagnostics] Warning: Chunk size > 500 credits limit! Splitting cleanly into half routines...")
                mid_idx = len(old_entries) // 2
                first_half = old_entries[:mid_idx]
                second_half = old_entries[mid_idx:]

                print("[Memory Diagnostics] Processing First Half...")
                processed_old.extend(process_cleanup_chunk(first_half))
                print("[Memory Diagnostics] Processing Second Half...")
                processed_old.extend(process_cleanup_chunk(second_half))
            else:
                processed_old.extend(process_cleanup_chunk(old_entries))

            optimized_history = processed_old + new_entries
            with open("memory.json", "w") as f:
                json.dump(optimized_history, f, indent=2)
            print("[Memory Diagnostics] Optimization complete. Low quality items discarded, high quality data retained safely.")

        except Exception as e:
            print(f"[Memory Daemon Error] {e}")

        time.sleep(3600)

# =========================================================
# SERIAL CONNECTION
# =========================================================


try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.5)
    time.sleep(2)
    ser.reset_input_buffer()
    print("Connected! Mochi Engine Active...")
except Exception as e:
    print(f"Error: {e}")
    exit()

# =========================================================
# STATES & FLAGS
# =========================================================

is_holding_vol_up = False
is_holding_vol_down = False
last_volume_tick = 0
VOLUME_SPEED = 0.07

head_press_start_time = 0
is_holding_head = False
show_clock_mode = False

tap_count = 0
last_tap_time = 0

special_mode = None
special_mode_end = 0

last_activity_time = time.time()
just_woke_up = False
force_next_gif = False
currently_snoring = False

keypress_timestamps = deque()
current_wpm = 0
wpm_lock = threading.Lock()

nightmare_triggered = False

last_youtube_title = ""
show_yt_title_mode = False
yt_title_start_time = 0
current_yt_title = ""
current_yt_channel = ""
last_window_check_time = 0

# --- AI & VOICE VARS ---
ai_mode = False
ai_state = None
ai_text_lines = []
ai_display_start_time = 0.0
ai_speech_duration = 0.0
raw_ai_display_text = ""

is_recording = False
audio_frames = []
audio_stream = None

# --- DARK MODE STATE ---
dark_mode_active = False

# --- MOCHIVAULT & PRODUCTIVITY NUDGE ---
vault = None
nudge_lines = []
nudge_until = 0.0
nudge_lock = threading.Lock()
last_nudge_check = 0.0

# =========================================================
# LIVE SEARCH & AUTOMATION HELPERS
# =========================================================


def get_live_info(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if results:
                return "\n".join([r.get('body', '') for r in results])
    except Exception as e:
        print(f"Search failed: {e}")
    return ""


def get_system_stats():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    return f"CPU: {cpu}%, RAM: {ram}%"


def execute_youtube_action(query, auto_play=False):
    safe_query = urllib.parse.quote(query)

    if auto_play:
        print(
            f"Bypassing libraries - Scraping YouTube directly for: {query}...")
        try:
            url = f"https://www.youtube.com/results?search_query={safe_query}"
            req = urllib.request.Request(
                url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

            with urllib.request.urlopen(req) as response:
                html = response.read().decode()
                video_ids = re.findall(r"watch\?v=(\S{11})", html)

                if video_ids:
                    first_video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                    print(f"Success! Playing video link: {first_video_url}")
                    webbrowser.open(first_video_url)
                    return
                else:
                    print("No video IDs found in HTML, falling back to search page.")
        except Exception as e:
            print(
                f"Direct scrape failed: {e}. Falling back to normal search...")

    print(f"Opening YouTube search layout for: {query}")
    search_url = f"https://www.youtube.com/results?search_query={safe_query}"
    webbrowser.open(search_url)


def perform_search(query):
    print(f"Searching web for: {query}...")
    search_url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
    os.system(f'start "" brave "{search_url}"')

# =========================================================
# TEXT PROMPT EXECUTION PIPELINE
# =========================================================


def evaluate_single_input_quality(user_text):
    test_entry = [{
        "role": "user",
        "content": str(user_text),
        "timestamp": datetime.now().isoformat()
    }]

    prompt = (
        "You are an elite memory-optimization routine for an AI companion named Mochi.\n"
        "Analyze the following user input object. Determine if it is "
        "'High Quality' (contains explicit user specifications, hardware context, custom preferences, plans, names, or critical files) "
        "or 'Low Quality' (generic greetings like 'hi', short replies like 'ok', basic filler chit-chat, or repetitive insults).\n\n"
        "Return a JSON object containing:\n"
        "- 'keep': true (for High Quality) or false (for Low Quality)\n"
        "- 'quality_label': string 'High Quality' or 'Low Quality'\n\n"
        f"Data to evaluate:\n{json.dumps(test_entry)}"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(chat_completion.choices[0].message.content)
        return data.get("quality_label", "Unknown Quality"), data.get("keep", True)
    except Exception as e:
        print(f"[Live Memory Monitor] Quality evaluation error: {e}")
        return "Evaluation Failed (Defaulting to Keep)", True


def check_search_necessity_intent(user_text):
    router_prompt = (
        "You are an elite intent-routing system. Analyze the user request.\n"
        "Determine if answering this question accurately requires fresh, real-time web information "
        "(e.g., current weather, sports scores, news events, upcoming movie release dates, "
        "current prices, or active real-world statistics).\n\n"
        "Return ONLY the word 'TRUE' if it needs a live web search, or 'FALSE' if it can be "
        "answered directly using standard internal AI training data (general coding, historical facts, "
        "casual conversations, or roleplay).\n"
        "Do not include any punctuation, explanation, or extra characters."
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": router_prompt},
                {"role": "user", "content": f"Request: {user_text}"}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=5
        )
        decision = response.choices[0].message.content.strip().upper()
        return "TRUE" in decision
    except Exception as e:
        print(f"[Router Engine Error] Defaulting to local: {e}")
        return False


def submit_text_prompt_to_ai(raw_user_text):
    global ai_mode, ai_state
    if not raw_user_text.strip():
        ai_mode = False
        return

    ai_mode = True
    ai_state = "THINKING"

    print("\n" + "="*50)
    print(f"[Live Memory Monitor] Analyzing input: \"{raw_user_text}\"")

    quality_label, should_keep = evaluate_single_input_quality(raw_user_text)

    print(f"[Live Memory Monitor] Classification -> {quality_label}")
    if should_keep:
        print(
            "[Live Memory Monitor] Action -> COMMIT: This entry is being added to memory.json")
    else:
        print("[Live Memory Monitor] Action -> DISCARD: Low quality chat detected. Skipping memory.json storage.")
    print("="*50 + "\n")

    threading.Thread(
        target=run_ai_generation_engine,
        args=(raw_user_text, should_keep),
        daemon=True
    ).start()


def run_ai_generation_engine(user_text, should_save_to_memory=True):
    global ai_mode, ai_state, ai_text_lines, ai_display_start_time, ai_speech_duration, conversation_history, raw_ai_display_text
    try:
        print(f"You typed/said: {user_text}")

        history_buffer = []
        if os.path.exists("memory.json"):
            with open("memory.json", "r") as f:
                try:
                    history_buffer = json.load(f)
                except:
                    pass

        if should_save_to_memory:
            conversation_history = update_memory(
                [{"role": "user", "content": str(user_text)}])
        else:
            conversation_history = history_buffer + [{
                "role": "user",
                "content": str(user_text),
                "timestamp": datetime.now().isoformat()
            }]

        trigger_keywords = ["play", "search", "youtube", "yt", "find", "watch"]
        user_requested_action = any(word in user_text.lower()
                                    for word in trigger_keywords)

        injected_context = ""

        stat_triggers = ["stats", "cpu", "ram", "health", "system"]
        if any(word in user_text.lower() for word in stat_triggers):
            sys_info = get_system_stats()
            injected_context += f" [System Hardware Context: {sys_info}]"

        needs_web_search = check_search_necessity_intent(user_text)

        if needs_web_search:
            print(
                f"[Mochi Router] Intent identified: Dynamic Search triggered for '{user_text}'")
            live_data = get_live_info(user_text)
            if live_data:
                injected_context += f" [Live DuckDuckGo Web Context: {live_data}]"
        else:
            print("[Mochi Router] Intent identified: Conversational/Local processing.")

        system_prompt = (
            "CRITICAL: You are Mochi, a super insanely polite AI who will do anything for his creator AKA the user "
            "1. ONLY use search tags (PLAY_YT:, SEARCH_YT:, SEARCH:) IF the user explicitly asked for them. "
            "2. If the user is just chatting ('sup', 'hello'), NEVER include search tags. "
            "3. If the user did not ask for a search, do not try to search. "
            "4. be very polite and act very human"
        )

        messages = [{"role": "system", "content": system_prompt}
                    ] + conversation_history

        if injected_context:
            messages[-1]["content"] += injected_context

        sanitized_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        chat_completion = client.chat.completions.create(
            messages=sanitized_messages,
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content

        if user_requested_action:
            if "PLAY_YT:" in response_text:
                video_query = response_text.split("PLAY_YT:")[1].strip()
                execute_youtube_action(video_query, auto_play=True)
                response_text = response_text.replace("PLAY_YT:", "").strip()
            elif "SEARCH_YT:" in response_text:
                search_query = response_text.split("SEARCH_YT:")[1].strip()
                execute_youtube_action(search_query, auto_play=False)
                response_text = response_text.replace("SEARCH_YT:", "").strip()
            elif "SEARCH:" in response_text:
                search_query = response_text.split("SEARCH:")[1].strip()
                perform_search(search_query)
                response_text = response_text.replace("SEARCH:", "").strip()
        else:
            response_text = response_text.replace("PLAY_YT:", "").replace(
                "SEARCH_YT:", "").replace("SEARCH:", "").strip()

        print(f"Mochi: {response_text}")

        if should_save_to_memory:
            conversation_history = update_memory(
                [{"role": "assistant", "content": str(response_text)}])
        else:
            conversation_history.append({
                "role": "assistant",
                "content": str(response_text),
                "timestamp": datetime.now().isoformat()
            })

        word_count = max(1, len(response_text.split()))
        ai_speech_duration = (word_count / 3.0) + 0.5

        # IMPORTANT: Set state global context FIRST before speaking thread fires up
        raw_ai_display_text = response_text
        ai_display_start_time = time.time()
        ai_state = "DISPLAYING"

        threading.Thread(target=speak_thread_safe, args=(
            response_text,), daemon=True).start()

    except Exception as e:
        print(f"AI Matrix Error: {e}")
        raw_ai_display_text = "Connection Error!"
        ai_speech_duration = 2.0
        ai_display_start_time = time.time()
        ai_state = "DISPLAYING"
        threading.Thread(target=speak_thread_safe, args=(
            "Connection error.",), daemon=True).start()

# =========================================================
# NON-BLOCKING TYPING OVERLAY TETHER
# =========================================================


def _tkinter_worker_process():
    global ai_mode

    def on_submit(event=None):
        text_payload = entry_box.get()
        root.destroy()
        if text_payload.strip():
            submit_text_prompt_to_ai(text_payload)
        else:
            global ai_mode
            ai_mode = False

    root = tk.Tk()
    root.title("Talk to Mochi")
    root.attributes("-topmost", True)
    root.geometry("400x100+450+300")
    root.configure(bg="#1e1e2e")

    label = tk.Label(root, text="Type your message to Mochi:",
                     fg="#cdd6f4", bg="#1e1e2e", font=("Arial", 11, "bold"))
    label.pack(pady=5)

    entry_box = tk.Entry(root, width=45, bg="#313244", fg="#a6e3a1",
                         insertbackground="white", font=("Arial", 11))
    entry_box.pack(pady=5)
    entry_box.focus_set()

    entry_box.bind("<Return>", on_submit)

    def on_close():
        global ai_mode
        ai_mode = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def open_typing_overlay_window():
    threading.Thread(target=_tkinter_worker_process, daemon=True).start()

# =========================================================
# AUDIO RECORDING PIPELINE
# =========================================================


def speak_thread_safe(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.stop()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"TTS Error: {e}")


def productivity_nudge_daemon():
    global nudge_lines, nudge_until, last_nudge_check
    while True:
        try:
            time.sleep(45)
            if vault is None or vault.active:
                continue
            if ai_mode:
                continue
            app = get_active_app_mode()
            if app not in ("youtube",) and "spotify" not in str(app).lower():
                try:
                    w = gw.getActiveWindow()
                    if not w or not w.title:
                        continue
                    title = w.title.lower()
                    if not any(x in title for x in ("youtube", "spotify", "music", "netflix", "twitch")):
                        continue
                except Exception:
                    continue
            msg = vault.productivity_nudge()
            if not msg:
                continue
            pyautogui.press('space')
            with nudge_lock:
                nudge_lines = textwrap.wrap(msg, width=21)
                nudge_until = time.time() + 8
            threading.Thread(target=speak_thread_safe,
                             args=(msg,), daemon=True).start()
            print(f"[Mochi Nudge] {msg}")
        except Exception as e:
            print(f"[Nudge Error] {e}")


def audio_callback(indata, frames, time, status):
    if is_recording:
        audio_frames.append(indata.copy())


def start_recording():
    global audio_frames, is_recording, audio_stream
    audio_frames.clear()
    is_recording = True
    print("Mic Stream Opened Cleanly.")
    try:
        audio_stream = sd.InputStream(
            samplerate=16000, channels=1, dtype='int16', callback=audio_callback)
        audio_stream.start()
    except Exception as e:
        print(f"Failed to open hardware microphone: {e}")


def stop_recording():
    global is_recording, audio_stream
    is_recording = False
    print("Mic Stream Closed Safely.")
    if audio_stream:
        try:
            audio_stream.stop()
            audio_stream.close()
        except Exception as e:
            print(f"Failed to close hardware microphone safely: {e}")
        audio_stream = None


def process_voice_thread():
    global ai_mode, ai_state, ai_text_lines, ai_display_start_time, ai_speech_duration
    ai_state = "THINKING"

    if not audio_frames:
        ai_mode = False
        return

    try:
        audio_data = np.concatenate(audio_frames, axis=0)
        if audio_data.size > 0:
            peak = np.max(np.abs(audio_data))
            if peak > 0 and peak < 20000:
                scale_factor = 28000.0 / peak
                audio_data = (audio_data * scale_factor).astype(np.int16)

        wav.write("temp_voice.wav", 16000, audio_data)
    except Exception as e:
        print(f"Audio compilation error: {e}")
        ai_mode = False
        return

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 150
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    with sr.AudioFile("temp_voice.wav") as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio_val = recognizer.record(source)
            user_text = recognizer.recognize_google(audio_val)
            run_ai_generation_engine(user_text)
        except sr.UnknownValueError:
            global raw_ai_display_text
            raw_ai_display_text = "I didn't quite catch that..."
            ai_speech_duration = 2.0
            ai_display_start_time = time.time()
            ai_state = "DISPLAYING"
            threading.Thread(target=speak_thread_safe, args=(
                "I didn't quite catch that.",), daemon=True).start()

# =========================================================
# KEYBOARD LISTENER
# =========================================================


def on_press(key):
    global keypress_timestamps, last_activity_time, just_woke_up, force_next_gif
    now = time.time()
    if now - last_activity_time > IDLE_TIMEOUT:
        just_woke_up = True
        force_next_gif = True
    last_activity_time = now

    if vault and getattr(vault, 'active', False):
        try:
            vault._on_key_press(key)
        except Exception as e:
            print(f"Vault Key Routing Error: {e}")

    if key == keyboard.Key.space:
        with wpm_lock:
            keypress_timestamps.append(now)


listener = keyboard.Listener(on_press=on_press)
listener.start()


def calculate_wpm():
    global keypress_timestamps, current_wpm
    now = time.time()
    with wpm_lock:
        while keypress_timestamps and now - keypress_timestamps[0] > 5.0:
            keypress_timestamps.popleft()
        total_clicks = len(keypress_timestamps)
    if total_clicks > 0:
        current_wpm = int((total_clicks / 5) * 12)
    else:
        current_wpm = 0

# =========================================================
# HELPERS & SERIAL BYTES HANDLER
# =========================================================


def get_all_gifs():
    try:
        files = os.listdir(GIF_FOLDER)
        return [f for f in files if f.lower().endswith('.gif')]
    except Exception as e:
        return []


def get_active_app_mode():
    try:
        active_window = gw.getActiveWindow()
        if active_window and active_window.title:
            title = active_window.title.lower()
            if any(browser in title for browser in ["chrome", "firefox", "brave", "edge"]):
                if "youtube" in title:
                    return "youtube"
    except Exception:
        pass
    return "global"


def get_youtube_info():
    try:
        active_window = gw.getActiveWindow()
        if active_window and active_window.title:
            title = active_window.title
            if " - YouTube" in title:
                clean_title = title.replace(" - Google Chrome", "").replace(" - Brave", "").replace(
                    " - Mozilla Firefox", "").replace(" - Microsoft Edge", "").replace(" - YouTube", "")
                if " - " in clean_title:
                    parts = clean_title.rsplit(" - ", 1)
                    return parts[0][:50], parts[1][:20]
                return clean_title[:50], "YouTube"
    except Exception:
        pass
    return None, None


def handle_serial_bytes(cmd_byte):
    global is_holding_vol_up, is_holding_vol_down
    global head_press_start_time, is_holding_head, show_clock_mode
    global tap_count, last_tap_time
    global special_mode, special_mode_end, force_next_gif
    global ai_mode, ai_state, is_recording, audio_frames
    global dark_mode_active

    if vault and vault.active:
        if vault.handle_touch(cmd_byte, None):
            return

    app_mode = get_active_app_mode()

    if cmd_byte == b'F':
        print("Double-tap: Opening MochiVault...")
        stop_recording()
        ai_mode = False
        if vault:
            vault.open_vault()
        return

    if cmd_byte == b'P':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        if ai_mode:
            ai_mode = False
            return
        current_time = time.time()
        if current_time - last_tap_time > 1.2:
            tap_count = 0
        tap_count += 1
        last_tap_time = current_time

        if tap_count == 3:
            special_mode = "love"
            special_mode_end = time.time() + 10
            force_next_gif = True
            tap_count = 0
        elif tap_count == 5:
            special_mode = "interstellar"
            special_mode_end = time.time() + 18
            force_next_gif = True
            tap_count = 0

        if not is_holding_head:
            head_press_start_time = time.time()
            is_holding_head = True

    elif cmd_byte == b'p':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        if is_holding_head:
            if not show_clock_mode and (time.time() - head_press_start_time) < 2.0:
                if app_mode in ["youtube", "spotify"]:
                    pyautogui.press('space')
                else:
                    pyautogui.press('playpause')
        is_holding_head = False
        show_clock_mode = False

    elif cmd_byte == b'N':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        if app_mode == "youtube":
            pyautogui.hotkey('shift', 'n')
        elif app_mode == "spotify":
            pyautogui.hotkey('ctrl', 'right')
        else:
            pyautogui.press('nexttrack')

    elif cmd_byte == b'B':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        if app_mode == "youtube":
            pyautogui.hotkey('shift', 'p')
        elif app_mode == "spotify":
            pyautogui.hotkey('ctrl', 'left')
        else:
            pyautogui.press('prevtrack')

    elif cmd_byte == b'R':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        is_holding_vol_up = True
    elif cmd_byte == b'r':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        is_holding_vol_up = False
    elif cmd_byte == b'L':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        is_holding_vol_down = True
    elif cmd_byte == b'l':
        if vault and vault.active:
            vault.handle_touch(cmd_byte, None)
            return
        is_holding_vol_down = False

    elif cmd_byte == b'K':
        print("Arduino triggered Typing Mode! Launching isolated keyboard window...")
        stop_recording()
        ai_mode = True
        ai_state = "TYPING"
        open_typing_overlay_window()

    elif cmd_byte == b'V':
        ai_mode = True
        ai_state = "LISTENING"
        start_recording()
        print("Mochi is listening to your voice...")

    elif cmd_byte == b'v':
        if is_recording and ai_state == "LISTENING":
            stop_recording()
            print("Mochi stopped listening. Processing speech stream...")
            threading.Thread(target=process_voice_thread, daemon=True).start()
        else:
            stop_recording()

    elif cmd_byte == b'D':
        dark_mode_active = True
    elif cmd_byte == b'd':
        dark_mode_active = False


def process_background_volume():
    global last_volume_tick
    current_time = time.time()

    if ai_mode and ai_state == "DISPLAYING":
        return

    if is_holding_vol_up and (current_time - last_volume_tick) > VOLUME_SPEED:
        pyautogui.press('volumeup')
        last_volume_tick = current_time
    if is_holding_vol_down and (current_time - last_volume_tick) > VOLUME_SPEED:
        pyautogui.press('volumedown')
        last_volume_tick = current_time


def volume_background_worker():
    while True:
        process_background_volume()
        time.sleep(0.01)

# =========================================================
# HYBRID CHUNKED-HANDSHAKE TRANSMITTER
# =========================================================


def send_oled_frame(buffer, is_text_mode=False):
    try:
        ser.write(b'\x01')
        for i in range(0, 1024, 32):
            ser.write(buffer[i:i+32])
            time.sleep(0.0008)

        ser.flush()

        start_wait = time.time()
        while True:
            if ser.in_waiting > 0:
                rx_byte = ser.read(1)
                if rx_byte == b'Y':
                    break
                else:
                    handle_serial_bytes(rx_byte)
            else:
                time.sleep(0.001)

            if time.time() - start_wait > 0.4:
                break

        if is_text_mode:
            # Cut timing window slightly to drop serial collision risks
            time.sleep(0.03)

    except Exception as e:
        print(f"Serial Frame Sync Error: {e}")

# =========================================================
# MAIN EMOJI TEXT LAYOUT ENGINE
# =========================================================


def layout_emoji_text(text, font, max_width=124, emoji_size=12):
    if not text:
        return []
    tokens = re.findall(r'[a-zA-Z0-9[:punct:]]+|\s+|[^\x00-\x7F]', text)

    lines = []
    current_line = []
    current_x = 0

    for token in tokens:
        is_emoji = bool(re.match(r'[^\x00-\x7F]', token))

        if is_emoji:
            token_width = emoji_size + 2
        else:
            token_width = int(ImageDraw.Draw(
                Image.new('1', (1, 1))).textlength(token, font=font))

        if current_x + token_width > max_width and token != ' ':
            if current_line:
                lines.append((current_line, current_x))
            current_line = []
            current_x = 0
            if token == ' ':
                continue

        current_line.append(
            {'text': token, 'is_emoji': is_emoji, 'width': token_width})
        current_x += token_width

    if current_line:
        lines.append((current_line, current_x))

    return lines

# =========================================================
# MAIN STREAM ENGINE
# =========================================================


def stream_gif():
    global is_holding_head, show_clock_mode
    global special_mode, special_mode_end
    global nightmare_triggered, just_woke_up, force_next_gif, currently_snoring
    global last_youtube_title, show_yt_title_mode, yt_title_start_time
    global current_yt_title, current_yt_channel, last_window_check_time
    global ai_mode, ai_state, raw_ai_display_text
    global dark_mode_active
    global nudge_lines, nudge_until

    blocky_font = ImageFont.load_default()
    is_booting = True
    SYSTEM_GIFS = [LOVE_GIF, INTERSTELLAR_GIF, BOOT_GIF, IDLE_GIF, ACTIVE_GIF]

    while True:
        all_gifs = get_all_gifs()
        if not all_gifs:
            time.sleep(5)
            continue

        time_since_last_key = time.time() - last_activity_time

        if vault and vault.active:
            vault.tick()
            frame_clean = vault.render_frame(blocky_font)
            if dark_mode_active:
                frame_clean = frame_clean.point(
                    lambda x: 0 if x > 0 else 255, mode='1')
            pixels = frame_clean.load()
            buffer = bytearray(1024)
            for page in range(8):
                for x in range(128):
                    byte = 0
                    for bit in range(8):
                        if pixels[x, page * 8 + bit] > 0:
                            byte |= (1 << bit)
                    buffer[page * 128 + x] = byte
            send_oled_frame(buffer, is_text_mode=True)
            time.sleep(0.022 if vault.needs_fast_refresh() else 0.035)
            continue

        with nudge_lock:
            nudge_active = nudge_lines and time.time() < nudge_until
            active_nudge = list(nudge_lines) if nudge_active else []

        if nudge_active:
            frame_clean = Image.new('1', (128, 64), 0)
            draw = ImageDraw.Draw(frame_clean)
            now_time = datetime.now()
            t = now_time.strftime("%I:%M %p").lstrip("0")
            d = now_time.strftime("%a %b %d")
            draw.text((0, 0), t, font=blocky_font, fill=255)
            draw.text((68, 0), d, font=blocky_font, fill=255)
            draw.line((0, 9, 127, 9), fill=255)
            draw.text((2, 12), "MOCHI INTERRUPT", font=blocky_font, fill=255)
            for i, ln in enumerate(active_nudge[:4]):
                draw.text((2, 22 + i * 9), ln, font=blocky_font, fill=255)
            if dark_mode_active:
                frame_clean = frame_clean.point(
                    lambda x: 0 if x > 0 else 255, mode='1')
            pixels = frame_clean.load()
            buffer = bytearray(1024)
            for page in range(8):
                for x in range(128):
                    byte = 0
                    for bit in range(8):
                        if pixels[x, page * 8 + bit] > 0:
                            byte |= (1 << bit)
                    buffer[page * 128 + x] = byte
            send_oled_frame(buffer, is_text_mode=True)
            continue

        if is_booting:
            chosen_gif_name = BOOT_GIF
        elif special_mode == "love":
            chosen_gif_name = LOVE_GIF
            if time.time() > special_mode_end:
                special_mode = None
        elif special_mode == "interstellar":
            chosen_gif_name = INTERSTELLAR_GIF
            if time.time() > special_mode_end:
                special_mode = None
        elif time_since_last_key > IDLE_TIMEOUT:
            chosen_gif_name = IDLE_GIF
            if not currently_snoring:
                ser.write(b'S')
                currently_snoring = True
        elif just_woke_up:
            chosen_gif_name = ACTIVE_GIF
            if currently_snoring:
                ser.write(b'W')
                currently_snoring = False
        else:
            normal_gifs = [gif for gif in all_gifs if gif not in SYSTEM_GIFS]
            chosen_gif_name = random.choice(
                normal_gifs) if normal_gifs else ACTIVE_GIF

        full_gif_path = os.path.join(GIF_FOLDER, chosen_gif_name)
        try:
            with Image.open(full_gif_path) as img:
                for frame in ImageSequence.Iterator(img):
                    current_time = time.time()

                    if current_time - last_window_check_time > 1.5:
                        yt_title, yt_channel = get_youtube_info()
                        if yt_title and yt_title != last_youtube_title:
                            last_youtube_title = yt_title
                            current_yt_title = yt_title
                            current_yt_channel = yt_channel
                            show_yt_title_mode = True
                            yt_title_start_time = current_time
                        last_window_check_time = current_time

                    if show_yt_title_mode and (current_time - yt_title_start_time > 8.0):
                        show_yt_title_mode = False

                    if force_next_gif:
                        force_next_gif = False
                        break

                    if current_time - last_activity_time > IDLE_TIMEOUT and chosen_gif_name != IDLE_GIF:
                        break

                    now_time = datetime.now()
                    if now_time.hour == 22 and now_time.minute == 0:
                        if not nightmare_triggered:
                            ser.write(b'E')
                            nightmare_triggered = True
                            time.sleep(1)
                            ser.reset_input_buffer()
                            break
                    else:
                        nightmare_triggered = False

                    calculate_wpm()

                    if is_holding_head and not show_clock_mode:
                        if (current_time - head_press_start_time) >= 0.8:
                            show_clock_mode = True

                    # --- UI RENDERING MODES ---
                    is_text_active = False

                    if ai_mode:
                        is_text_active = True
                        frame_clean = Image.new('1', (128, 64), 0)
                        draw = ImageDraw.Draw(frame_clean)
                        if ai_state == "LISTENING":
                            draw.text((32, 28), "Listening...",
                                      font=blocky_font, fill=255)
                        elif ai_state == "TYPING":
                            draw.text((28, 28), "Keyboard Mode",
                                      font=blocky_font, fill=255)
                        elif ai_state == "THINKING":
                            draw.text((36, 28), "Thinking...",
                                      font=blocky_font, fill=255)
                        elif ai_state == "DISPLAYING":
                            # Secure a reliable fallback string if the text didn't pass properly
                            text_to_render = raw_ai_display_text if raw_ai_display_text else "..."

                            # Layout the text wrap frames
                            structured_lines = layout_emoji_text(
                                text_to_render, blocky_font, max_width=124)

                            # Force text to stay statically on screen instead of relying on fragile elapsed time equations
                            line_height = 10
                            y_start = 2  # Start high up so multiple lines fit comfortably

                            for row_idx, (line_tokens, line_w) in enumerate(structured_lines):
                                y_pos = y_start + (row_idx * line_height)

                                # Prevent array index out of bounds on screen height
                                if y_pos > 54:
                                    break

                                x_cursor = 2
                                for token in line_tokens:
                                    if token['is_emoji']:
                                        emoji_char = token['text']
                                        sprite_path = os.path.join(
                                            EMOJI_SPRITE_FOLDER, f"{emoji_char}.png")

                                        if os.path.exists(sprite_path):
                                            try:
                                                with Image.open(sprite_path) as emoji_img:
                                                    emoji_mono = emoji_img.resize(
                                                        (10, 10)).convert('1')
                                                    frame_clean.paste(
                                                        emoji_mono, (x_cursor, y_pos + 1))
                                            except Exception:
                                                pass
                                        else:
                                            draw.rectangle(
                                                [x_cursor, y_pos + 1, x_cursor + 9, y_pos + 10], outline=255, fill=0)
                                    else:
                                        draw.text(
                                            (x_cursor, y_pos), token['text'], font=blocky_font, fill=255)

                                    x_cursor += token['width']

                            # Keep text on screen during the estimated speech duration plus a 3-second reading buffer
                            elapsed = current_time - ai_display_start_time
                            if elapsed > (ai_speech_duration + 3.0):
                                ai_mode = False

                    elif show_clock_mode:
                        frame_clean = Image.new('1', (128, 64), 0)
                        draw = ImageDraw.Draw(frame_clean)
                        time_str = now_time.strftime("%I:%M:%S %p")
                        date_str = now_time.strftime("%A, %b %d")
                        draw.text(((128 - draw.textlength(time_str, font=blocky_font)
                                    ) // 2, 20), time_str, font=blocky_font, fill=255)
                        draw.text(((128 - draw.textlength(date_str, font=blocky_font)
                                    ) // 2, 40), date_str, font=blocky_font, fill=255)

                    elif show_yt_title_mode:
                        frame_clean = Image.new('1', (128, 64), 0)
                        draw = ImageDraw.Draw(frame_clean)
                        elapsed = current_time - yt_title_start_time
                        title_w = draw.textlength(
                            current_yt_title, font=blocky_font)
                        chan_str = f"By: {current_yt_channel}"
                        chan_w = draw.textlength(chan_str, font=blocky_font)

                        x_title = 5 - min(max(0, (elapsed - 1.0) * 40), title_w -
                                          110) if title_w > 120 else (128 - title_w) // 2
                        x_chan = 5 - min(max(0, (elapsed - 1.0) * 40), chan_w -
                                         110) if chan_w > 120 else (128 - chan_w) // 2

                        draw.text((x_title, 12), current_yt_title,
                                  font=blocky_font, fill=255)
                        draw.text((x_chan, 38), chan_str,
                                  font=blocky_font, fill=255)

                    else:
                        frame_clean = frame.resize((128, 64)).convert(
                            'L').point(lambda x: 255 if x > 128 else 0, mode='1')
                        ImageDraw.Draw(frame_clean).text((2, 52), str(
                            current_wpm), font=blocky_font, fill=255)

                    if dark_mode_active:
                        frame_clean = frame_clean.point(
                            lambda x: 0 if x > 0 else 255, mode='1')

                    pixels = frame_clean.load()
                    buffer = bytearray(1024)
                    for page in range(8):
                        for x in range(128):
                            byte = 0
                            for bit in range(8):
                                if pixels[x, page * 8 + bit] > 0:
                                    byte |= (1 << bit)
                            buffer[page * 128 + x] = byte

                    send_oled_frame(buffer, is_text_mode=is_text_active)

        except Exception as e:
            print(f"GIF Stream Error: {e}")
            is_booting = False
            continue

        if chosen_gif_name == ACTIVE_GIF:
            just_woke_up = False
        is_booting = False


if __name__ == "__main__":
    threading.Thread(target=optimize_and_clean_memory_file,
                     daemon=True).start()
    threading.Thread(target=volume_background_worker, daemon=True).start()
    threading.Thread(target=productivity_nudge_daemon, daemon=True).start()
    stream_gif()
