import streamlit as st
import yt_dlp
import ffmpeg
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip
import os

st.title("🎧 YouTube Video Translator & Dubbing App")

# --- Input section
video_url = st.text_input("📎 Paste YouTube video link:")
target_lang = st.selectbox(
    "🌐 Choose target translation language:",
    ["en", "hi", "te", "ta", "ml", "kn", "fr", "es", "de"]
)

if st.button("Translate and Dub Video"):
    if not video_url:
        st.error("Please paste a valid YouTube link.")
    else:
        try:
            st.info("📥 Downloading YouTube video...")
            ydl_opts = {'outtmpl': 'video.%(ext)s', 'format': 'best'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Find the downloaded video
            for file in os.listdir():
                if file.startswith("video") and file.endswith((".mp4", ".mkv", ".webm")):
                    input_video = file
                    break

            # --- Extract audio from the video
            st.info("🎧 Extracting original audio...")
            ffmpeg.input(input_video).output('audio.wav').run(overwrite_output=True)

            # --- Convert speech to text
            st.info("🗣️ Converting audio to text...")
            recognizer = sr.Recognizer()
            with sr.AudioFile('audio.wav') as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)

            # --- Translate the text
            st.info("🌍 Translating text...")
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)

            # --- Convert translated text to speech
            st.info("🔊 Generating translated audio...")
            tts = gTTS(translated_text, lang=target_lang)
            tts.save("translated_audio.mp3")

            # --- Merge translated audio with original video
            st.info("🎬 Replacing original audio in the video...")
            video_clip = VideoFileClip(input_video)
            audio_clip = AudioFileClip("translated_audio.mp3")

            # Ensure same duration for audio/video
            if audio_clip.duration < video_clip.duration:
                audio_clip = audio_clip.set_duration(video_clip.duration)

            final_video = video_clip.set_audio(audio_clip)
            final_video.write_videofile("translated_video.mp4", codec="libx264", audio_codec="aac")

            st.success("✅ Translation & dubbing complete!")
            st.video("translated_video.mp4")
            st.download_button(
                "⬇️ Download Translated Video",
                data=open("translated_video.mp4", "rb"),
                file_name="translated_video.mp4",
                mime="video/mp4"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
