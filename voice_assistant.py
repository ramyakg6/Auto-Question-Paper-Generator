import threading
import queue
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
        self._init_engine()
        self._start_worker()

    def _init_engine(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 160)    # Speed
            self.engine.setProperty('volume', 0.9)  # Volume
            # Try to set a female voice if available
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"[Voice] TTS init error: {e}")
            self.engine = None

    def _start_worker(self):
        """Background thread to process speech queue."""
        def worker():
            while True:
                text = self.speech_queue.get()
                if text is None:
                    break
                try:
                    if self.engine and self.enabled:
                        self.engine.say(text)
                        self.engine.runAndWait()
                except Exception as e:
                    print(f"[Voice] Speak error: {e}")
                    self._init_engine()  # Reinit on error
                self.speech_queue.task_done()

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def speak(self, text):
        """Add text to speech queue."""
        if self.enabled and self.engine:
            # Clear queue to avoid backlog
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except:
                    pass
            self.speech_queue.put(text)

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled

    def stop(self):
        try:
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
            mic = sr.Microphone()

            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)

            while self.active:
                try:
                    with mic as source:
                        audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio).lower()
                    print(f"[Voice] Heard: {text}")
                    self._process_command(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"[Voice] Listen error: {e}")
        except ImportError:
            print("[Voice] SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")

    def _process_command(self, text):
        """Map voice commands to actions."""
        commands = {
            # Navigation
            "generate paper":       "nav_generate",
            "open generate":        "nav_generate",
            "ai generate":          "nav_ai",
            "open ai":              "nav_ai",
            "question bank":        "nav_bank",
            "open bank":            "nav_bank",
            "show history":         "nav_history",
            "open history":         "nav_history",
            # Actions
            "generate":             "action_generate",
            "create paper":         "action_generate",
            "start":                "action_generate",
            "save":                 "action_save",
            "logout":               "action_logout",
            "log out":              "action_logout",
            # Voice control
            "stop listening":       "voice_stop",
            "mute":                 "voice_mute",
            "unmute":               "voice_unmute",
        }

        for phrase, action in commands.items():
            if phrase in text:
                self.callback(action)
                return

        self.assistant.speak("Sorry, I didn't understand that command.")


# ── Global assistant instance ─────────────────────────────────
_assistant = None

def get_assistant():
    global _assistant
    if _assistant is None:
        _assistant = VoiceAssistant()
    return _assistant

def speak(text):
    get_assistant().speak(text)