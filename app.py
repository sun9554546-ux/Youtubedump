import streamlit as st
import yt_dlp
import ffmpeg
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip
from langdetect import detect
import os

st.set_page_config(page_title="AI Video Translator", page_icon="🎧", layout="wide")

st.title("🎬 AI Video Translator & Dubbing App")
st.write("Upload or paste a YouTube link — this app will automatically translate and dub your video into another language with subtitles!")

# --- Input choice
option = st.radio("Choose input source:", ["📎 YouTube Link", "📤 Upload Video File"])

video_path = None

if option == "📎 YouTube Link":
    video_url = st.text_input("Paste YouTube video link:")
    if video_url:
        ydl_opts = {'outtmpl': 'video.%(ext)s', 'format': 'best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            st.info("📥 Downloading video...")
            ydl.download([video_url])
        for f in os.listdir():
            if f.startswith("video") and f.endswith((".mp4", ".mkv", ".webm")):
                video_path = f
                break

elif option == "📤 Upload Video File":
    uploaded = st.file_uploader("Upload a video file", type=["mp4", "mkv", "mov", "webm"])
    if uploaded:
        video_path = uploaded.name
        with open(video_path, "wb") as f:
            f.write(uploaded.read())
        st.success(f"✅ Uploaded: {uploaded.name}")

# --- Target language
target_lang = st.selectbox(
    "🌐 Choose translation language:",
    ["en", "hi", "te", "ta", "ml", "kn", "fr", "es", "de"]
)

progress = st.progress(0)
status = st.empty()

if st.button("🎧 Translate and Dub"):
    if not video_path:
        st.error("Please provide a video file or YouTube link first.")
    else:
        try:
            progress.progress(10)
            status.text("🎧 Extracting audio from video...")
            ffmpeg.input(video_path).output('audio.wav').run(overwrite_output=True)

            progress.progress(30)
            status.text("🗣️ Transcribing speech to text...")
            recognizer = sr.Recognizer()
            with sr.AudioFile('audio.wav') as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)

            if not text.strip():
                raise Exception("No speech detected in video.")

            progress.progress(45)
            detected_lang = detect(text)
            st.info(f"🔍 Detected source language: **{detected_lang.upper()}**")

            progress.progress(55)
            status.text("🌍 Translating text...")
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)

            progress.progress(70)
            status.text("🔊 Generating translated voice...")
            tts = gTTS(translated_text, lang=target_lang)
            tts.save("translated_audio.mp3")

            progress.progress(80)
            status.text("🎬 Merging translated audio with video...")
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip("translated_audio.mp3")

            if audio_clip.duration < video_clip.duration:
                audio_clip = audio_clip.set_duration(video_clip.duration)

            final_video = video_clip.set_audio(audio_clip)
            final_video.write_videofile("translated_video.mp4", codec="libx264", audio_codec="aac", verbose=False, logger=None)

            progress.progress(95)
            status.text("📝 Generating subtitles...")
            with open("subtitles.srt", "w", encoding="utf-8") as srt:
                srt.write("1\n00:00:00,000 --> 00:00:10,000\n" + translated_text + "\n")

            progress.progress(100)
            status.text("✅ All done!")

            st.success("✅ Video translated and dubbed successfully!")
            st.video("translated_video.mp4")

            with open("translated_video.mp4", "rb") as f:
                st.download_button("⬇️ Download Translated Video", f, file_name="translated_video.mp4", mime="video/mp4")

            with open("subtitles.srt", "rb") as s:
                st.download_button("🗒️ Download Subtitles (.srt)", s, file_name="subtitles.srt", mime="text/plain")

        except Exception as e:
            st.error(f"❌ Error: {e}")
