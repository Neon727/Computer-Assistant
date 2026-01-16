import sounddevice as sd
import vosk
import json
import queue
import threading
import openai
import pyttsx3
import tkinter as tk
from tkinter import messagebox
import os
import time

# ================= CONFIG =================

openai.api_key = os.getenv("AI_KEY")
WAKE_WORD = "computer ai"
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

# ==========================================

audio_queue = queue.Queue()
conversation_history = []

# Text-to-speech
tts_engine = pyttsx3.init()

def speak(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

def show_box(text):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Answer", text)
    root.destroy()

def get_answer(question):
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
        callback=audio_callback,
    ):
        start = time.time()
        while time.time() - start < timeout:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                return result.get("text", "")
    return ""

def listen_for_question():
    print("Listening for question...")
    question = listen_for_speech()

    if not question:
        show_box("Sorry, I didn't catch that.")
        speak("Sorry, I didn't catch that.")
        return

    print("Question:", question)
    answer = get_answer(question)
    show_box(answer)
    speak(answer)

def listen_for_wake_word():
    print("Listening for wake word...")
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=audio_callback,
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()

                if text:
                    print("Heard:", text)

                if WAKE_WORD in text:
                    print("Wake word detected!")
                    speak("Yes?")
                    threading.Thread(target=listen_for_question).start()

if __name__ == "__main__":
    listen_for_wake_word()
