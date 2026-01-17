import os
import queue
import threading
import json
import time
import tkinter as tk
from PIL import Image, ImageTk
import sounddevice as sd
import vosk
import openai
import pygame
from TTS.api import TTS  # Coqui TTS

# ================= CONFIG =================
openai.api_key = os.getenv("AI_KEY")  # Set your OpenAI API key in env
WAKE_WORD = "computer ai"
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
PIXEL_AVATAR_SIZE = 128
# ==========================================

audio_queue = queue.Queue()
conversation_history = []

# Initialize TTS (Coqui) - replace with your Miku-like model
tts_model = TTS(model_name="tts_models/en/multilingual/miku_v1")  # Example Miku-style TTS

# Initialize pygame for audio playback
pygame.mixer.init()

# ================== AVATAR ==================
class AvatarWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Floating window
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{PIXEL_AVATAR_SIZE}x{PIXEL_AVATAR_SIZE}+100+100")
        self.canvas = tk.Canvas(self.root, width=PIXEL_AVATAR_SIZE, height=PIXEL_AVATAR_SIZE, highlightthickness=0)
        self.canvas.pack()

        # Load images
        self.frames = {
            "idle": ImageTk.PhotoImage(file="miku idle.png"),
            "talk1": ImageTk.PhotoImage(file="miku talk1.png"),
            "talk2": ImageTk.PhotoImage(file="miku talk2.png"),
            "blink": ImageTk.PhotoImage(file="miku blink.png")
        }
        self.current_image = self.canvas.create_image(PIXEL_AVATAR_SIZE//2, PIXEL_AVATAR_SIZE//2, image=self.frames["idle"])
        self.root.update()

    def set_frame(self, frame_name):
        self.canvas.itemconfig(self.current_image, image=self.frames[frame_name])
        self.root.update()

    def animate_talk(self, duration=1.0, fps=5):
        frames = ["talk1", "talk2"]
        end_time = time.time() + duration
        while time.time() < end_time:
            for f in frames:
                self.set_frame(f)
                time.sleep(1/fps)
        self.set_frame("idle")

    def blink(self):
        self.set_frame("blink")
        time.sleep(0.2)
        self.set_frame("idle")

avatar = AvatarWindow()

# ================== VOICE ==================
def speak_ai(text):
    # Generate speech WAV from AI TTS
    wav_path = "miku_response.wav"
    tts_model.tts_to_file(text=text, file_path=wav_path)

    # Play WAV with pygame
    pygame.mixer.music.load(wav_path)
    pygame.mixer.music.play()

    # Animate talking while audio plays
    while pygame.mixer.music.get_busy():
        avatar.animate_talk(duration=0.5)

# ================== VOSK LISTEN ==================
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def listen_for_speech(timeout=6):
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                           dtype="int16", channels=1, callback=audio_callback):
        start = time.time()
        while time.time() - start < timeout:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                return result.get("text", "")
    return ""

def get_ai_response(question):
    conversation_history.append(f"User: {question}")
    context = "\n".join(conversation_history[-6:])
    prompt = f"{context}\nAI:"

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7,
            stop=["User:", "AI:"]
        )
        answer = response.choices[0].text.strip()
        conversation_history.append(f"AI: {answer}")
        return answer
    except Exception as e:
        return f"Error: {e}"

def listen_for_question():
    avatar.blink()
    print("Listening for question...")
    question = listen_for_speech()
    if not question:
        speak_ai("Sorry, I didn't catch that.")
        return
    print("Question:", question)
    answer = get_ai_response(question)
    speak_ai(answer)

def listen_for_wake_word():
    print("Listening for wake word...")
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                           dtype="int16", channels=1, callback=audio_callback):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if WAKE_WORD in text:
                    print("Wake word detected!")
                    threading.Thread(target=listen_for_question).start()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=listen_for_wake_word, daemon=True).start()
    avatar.root.mainloop()
