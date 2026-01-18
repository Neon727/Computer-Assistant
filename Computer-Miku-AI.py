import os
import queue
import threading
import json
import time
import tkinter as tk
from PIL import Image, ImageTk
import sounddevice as sd
import vosk
import pygame
from openai import OpenAI
from TTS.api import TTS

# ================= CONFIG =================
client = OpenAI(api_key=os.getenv("AI_KEY"))

WAKE_WORD = "computer ai"
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
PIXEL_AVATAR_SIZE = 128
# ==========================================

audio_queue = queue.Queue()
conversation_history = []

# ✅ VALID Coqui TTS model
tts_model = TTS(model_name="tts_models/en/vctk/vits")

# Initialize pygame for audio playback
pygame.mixer.init()

# ================== AVATAR ==================
class AvatarWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{PIXEL_AVATAR_SIZE}x{PIXEL_AVATAR_SIZE}+100+100")
        self.canvas = tk.Canvas(self.root, width=PIXEL_AVATAR_SIZE,
                                height=PIXEL_AVATAR_SIZE, highlightthickness=0)
        self.canvas.pack()

        self.frames = {
            "idle": ImageTk.PhotoImage(file="miku idle.png"),
            "talk1": ImageTk.PhotoImage(file="miku talk1.png"),
            "talk2": ImageTk.PhotoImage(file="miku talk2.png"),
            "blink": ImageTk.PhotoImage(file="miku blink.png")
        }
        self.current_image = self.canvas.create_image(
            PIXEL_AVATAR_SIZE // 2,
            PIXEL_AVATAR_SIZE // 2,
            image=self.frames["idle"]
        )

    def set_frame(self, frame_name):
        self.canvas.itemconfig(self.current_image, image=self.frames[frame_name])
        self.root.update_idletasks()

    def animate_talk(self):
        while pygame.mixer.music.get_busy():
            self.set_frame("talk1")
            time.sleep(0.15)
            self.set_frame("talk2")
            time.sleep(0.15)
        self.set_frame("idle")

    def blink(self):
        self.set_frame("blink")
        time.sleep(0.2)
        self.set_frame("idle")

avatar = AvatarWindow()

# ================== VOICE ==================
def speak_ai(text):
    wav_path = "response.wav"
    tts_model.tts_to_file(text=text, file_path=wav_path)

    pygame.mixer.music.load(wav_path)
    pygame.mixer.music.play()

    threading.Thread(target=avatar.animate_talk, daemon=True).start()

# ================== VOSK ==================
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    audio_queue.put(bytes(indata))

def listen_for_speech(timeout=6):
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback
    ):
        start = time.time()
        while time.time() - start < timeout:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                return json.loads(recognizer.Result()).get("text", "")
    return ""

def get_ai_response(question):
    conversation_history.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation_history[-6:],
        max_tokens=150,
        temperature=0.7
    )

    answer = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": answer})
    return answer

def listen_for_question():
    avatar.blink()
    question = listen_for_speech()
    if not question:
        speak_ai("Sorry, I didn't catch that.")
        return
    answer = get_ai_response(question)
    speak_ai(answer)

def listen_for_wake_word():
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                text = json.loads(recognizer.Result()).get("text", "").lower()
                if WAKE_WORD in text:
                    threading.Thread(target=listen_for_question, daemon=True).start()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=listen_for_wake_word, daemon=True).start()
    avatar.root.mainloop()
