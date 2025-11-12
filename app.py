import os
import yt_dlp
import ffmpeg
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import tkinter as tk
from tkinter import scrolledtext

# ===== SETTINGS =====
TARGET_LANG = "te"  # Telugu (change as needed)
OUTPUT_NAME = "translated_video.mp4"

# ===== FUNCTIONS =====
def download_youtube_video(url):
    log_box.insert(tk.END, "📥 Downloading video...\n")
    ydl_opts = {'format': 'best', 'outtmpl': 'video.mp4'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video.mp4"
def extract_audio(video_path):
    log_box.insert(tk.END, "Extracting audio...\n")
    # Delete old audio file if it exists
    if os.path.exists("audio.wav"):
        os.remove("audio.wav")

    # Correct FFmpeg conversion — guarantees a real WAV file
    cmd = "ffmpeg -y -i video.mp4 -ac 1 -ar 16000 -acodec pcm_s16le audio.wav"
    os.system(cmd)

    # Double-check if file was created
    if not os.path.exists("audio.wav"):
        log_box.insert(tk.END, "❌ Failed to create audio.wav. Check FFmpeg plugin.\n")
    else:
        log_box.insert(tk.END, "✅ Audio extracted successfully.\n")
    return "audio.wav"

def transcribe_audio_and_detect(audio_path):
    log_box.insert(tk.END, "🗣️ Converting speech to text (auto-detect language)...\n")
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, show_all=True)
        if isinstance(text, dict) and "alternative" in text:
            transcript = text["alternative"][0]["transcript"]
            detected_lang = text.get("language", "auto")
        else:
            transcript = recognizer.recognize_google(audio_data)
            detected_lang = "auto"
    except Exception as e:
        transcript = "[Could not understand audio]"
        detected_lang = "auto"

    log_box.insert(tk.END, f"🌍 Detected language: {detected_lang}\n")
    return transcript, detected_lang

def translate_text(text, target_lang):
    log_box.insert(tk.END, f"🔁 Translating text to {target_lang}...\n")
    translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
    return translated

def text_to_speech(text, target_lang):
    log_box.insert(tk.END, "🔊 Generating translated voice...\n")
    tts = gTTS(text=text, lang=target_lang)
    tts.save("translated.mp3")
    return "translated.mp3"

def merge_audio_video(video_path, audio_path, output_path):
    log_box.insert(tk.END, "🎬 Merging translated audio with video...\n")
    os.system(f"ffmpeg -i {video_path} -i {audio_path} -map 0:v -map 1:a -c:v copy -shortest {output_path} -y")
    return output_path

def start_translation():
    url = url_entry.get()
    if not url:
        log_box.insert(tk.END, "⚠️ Please enter a YouTube URL.\n")
        return

    video_path = download_youtube_video(url)
    audio_path = extract_audio(video_path)
    text, detected_lang = transcribe_audio_and_detect(audio_path)
    translated_text = translate_text(text, TARGET_LANG)
    translated_audio = text_to_speech(translated_text, TARGET_LANG)
    merge_audio_video(video_path, translated_audio, OUTPUT_NAME)
    log_box.insert(tk.END, f"\n✅ Done! Saved as {OUTPUT_NAME}\n")

# ===== GUI =====
root = tk.Tk()
root.title("YouTube Translator (Auto-Detect Lite)")
root.geometry("520x520")

tk.Label(root, text="Enter YouTube Video URL:", font=("Arial", 12)).pack(pady=5)
url_entry = tk.Entry(root, width=60)
url_entry.pack(pady=5)

start_button = tk.Button(
    root, text="Translate Video",
    bg="#4CAF50", fg="white",
    font=("Arial", 12, "bold"),
    command=start_translation
)
start_button.pack(pady=10)

log_box = scrolledtext.ScrolledText(root, width=70, height=18, wrap=tk.WORD)
log_box.pack(pady=10)

root.mainloop()
  
