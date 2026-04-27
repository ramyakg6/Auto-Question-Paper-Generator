import threading
import queue
import time
import pyttsx3

# ── Voice Assistant Module ────────────────────────────────────
# Uses pyttsx3 for text-to-speech (offline, no API needed)
# Uses SpeechRecognition for voice commands


class VoiceAssistant:
    def __init__(self):
        self.engine = None
        self.enabled = True
        self.speech_queue = queue.Queue()
        self.listening = False
        self._lock = threading.Lock()
        self._on_command_heard = None   # FIX 1: callback to update visual status bar
        self._init_engine()
        self._start_worker()

    def set_command_callback(self, callback):
        """Register a callback to show heard text in the UI (visual feedback)."""
        self._on_command_heard = callback

    def _init_engine(self):
        """FIX 3: Silently reinit TTS engine on crash."""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 155)
            self.engine.setProperty('volume', 0.9)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            print("[Voice] TTS engine initialized.")
        except Exception as e:
            print(f"[Voice] TTS init error: {e}")
            self.engine = None

    def _start_worker(self):
        """FIX 4: Smoother speech queue — don't abruptly drop items, let current finish."""
        def worker():
            while True:
                try:
                    text = self.speech_queue.get(timeout=0.5)
                    if text is None:
                        break
                    if self.enabled and self.engine:
                        try:
                            with self._lock:
                                self.engine.say(text)
                                self.engine.runAndWait()
                        except Exception as e:
                            print(f"[Voice] Speak error: {e}")
                            # FIX 3: Auto reinit on any TTS crash
                            time.sleep(0.5)
                            self._init_engine()
                    self.speech_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[Voice] Worker error: {e}")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def speak(self, text):
        """FIX 4: Smoother queue — only drop queued items if queue is getting backed up (>2 items)."""
        if not self.enabled or not self.engine:
            return
        # Only clear backlog if more than 2 items are queued (avoids cutting off important messages)
        if self.speech_queue.qsize() > 2:
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except:
                    pass
        self.speech_queue.put(text)

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled

    def stop(self):
        """Stop current speech immediately."""
        try:
            with self._lock:
                if self.engine:
                    self.engine.stop()
        except:
            pass


class VoiceCommandListener:
    """Listens for voice commands using microphone."""
    def __init__(self, assistant, command_callback):
        self.assistant = assistant
        self.callback = command_callback
        self.active = False

    def start_listening(self):
        self.active = True
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def stop_listening(self):
        self.active = False

    def _listen_loop(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300          # Better sensitivity
            recognizer.dynamic_energy_threshold = True  # Auto-adjust for noise
            mic = sr.Microphone()

            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                print("[Voice] Ambient noise adjusted. Listening...")

            while self.active:
                try:
                    with mic as source:
                        audio = recognizer.listen(source, timeout=4, phrase_time_limit=6)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"[Voice] Heard: {text}")

                    # FIX 1: Update visual status bar with what was heard
                    if self.assistant._on_command_heard:
                        self.assistant._on_command_heard(f'🎙 Heard: "{text}"')

                    self._process_command(text)

                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    # FIX 1: Show in status bar when speech wasn't understood
                    if self.assistant._on_command_heard:
                        self.assistant._on_command_heard("🎙 Listening... (couldn't understand)")
                except Exception as e:
                    print(f"[Voice] Listen error: {e}")
                    if self.assistant._on_command_heard:
                        self.assistant._on_command_heard(f"🎙 Error: {e}")

        except ImportError:
            print("[Voice] SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")

    def _process_command(self, text):
        """FIX 2: Extended command map with preview, clear, and better aliases."""
        commands = {
            # Navigation
            "generate paper":       "nav_generate",
            "open generate":        "nav_generate",
            "go to generate":       "nav_generate",
            "ai generate":          "nav_ai",
            "open ai":              "nav_ai",
            "go to ai":             "nav_ai",
            "question bank":        "nav_bank",
            "open bank":            "nav_bank",
            "go to bank":           "nav_bank",
            "show history":         "nav_history",
            "open history":         "nav_history",
            "go to history":        "nav_history",
            # Actions
            "generate":             "action_generate",
            "create paper":         "action_generate",
            "make paper":           "action_generate",
            "show preview":         "action_preview",   # FIX 2: new
            "preview":              "action_preview",   # FIX 2: new
            "save":                 "action_save",
            "clear":                "action_clear",     # FIX 2: new
            "reset":                "action_clear",     # FIX 2: new
            "logout":               "action_logout",
            "log out":              "action_logout",
            "sign out":             "action_logout",
            # Voice control
            "stop listening":       "voice_stop",
            "stop voice":           "voice_stop",
            "mute":                 "voice_mute",
            "mute voice":           "voice_mute",
            "unmute":               "voice_unmute",
            "unmute voice":         "voice_unmute",
            "enable voice":         "voice_unmute",
            # Help
            "help":                 "action_help",      # FIX 2: new
            "what can you do":      "action_help",
            "commands":             "action_help",
        }

        for phrase, action in commands.items():
            if phrase in text:
                self.callback(action)
                return

        # Not understood — speak feedback
        self.assistant.speak("Sorry, I didn't catch that. Say 'help' for a list of commands.")


# ── Global assistant instance ─────────────────────────────────
_assistant = None

def get_assistant():
    global _assistant
    if _assistant is None:
        _assistant = VoiceAssistant()
    return _assistant

def speak(text):
    get_assistant().speak(text)