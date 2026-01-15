import speech_recognition as sr
import openai
import tkinter as tk
from tkinter import messagebox
import threading
import pyttsx3
import os
import time

# Insert your OpenAI API key here
openai.api_key = os.getenv("AI_KEY")

WAKE_WORD = "computer ai"

# Initialize text-to-speech engine
tts_engine = pyttsx3.init()

def get_answer(question):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=question,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {e}"

def show_box(text):
    # Create a simple Tkinter message box
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    messagebox.showinfo("Answer", text)
    time.sleep(10)
    root.destroy()

def speak(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

def listen_for_question():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Say your question now.")
        try:
            audio = recognizer.listen(source, timeout=5)
            question = recognizer.recognize_google(audio)
            print(f"Question: {question}")
            answer = get_answer(question)
            show_box(answer)
            # Speak the answer aloud
            speak(answer)
        except sr.UnknownValueError:
            show_box("Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
        except sr.RequestError:
            show_box("API error.")
            speak("API error.")
        except sr.WaitTimeoutError:
            show_box("Listening timed out. Please try again.")
            speak("Listening timed out. Please try again.")

def listen_for_wake_word():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
    print("Listening for wake word...")
    while True:
        with microphone as source:
            try:
                audio = recognizer.listen(source, timeout=1)
                phrase = recognizer.recognize_google(audio).lower()
                print(f"Heard: {phrase}")
                if WAKE_WORD in phrase:
                    print("Wake word detected! Listening for your question...")
                    # Run question listening in a separate thread
                    threading.Thread(target=listen_for_question).start()
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                print("API unavailable or unresponsive.")
                continue

if __name__ == "__main__":
    listen_for_wake_word()
