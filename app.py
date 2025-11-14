# app.py
import os
import shutil
import subprocess
import tempfile
import yt_dlp
import openai
from deep_translator import GoogleTranslator
from gtts import gTTS
from langdetect import detect
import streamlit as st

st.set_page_config(page_title="AI Video Translator", page_icon="🎧", layout="wide")
st.title("🎬 AI Video Translator (Whisper API)")

# --- OpenAI setup
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not OPENAI_KEY:
    st.error("Missing OpenAI API key. Add OPENAI_API_KEY to Streamlit Secrets or environment.")
    st.stop()
openai.api_key = OPENAI_KEY

# --- Input
option = st.radio("Choose input source:", ["📎 YouTube Link", "📤 Upload Video File"])

video_path = None
temp_dir = None

if option == "📎 YouTube Link":
    video_url = st.text_input("Paste YouTube video link:")
    if video_url:
        # download into a temp dir
        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            "outtmpl": os.path.join(temp_dir, "video.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "noplaylist": True,
        }
        with st.spinner("Downloading video..."):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        # find downloaded file
        for f in os.listdir(temp_dir):
            if f.startswith("video") and f.rsplit(".", 1)[-1] in ("mp4", "mkv", "webm", "mov"):
                video_path = os.path.join(temp_dir, f)
                break
        if video_path:
            st.success(f"Downloaded to `{video_path}`")
        else:
            st.error("Could not find downloaded video file.")

elif option == "📤 Upload Video File":
    uploaded = st.file_uploader("Upload a video file", type=["mp4", "mkv", "mov", "webm"])
    if uploaded:
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, uploaded.name)
        with open(video_path, "wb") as f:
            f.write(uploaded.read())
        st.success(f"Uploaded: {uploaded.name}")

# --- target language
target_lang = st.selectbox(
    "🌐 Choose translation language (for dubbing & subtitles):",
    ["en", "hi", "te", "ta", "ml", "kn", "fr", "es", "de"]
)

if st.button("🎧 Transcribe → Translate → TTS"):
    if not video_path or not os.path.exists(video_path):
        st.error("Please provide a valid video file or YouTube link first.")
    else:
        try:
            st.info("1/5 — Sending video to OpenAI Whisper for transcription...")
            with open(video_path, "rb") as vf:
                # Uses OpenAI Speech-to-Text (Whisper) — returns a dict with 'text'
                # This call sends the raw video file (mp4/webm) and Whisper transcribes audio tracks inside.
                transcript = openai.Audio.transcribe("whisper-1", vf)
                text = transcript.get("text", "").strip()

            if not text:
                st.warning("Transcription returned empty text.")
            else:
                st.success("Transcription complete.")
                st.write("**Transcript (excerpt):**")
                st.code(text[:1000] + ("..." if len(text) > 1000 else ""))

            # language detection (optional)
            try:
                detected_lang = detect(text) if text else "unknown"
            except Exception:
                detected_lang = "unknown"
            st.info(f"Detected language: {detected_lang}")

            st.info("2/5 — Translating text...")
            translated_text = GoogleTranslator(source="auto", target=target_lang).translate(text) if text else ""
            st.success("Translation complete.")
            st.write("**Translated (excerpt):**")
            st.code(translated_text[:1000] + ("..." if len(translated_text) > 1000 else ""))

            st.info("3/5 — Generating TTS audio (gTTS)...")
            tts = gTTS(translated_text or " ", lang=target_lang)
            tts_path = os.path.join(tempfile.mkdtemp(), "translated_audio.mp3")
            tts.save(tts_path)
            st.success("TTS generated.")

            st.info("4/5 — Creating subtitles (SRT)...")
            srt_path = os.path.join(tempfile.mkdtemp(), "subtitles.srt")
            # Simple single-block SRT — you can improve with timestamps later.
            with open(srt_path, "w", encoding="utf-8") as s:
                s.write("1\n00:00:00,000 --> 00:59:59,000\n")
                s.write(translated_text + "\n")
            st.success("Subtitles created.")

            # Attempt to merge audio into video if ffmpeg is present
            ffmpeg_bin = shutil.which("ffmpeg")
            if ffmpeg_bin:
                st.info("5/5 — ffmpeg found on host, merging audio into video...")
                out_path = os.path.join(tempfile.mkdtemp(), "translated_video.mp4")
                # Use ffmpeg subprocess to replace audio track
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    tts_path,
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    out_path,
                ]
                subprocess.run(cmd, check=True)
                st.success("Merged audio into video.")
                st.video(out_path)
                st.download_button("⬇️ Download Translated Video", open(out_path, "rb"), file_name="translated_video.mp4", mime="video/mp4")
            else:
                st.warning(
                    "ffmpeg binary not found on this host. The app created the translated audio and subtitles files for you to download. "
                    "To merge audio + video, run locally: ffmpeg -i original_video.mp4 -i translated_audio.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4"
                )
                st.audio(tts_path, format="audio/mp3")
                st.download_button("⬇️ Download Translated Audio (MP3)", open(tts_path, "rb"), file_name="translated_audio.mp3", mime="audio/mpeg")
                st.download_button("⬇️ Download Subtitles (SRT)", open(srt_path, "rb"), file_name="subtitles.srt", mime="text/plain")

            st.success("Done — check the downloads above.")

        except subprocess.CalledProcessError as e:
            st.error(f"Error while calling ffmpeg: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# Cleanup: optional remove temp_dir if created
if st.button("🧹 Cleanup temp files"):
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        st.success("Temp files removed.")
    else:
        st.info("No temp files found.")
